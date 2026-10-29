# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    default_admin_fee_percent = fields.Float(
        config_parameter="container_demurrage.default_admin_fee_percent",
        default=10.0)
    due_soon_days = fields.Integer(
        config_parameter="container_demurrage.due_soon_days",
        default=2)
