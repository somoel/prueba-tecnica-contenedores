# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError


class DemurrageInvoiceWizard(models.TransientModel):
    _name = "demurrage.invoice.wizard"
    _description = "Asistente para facturar contenedores"

    partner_id = fields.Many2one("res.partner", required=True)
    container_ids = fields.Many2many(
        "demurrage.container", required=True,
        domain="[('state','=','returned'),('invoice_id','=',False),"
               "('missing_tariff','=',False),('missing_exchange_rate','=',False)]")
    invoice_date = fields.Date(
        required=True, default=lambda self: fields.Date.context_today(self))

    def action_create_invoice(self):
        self.ensure_one()
        if not self.env.is_superuser() and not (
                self.env.user.has_group(
                    "container_demurrage.group_demurrage_billing")
                or self.env.user.has_group(
                    "container_demurrage.group_demurrage_manager")):
            raise AccessError("No tiene permisos para facturar.")
        containers = self.container_ids
        if not containers:
            raise UserError("Debe seleccionar al menos un contenedor.")

        partners = containers.mapped("partner_id")
        if len(partners) != 1 or partners != self.partner_id:
            raise UserError(
                "Todos los contenedores deben pertenecer al mismo cliente.")

        for c in containers:
            if c.state != "returned" or c.invoiced:
                raise UserError(
                    "El contenedor %s no está devuelto o ya está facturado."
                    % c.container_number)
            if c.missing_tariff or not c.tariff_id:
                raise UserError("Falta tarifa para %s." % c.container_number)

        journal = self.env["account.journal"].search(
            [("type", "=", "sale")], limit=1)
        if not journal:
            raise UserError("No se encontró un diario de venta.")

        product = self.env.ref(
            "container_demurrage.product_demurrage_service",
            raise_if_not_found=False)
        if not product:
            product = self.env["product.product"].search(
                [("name", "=", "Demora de contenedor")], limit=1)
        if not product:
            raise UserError("No se encontró el producto de demora.")

        income_account = (product.property_account_income_id
                          or product.categ_id.property_account_income_categ_id)
        if not income_account:
            income_account = self.env["account.account"].search(
                [("account_type", "=", "income")], limit=1)
        if not income_account:
            found = self.env["account.account"].search([("account_type", "=", "income")])
            if found:
                income_account = found[:1]
            else:
                income_account = self.env["account.account"].create({
                    "name": "Ingresos demora",
                    "code": "499999",
                    "account_type": "income",
                })
        if not income_account:
            raise UserError("NO INCOME ACCOUNT")

        cop = self.env.ref("base.COP")

        receivable = self.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1)
        if not receivable:
            receivable = self.env["account.account"].create({
                "name": "Clientes",
                "code": "110001",
                "account_type": "asset_receivable",
            })
        self.partner_id.property_account_receivable_id = receivable.id

        # Validate TRM per container and compute price units
        line_vals = []
        bl_names = []
        for c in containers:
            rate_result = c._get_exchange_rate(self.invoice_date)
            if isinstance(rate_result, tuple):
                exchange_rate, found = rate_result
            else:
                exchange_rate, found = rate_result, True
            if not found or not exchange_rate:
                raise UserError(
                    "Falta tasa de cambio para %s." % c.container_number)
            price_unit = round(c.customer_charge_usd * exchange_rate, 2)
            line_vals.append((0, 0, {
                "name": "Demora %s — BL %s — %s días"
                % (c.container_number, c.bl_id.name, c.demurrage_days),
                "product_id": product.id,
                "quantity": 1,
                "price_unit": price_unit,
                "account_id": income_account.id,
                "display_type": "product",
                "tax_ids": [(6, 0, [])],
            }))
            if c.bl_id.name not in bl_names:
                bl_names.append(c.bl_id.name)

        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": journal.id,
            "currency_id": cop.id,
            "invoice_date": self.invoice_date,
            "invoice_origin": ", ".join(bl_names),
            "invoice_payment_term_id": False,
            "invoice_line_ids": line_vals,
        })
        move.write({"partner_id": self.partner_id.id,
                    "invoice_payment_term_id": False})

        reference = move.name or move.ref or "Factura demora"
        for c in containers:
            c.action_mark_invoiced(reference, self.invoice_date)
            c.write({"invoice_id": move.id})

        return {
            "type": "ir.actions.act_window",
            "name": "Factura",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }