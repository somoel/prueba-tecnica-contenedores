# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DemurrageCarrierInvoice(models.Model):
    _name = "demurrage.carrier.invoice"
    _description = "Factura de naviera"
    _order = "invoice_date desc, name"

    name = fields.Char(required=True)
    shipping_line_id = fields.Many2one(
        "demurrage.shipping.line", required=True, ondelete="restrict")
    invoice_date = fields.Date(required=True)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda self: self.env.ref("base.USD"))
    attachment_ids = fields.Many2many(
        "ir.attachment", "carrier_invoice_attachment_rel",
        "invoice_id", "attachment_id", string="Adjuntos")
    line_ids = fields.One2many(
        "demurrage.carrier.invoice.line", "invoice_id", string="Líneas")
    total_usd = fields.Monetary(
        compute="_compute_total_usd", store=True, currency_field="currency_id")
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_shipping_line_company_unique",
         "unique(name, shipping_line_id, company_id)",
         "Ya existe una factura de naviera con ese número para la naviera."),
    ]

    @api.constrains("name", "shipping_line_id", "company_id")
    def _check_unique_invoice(self):
        for record in self:
            domain = [
                ("name", "=", record.name),
                ("shipping_line_id", "=", record.shipping_line_id.id),
                ("company_id", "=", record.company_id.id),
                ("id", "!=", record.id),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    "Ya existe una factura de naviera con ese número para la naviera.")


    @api.depends("line_ids.amount_usd")
    def _compute_total_usd(self):
        for record in self:
            record.total_usd = sum(record.line_ids.mapped("amount_usd"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = vals.get("name")
            sl = vals.get("shipping_line_id")
            company = vals.get("company_id") or self.env.company.id
            if name and sl:
                if self.search_count([
                    ("name", "=", name),
                    ("shipping_line_id", "=", sl),
                    ("company_id", "=", company),
                ]):
                    raise ValidationError(
                        "Ya existe una factura de naviera con ese número para la naviera.")
        return super(DemurrageCarrierInvoice, self).create(vals_list)


class DemurrageCarrierInvoiceLine(models.Model):
    _name = "demurrage.carrier.invoice.line"
    _description = "Línea de factura de naviera"

    invoice_id = fields.Many2one(
        "demurrage.carrier.invoice", required=True, ondelete="cascade")
    container_id = fields.Many2one(
        "demurrage.container", required=True, ondelete="restrict")
    amount_usd = fields.Monetary(required=True, currency_field="currency_id")
    expected_usd = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        related="invoice_id.currency_id", store=True, readonly=True)
    variance_usd = fields.Monetary(
        compute="_compute_variance_usd", store=True, currency_field="currency_id")
    note = fields.Char()

    _sql_constraints = [
        ("invoice_container_unique",
         "unique(invoice_id, container_id)",
         "El contenedor ya está incluido en esta factura."),
    ]

    @api.constrains("invoice_id", "container_id")
    def _check_unique_line(self):
        for record in self:
            domain = [
                ("invoice_id", "=", record.invoice_id.id),
                ("container_id", "=", record.container_id.id),
                ("id", "!=", record.id),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    "El contenedor ya está incluido en esta factura.")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inv = vals.get("invoice_id")
            cont = vals.get("container_id")
            if inv and cont:
                if self.search_count([
                    ("invoice_id", "=", inv),
                    ("container_id", "=", cont),
                ]):
                    raise ValidationError(
                        "El contenedor ya está incluido en esta factura.")
            if "expected_usd" not in vals and vals.get("container_id"):
                container = self.env["demurrage.container"].browse(
                    vals["container_id"])
                vals["expected_usd"] = container.carrier_charge_usd
        return super().create(vals_list)

    @api.depends("amount_usd", "expected_usd")
    def _compute_variance_usd(self):
        for record in self:
            record.variance_usd = (record.amount_usd or 0.0) - (record.expected_usd or 0.0)
