# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DemurrageReopenWizard(models.TransientModel):
    _name = "demurrage.reopen.wizard"
    _description = "Asistente para reabrir contenedor"

    container_id = fields.Many2one(
        "demurrage.container", required=True,
        default=lambda self: self.env.context.get("default_container_id"))
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        self.container_id.action_reopen(self.reason)
        return {"type": "ir.actions.act_window_close"}


class DemurrageCorrectionRequestWizard(models.TransientModel):
    _name = "demurrage.correction.request.wizard"
    _description = "Asistente para solicitar corrección"

    container_id = fields.Many2one(
        "demurrage.container", required=True,
        default=lambda self: self.env.context.get("default_container_id"))
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        self.container_id.action_request_correction(self.reason)
        return {"type": "ir.actions.act_window_close"}


class DemurrageCancelWizard(models.TransientModel):
    _name = "demurrage.cancel.wizard"
    _description = "Asistente para cancelar contenedor"

    container_id = fields.Many2one(
        "demurrage.container", required=True,
        default=lambda self: self.env.context.get("default_container_id"))
    reason = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        self.container_id.action_cancel(self.reason)
        return {"type": "ir.actions.act_window_close"}


class DemurrageMarkInvoicedWizard(models.TransientModel):
    _name = "demurrage.mark.invoiced.wizard"
    _description = "Asistente para marcar facturado"

    container_id = fields.Many2one(
        "demurrage.container", required=True,
        default=lambda self: self.env.context.get("default_container_id"))
    invoice_reference = fields.Char(required=True)
    invoice_date = fields.Date(
        required=True, default=lambda self: fields.Date.context_today(self))

    def action_confirm(self):
        self.ensure_one()
        self.container_id.action_mark_invoiced(
            self.invoice_reference, self.invoice_date)
        return {"type": "ir.actions.act_window_close"}
