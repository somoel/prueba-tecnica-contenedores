# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DemurrageBL(models.Model):
    _name = "demurrage.bl"
    _description = "Bill of Lading"
    _order = "name"

    _sql_constraints = [
        (
            "name_shipping_company_unique",
            "unique(name, shipping_line_id, company_id)",
            "Ya existe un BL con ese número para la naviera y compañía.",
        ),
    ]

    name = fields.Char(required=True)
    shipping_line_id = fields.Many2one(
        "demurrage.shipping.line", required=True, ondelete="restrict")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    discharge_date = fields.Date()
    container_ids = fields.One2many(
        "demurrage.container", "bl_id", string="Contenedores")
    container_count = fields.Integer(compute="_compute_container_count", store=True)
    has_mixed_discharge_dates = fields.Boolean(
        compute="_compute_has_mixed_discharge_dates", store=True)
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.depends("container_ids")
    def _compute_container_count(self):
        for record in self:
            record.container_count = len(record.container_ids)

    @api.depends("container_ids.discharge_date")
    def _compute_has_mixed_discharge_dates(self):
        for record in self:
            dates = {c.discharge_date for c in record.container_ids if c.discharge_date}
            record.has_mixed_discharge_dates = len(dates) > 1

    @api.onchange("discharge_date")
    def _onchange_discharge_date(self):
        for record in self:
            if record.discharge_date:
                for container in record.container_ids:
                    if not container.discharge_date:
                        container.discharge_date = record.discharge_date

    def action_apply_discharge_date(self):
        for record in self:
            if record.discharge_date:
                record.container_ids.filtered(
                    lambda c: not c.discharge_date
                ).write({"discharge_date": record.discharge_date})
        return True
