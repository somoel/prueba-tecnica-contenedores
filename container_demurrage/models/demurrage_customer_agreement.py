# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DemurrageCustomerAgreement(models.Model):
    _name = "demurrage.customer.agreement"
    _description = "Acuerdo por cliente y naviera"
    _order = "partner_id, shipping_line_id"

    _sql_constraints = [
        (
            "partner_shipping_company_unique",
            "unique(partner_id, shipping_line_id, company_id)",
            "Ya existe un acuerdo para este cliente, naviera y compañía.",
        ),
    ]

    partner_id = fields.Many2one(
        "res.partner", required=True, ondelete="cascade")
    shipping_line_id = fields.Many2one(
        "demurrage.shipping.line", required=True, ondelete="restrict")
    extra_free_days = fields.Integer(required=True, default=0)
    admin_fee_percent = fields.Float(required=True, default=10.0)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.constrains("extra_free_days")
    def _check_extra_free_days(self):
        for record in self:
            if record.extra_free_days < 0:
                raise ValidationError(
                    "Los días libres adicionales no pueden ser negativos.")

    @api.constrains("admin_fee_percent")
    def _check_admin_fee_percent(self):
        for record in self:
            if record.admin_fee_percent < 0 or record.admin_fee_percent > 100:
                raise ValidationError(
                    "El porcentaje de gastos administrativos debe estar entre 0 y 100.")
