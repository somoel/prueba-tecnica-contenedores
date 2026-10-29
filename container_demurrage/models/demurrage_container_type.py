# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DemurrageContainerType(models.Model):
    _name = "demurrage.container.type"
    _description = "Tipo de contenedor"
    _order = "code"

    _sql_constraints = [
        (
            "code_unique",
            "unique(code)",
            "El código del tipo de contenedor debe ser único.",
        ),
    ]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            if record.code and record.name:
                record.display_name = f"{record.code} - {record.name}"
            else:
                record.display_name = record.name or record.code or ""
