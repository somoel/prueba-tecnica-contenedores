# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    agreement_ids = fields.One2many(
        "demurrage.customer.agreement", "partner_id", string="Acuerdos")
