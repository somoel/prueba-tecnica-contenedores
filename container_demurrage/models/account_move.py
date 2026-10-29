# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    demurrage_container_ids = fields.One2many(
        "demurrage.container", "invoice_id", string="Contenedores")

    def write(self, vals):
        res = super().write(vals)
        if "invoice_date" in vals:
            for move in self:
                if move.state == "draft" and move.demurrage_container_ids:
                    for container in move.demurrage_container_ids:
                        container._refresh_invoice_snapshot(move.invoice_date)
        return res