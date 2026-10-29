# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.addons.container_demurrage.utils.iso6346 import (
    normalize_container_number, validate_container_number)
from odoo.addons.container_demurrage.utils.dates import days_between, last_free_day
from odoo.addons.container_demurrage.utils.calculator import calculate, Tier
from decimal import Decimal


class DemurrageContainer(models.Model):
    _name = "demurrage.container"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Contenedor"
    _order = "container_number"

    _sql_constraints = [
        (
            "bl_container_number_unique",
            "unique(bl_id, container_number)",
            "Ya existe un contenedor con ese número en este BL.",
        ),
    ]

    name = fields.Char(compute="_compute_name", store=True)
    container_number = fields.Char(required=True, index=True)
    bl_id = fields.Many2one(
        "demurrage.bl", required=True, ondelete="cascade")
    shipping_line_id = fields.Many2one(
        related="bl_id.shipping_line_id", store=True, readonly=True)
    partner_id = fields.Many2one(
        related="bl_id.partner_id", store=True, readonly=True)
    container_type_id = fields.Many2one(
        "demurrage.container.type", required=True, ondelete="restrict")
    discharge_date = fields.Date()
    return_date = fields.Date()
    as_of_date = fields.Date(default=lambda self: fields.Date.today())
    invoiced = fields.Boolean(default=False, copy=False)
    cancelled = fields.Boolean(default=False, copy=False)
    invoice_reference = fields.Char(readonly=True, copy=False)
    invoice_date = fields.Date(readonly=True, copy=False)
    invoiced_at = fields.Datetime(readonly=True, copy=False)
    invoiced_carrier_usd = fields.Monetary(
        readonly=True, copy=False, currency_field="currency_id")
    invoiced_customer_usd = fields.Monetary(
        readonly=True, copy=False, currency_field="currency_id")
    invoiced_demurrage_days = fields.Integer(readonly=True, copy=False)
    invoiced_admin_fee_percent = fields.Float(readonly=True, copy=False)
    invoiced_exchange_rate = fields.Float(readonly=True, copy=False)
    invoiced_customer_cop = fields.Monetary(
        readonly=True, copy=False, currency_field="cop_currency_id")
    invoice_needs_review = fields.Boolean(default=False, copy=False)
    state = fields.Selection(
        [("draft", "Borrador"), ("open", "Abierto"),
         ("returned", "Devuelto"), ("invoiced", "Facturado"),
         ("cancelled", "Cancelado")],
        compute="_compute_state", store=True)
    notes = fields.Text()
    active = fields.Boolean(default=True)

    eir_attachment_ids = fields.Many2many(
        "ir.attachment", "demurrage_container_eir_rel",
        "container_id", "attachment_id", string="Adjuntos EIR")
    eir_count = fields.Integer(
        compute="_compute_eir", store=True, default=0)
    missing_eir = fields.Boolean(
        compute="_compute_eir", store=True, default=True)
    company_id = fields.Many2one(
        related="bl_id.company_id", store=True, readonly=True)

    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda self: self.env.ref("base.USD").id)
    cop_currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda self: self.env.ref("base.COP").id)
    tariff_id = fields.Many2one(
        "demurrage.tariff", compute="_compute_demurrage", store=True)
    agreement_id = fields.Many2one(
        "demurrage.customer.agreement", compute="_compute_demurrage", store=True)
    extra_free_days = fields.Integer(compute="_compute_demurrage", store=True)
    free_days = fields.Integer(compute="_compute_demurrage", store=True)
    days_out = fields.Integer(compute="_compute_demurrage", store=True)
    demurrage_days = fields.Integer(compute="_compute_demurrage", store=True)
    admin_fee_percent = fields.Float(compute="_compute_demurrage", store=True)
    carrier_charge_usd = fields.Monetary(
        compute="_compute_demurrage", store=True, currency_field="currency_id")
    customer_charge_usd = fields.Monetary(
        compute="_compute_demurrage", store=True, currency_field="currency_id")
    customer_charge_cop = fields.Monetary(
        compute="_compute_demurrage", store=True, currency_field="cop_currency_id")
    exchange_rate = fields.Float(compute="_compute_demurrage", store=True)
    exchange_rate_date = fields.Date(compute="_compute_demurrage", store=True)
    missing_tariff = fields.Boolean(compute="_compute_demurrage", store=True)
    missing_exchange_rate = fields.Boolean(compute="_compute_demurrage", store=True)
    is_estimate = fields.Boolean(compute="_compute_demurrage", store=True)
    is_due_soon = fields.Boolean(compute="_compute_demurrage", store=True)
    is_overdue = fields.Boolean(compute="_compute_demurrage", store=True)
    due_date = fields.Date(compute="_compute_demurrage", store=True)
    tier_breakdown = fields.Text(compute="_compute_demurrage")
    calculation_status = fields.Selection(
        [("pending", "Pendiente"), ("ok", "OK"),
         ("missing_tariff", "Sin tarifa"),
         ("missing_rate", "Sin tasa")],
        compute="_compute_demurrage", store=True)

    @api.depends("container_number")
    def _compute_name(self):
        for record in self:
            record.name = record.container_number

    @api.depends("eir_attachment_ids")
    def _compute_eir(self):
        for record in self:
            count = len(record.eir_attachment_ids)
            record.eir_count = count
            record.missing_eir = count == 0

    @api.depends("cancelled", "invoiced", "return_date", "discharge_date")
    def _compute_state(self):
        for record in self:
            if record.cancelled:
                record.state = "cancelled"
            elif record.invoiced:
                record.state = "invoiced"
            elif record.return_date:
                record.state = "returned"
            elif record.discharge_date:
                record.state = "open"
            else:
                record.state = "draft"

    @api.depends("container_number", "bl_id.name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.container_number} ({record.bl_id.name})"

    @api.constrains("container_number")
    def _check_container_number(self):
        for record in self:
            if not record.container_number:
                continue
            is_valid, error, _expected = validate_container_number(
                record.container_number)
            if not is_valid:
                raise ValidationError(error)

    @api.constrains("eir_attachment_ids")
    def _check_eir_attachments(self):
        for record in self:
            for attachment in record.eir_attachment_ids:
                if not attachment.mimetype:
                    raise ValidationError(
                        "El adjunto EIR no tiene un tipo MIME válido.")
                if not (
                    attachment.mimetype == "application/pdf"
                    or attachment.mimetype.startswith("image/")
                ):
                    raise ValidationError(
                        "El adjunto EIR debe ser un PDF o una imagen.")
                size = attachment.file_size or 0
                if size > 10 * 1024 * 1024:
                    raise ValidationError(
                        "El adjunto EIR no puede superar los 10 MB.")

    @api.constrains("discharge_date", "return_date", "container_number",
                    "cancelled", "active", "bl_id")
    def _check_dates_and_overlap(self):
        for record in self:
            if record.return_date:
                if not record.discharge_date:
                    raise ValidationError(
                        "La fecha de devolución requiere fecha de descarga.")
                if record.return_date < record.discharge_date:
                    raise ValidationError(
                        "La fecha de devolución no puede ser anterior a la descarga.")
                if record.return_date > fields.Date.context_today(self):
                    raise ValidationError(
                        "La fecha de devolución no puede ser futura.")
            if record.cancelled or not record.discharge_date:
                continue
            domain = [
                ("container_number", "=", record.container_number),
                ("id", "!=", record.id),
                ("cancelled", "=", False),
                ("discharge_date", "!=", False),
            ]
            others = self.with_context(active_test=False).search(domain)
            rec_start = record.discharge_date
            rec_end = record.return_date or date.max
            for other in others:
                if not other.discharge_date:
                    continue
                other_start = other.discharge_date
                other_end = other.return_date or date.max
                if rec_start <= other_end and other_start <= rec_end:
                    raise ValidationError(
                        "El contenedor ya está registrado como afuera en ese periodo.")

    @api.depends("discharge_date", "return_date", "as_of_date",
                 "shipping_line_id", "container_type_id", "partner_id",
                 "company_id")
    def _compute_demurrage(self):
        for record in self:
            # defaults
            record.tariff_id = False
            record.agreement_id = False
            record.extra_free_days = 0
            record.free_days = 0
            record.days_out = 0
            record.demurrage_days = 0
            record.admin_fee_percent = 0.0
            record.carrier_charge_usd = 0.0
            record.customer_charge_usd = 0.0
            record.customer_charge_cop = 0.0
            record.exchange_rate = 0.0
            record.exchange_rate_date = False
            record.missing_tariff = False
            record.missing_exchange_rate = False
            record.is_estimate = False
            record.is_due_soon = False
            record.is_overdue = False
            record.due_date = False
            record.tier_breakdown = ""
            record.calculation_status = "pending"

            if not record.discharge_date:
                continue

            if record.invoiced and record.invoiced_at:
                record.demurrage_days = record.invoiced_demurrage_days
                record.admin_fee_percent = record.invoiced_admin_fee_percent
                record.carrier_charge_usd = record.invoiced_carrier_usd
                record.customer_charge_usd = record.invoiced_customer_usd
                record.exchange_rate = record.invoiced_exchange_rate
                record.customer_charge_cop = record.invoiced_customer_cop
                record.calculation_status = "ok"
                record.is_estimate = False
                record.missing_tariff = False
                record.missing_exchange_rate = False
                continue

            cutoff = record.return_date or record.as_of_date or fields.Date.today()
            if cutoff < record.discharge_date:
                days_out = 0
            else:
                days_out = days_between(record.discharge_date, cutoff)
            record.days_out = days_out
            record.is_estimate = not bool(record.return_date)

            # tariff
            tariff = record._find_tariff()
            record.tariff_id = tariff
            # agreement
            agreement = record._find_agreement()
            record.agreement_id = agreement
            extra_free_days = agreement.extra_free_days if agreement else 0
            record.extra_free_days = extra_free_days

            default_fee = float(self.env["ir.config_parameter"].sudo().get_param(
                "container_demurrage.default_admin_fee_percent", "10.0"))
            admin_percent = (agreement.admin_fee_percent if agreement
                             else default_fee)
            record.admin_fee_percent = admin_percent

            if not tariff:
                record.missing_tariff = True
                record.calculation_status = "missing_tariff"
                record.free_days = 0
                record.due_date = False
                continue

            free_days = tariff.free_days + extra_free_days
            record.free_days = free_days

            tiers = []
            for t in tariff.tier_ids:
                day_to = t.day_to if t.day_to not in (0, False) else None
                tiers.append(Tier(t.day_from, day_to, Decimal(str(t.rate_per_day))))

            calc = calculate(days_out, free_days, tiers, Decimal(str(admin_percent)))
            record.demurrage_days = calc.demurrage_days
            record.carrier_charge_usd = float(calc.carrier_amount)
            record.customer_charge_usd = float(calc.customer_amount)

            lines = []
            for ln in calc.lines:
                rate_s = f"{ln.rate:.2f}".replace(".", ",")
                sub_s = f"{ln.subtotal:.2f}".replace(".", ",")
                lines.append(
                    f"{ln.label}: {ln.days} × USD {rate_s} = USD {sub_s}")
            record.tier_breakdown = "\n".join(lines)

            record.due_date = last_free_day(record.discharge_date, free_days)

            # TRM
            record.exchange_rate_date = cutoff
            result = record._get_exchange_rate(cutoff)
            if isinstance(result, tuple):
                exchange_rate, found = result
            else:
                exchange_rate, found = result, True
            if not found or exchange_rate is None:
                record.exchange_rate = 0.0
                record.missing_exchange_rate = bool(record.customer_charge_usd)
                record.customer_charge_cop = 0.0
                record.calculation_status = "ok"
            else:
                record.exchange_rate = exchange_rate
                record.missing_exchange_rate = False
                if record.customer_charge_usd:
                    record.customer_charge_cop = round(
                        record.customer_charge_usd * exchange_rate, 2)
                record.calculation_status = "ok"

            # vencimiento
            due_soon_days = int(float(self.env["ir.config_parameter"].sudo().get_param(
                "container_demurrage.due_soon_days", "2") or 2))
            record.is_due_soon = False
            record.is_overdue = False
            if record.state == "open" and record.due_date:
                as_of = record.as_of_date or fields.Date.today()
                record.is_overdue = record.due_date < as_of
                record.is_due_soon = (
                    as_of <= record.due_date <= as_of + timedelta(days=due_soon_days))

    def _find_tariff(self):
        self.ensure_one()
        if not (self.shipping_line_id and self.container_type_id
                and self.discharge_date):
            return self.env["demurrage.tariff"]
        domain = [
            ("shipping_line_id", "=", self.shipping_line_id.id),
            ("container_type_id", "=", self.container_type_id.id),
            ("company_id", "=", self.company_id.id),
            ("valid_from", "<=", self.discharge_date),
            "|", ("valid_to", "=", False),
            ("valid_to", ">=", self.discharge_date),
            ("active", "=", True),
        ]
        return self.env["demurrage.tariff"].search(
            domain, order="valid_from desc", limit=1)

    def _get_exchange_rate(self, date):
        self.ensure_one()
        company = self.company_id or self.env.company
        root = company.root_id
        company_currency = company.currency_id

        def _rate_for(currency):
            if not currency:
                return None, False
            if currency == company_currency:
                return 1.0, True
            rec = self.env["res.currency.rate"].search([
                ("currency_id", "=", currency.id),
                ("name", "<=", date),
                ("company_id", "in", [False, root.id]),
            ], order="name desc", limit=1)
            if not rec:
                return None, False
            return rec.rate, True

        rate_usd, ok_usd = _rate_for(self.currency_id)
        if not ok_usd:
            return None, False
        rate_cop, ok_cop = _rate_for(self.cop_currency_id)
        if not ok_cop:
            return None, False
        if not rate_usd:
            return None, False
        return (rate_cop / rate_usd), True

    def _find_agreement(self):
        self.ensure_one()
        if not (self.partner_id and self.shipping_line_id):
            return self.env["demurrage.customer.agreement"]
        domain = [
            ("partner_id", "=", self.partner_id.id),
            ("shipping_line_id", "=", self.shipping_line_id.id),
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ]
        return self.env["demurrage.customer.agreement"].search(domain, limit=1)

    def write(self, vals):
        sensitive = {"container_number", "bl_id", "container_type_id",
                     "discharge_date", "return_date"}
        if sensitive & set(vals):
            for rec in self:
                if rec.invoiced and not self.env.context.get("demurrage_reopen"):
                    raise UserError(
                        "Reabra la facturación antes de modificar fechas o datos del contenedor.")
        if "invoiced" in vals or "cancelled" in vals:
            if not self.env.context.get("demurrage_transition") and not self.env.is_superuser():
                if not self.env.user.has_group(
                        "container_demurrage.group_demurrage_manager"):
                    raise UserError(
                        "No se puede modificar el estado de facturación directamente.")
        return super().write(vals)

    def action_mark_invoiced(self, invoice_reference=None, invoice_date=None):
        self.ensure_one()
        if not self.env.user.has_group(
                "container_demurrage.group_demurrage_billing"):
            raise AccessError("No tiene permisos para facturar.")
        if self.state != "returned" or not self.return_date:
            raise UserError("El contenedor debe estar devuelto para facturar.")
        if self.missing_tariff or not self.tariff_id:
            raise UserError("Falta tarifa.")
        if self.missing_exchange_rate:
            raise UserError("Falta tasa de cambio.")
        if invoice_reference is None:
            invoice_reference = "Facturación manual"
        if invoice_date is None:
            invoice_date = fields.Date.context_today(self)
        rate_result = self._get_exchange_rate(invoice_date)
        if isinstance(rate_result, tuple):
            exchange_rate, found = rate_result
        else:
            exchange_rate, found = rate_result, True
        if not found or exchange_rate is None:
            raise UserError("Falta tasa de cambio.")
        cop_amount = round(self.customer_charge_usd * exchange_rate, 2) if self.customer_charge_usd else 0.0
        self.with_context(demurrage_transition=True).write({
            "invoiced": True,
            "invoice_reference": invoice_reference,
            "invoice_date": invoice_date,
            "invoiced_at": fields.Datetime.now(),
            "invoiced_carrier_usd": self.carrier_charge_usd,
            "invoiced_customer_usd": self.customer_charge_usd,
            "invoiced_demurrage_days": self.demurrage_days,
            "invoiced_admin_fee_percent": self.admin_fee_percent,
            "invoiced_exchange_rate": exchange_rate,
            "invoiced_customer_cop": cop_amount,
        })
        return True

    def action_reopen(self, reason):
        self.ensure_one()
        if not self.env.user.has_group(
                "container_demurrage.group_demurrage_billing"):
            raise AccessError("No tiene permisos para reabrir.")
        if self.state != "invoiced":
            raise UserError("Solo se puede reabrir un contenedor facturado.")
        if not reason or not str(reason).strip():
            raise UserError("Debe indicar un motivo.")
        self.env["demurrage.correction"].create({
            "container_id": self.id,
            "reason": reason,
            "old_discharge_date": self.discharge_date,
            "old_return_date": self.return_date,
            "old_state": self.state,
        })
        self.with_context(demurrage_transition=True).write({
            "invoiced": False,
            "invoice_needs_review": True,
        })
        self.message_post(body=reason)
        return True

    def action_cancel(self, reason=None):
        self.ensure_one()
        if self.invoiced or self.state == "invoiced":
            raise UserError("No se puede cancelar un contenedor facturado.")
        self.with_context(demurrage_transition=True).write({"cancelled": True})
        self.message_post(body=reason or "Cancelado")
        return True

    def action_set_return_today(self):
        self.ensure_one()
        if not self.discharge_date:
            raise UserError("Se requiere fecha de descarga.")
        if not self.return_date:
            self.write({"return_date": fields.Date.context_today(self)})
        return True

    def action_request_correction(self, reason):
        self.ensure_one()
        self.message_post(body=reason)
        group = self.env.ref("container_demurrage.group_demurrage_billing")
        users = group.users
        user = users[0] if users else self.env.user
        self.activity_schedule(
            "mail.mail_activity_data_todo", user_id=user.id,
            summary="Solicitud de corrección", note=reason)
        return True

    def action_open_reopen_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Reabrir contenedor",
            "res_model": "demurrage.reopen.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_container_id": self.id},
        }

    def action_open_correction_request_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Solicitar corrección",
            "res_model": "demurrage.correction.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_container_id": self.id},
        }

    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cancelar contenedor",
            "res_model": "demurrage.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_container_id": self.id},
        }

    def action_open_mark_invoiced_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Marcar facturado",
            "res_model": "demurrage.mark.invoiced.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_container_id": self.id},
        }

    def action_refresh_estimate(self):
        self.ensure_one()
        if self.state == "open":
            self.write({"as_of_date": fields.Date.today()})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("container_number"):
                vals["container_number"] = normalize_container_number(
                    vals["container_number"])
            if not vals.get("discharge_date") and vals.get("bl_id"):
                bl_id = vals["bl_id"]
                if hasattr(bl_id, "id"):
                    bl_id = bl_id.id
                bl = self.env["demurrage.bl"].browse(bl_id)
                if bl.discharge_date:
                    vals["discharge_date"] = bl.discharge_date
            if not vals.get("as_of_date"):
                vals["as_of_date"] = fields.Date.today()
        return super().create(vals_list)
