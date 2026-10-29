# -*- coding: utf-8 -*-
from odoo import models, fields


class DemurrageCorrection(models.Model):
    _name = "demurrage.correction"
    _description = "Corrección de contenedor"
    _order = "date desc"

    container_id = fields.Many2one(
        "demurrage.container", required=True, ondelete="cascade")
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, readonly=True)
    reason = fields.Text(required=True)
    date = fields.Datetime(default=lambda self: fields.Datetime.now())
    old_discharge_date = fields.Date()
    old_return_date = fields.Date()
    old_state = fields.Char()
    note = fields.Text()