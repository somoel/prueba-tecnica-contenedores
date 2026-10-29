# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api
from odoo.addons.container_demurrage.utils.iso6346 import normalize_container_number


class DemurrageContainer(models.Model):
    _name = "demurrage.container"
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
    state = fields.Selection(
        [("draft", "Borrador"), ("open", "Abierto"),
         ("returned", "Devuelto"), ("invoiced", "Facturado"),
         ("cancelled", "Cancelado")],
        compute="_compute_state", store=True)
    notes = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related="bl_id.company_id", store=True, readonly=True)

    @api.depends("container_number")
    def _compute_name(self):
        for record in self:
            record.name = record.container_number

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
