# -*- coding: utf-8 -*-
from odoo import models, fields


class DemurrageShippingLine(models.Model):
    _name = "demurrage.shipping.line"
    _description = "Naviera"
    _order = "name"

    _sql_constraints = [
        (
            "code_unique",
            "unique(code)",
            "El código de la naviera debe ser único.",
        ),
    ]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    notes = fields.Text()
    active = fields.Boolean(default=True)
