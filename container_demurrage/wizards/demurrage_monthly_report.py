# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api


class DemurrageMonthlyReportWizard(models.TransientModel):
    _name = "demurrage.monthly.report.wizard"
    _description = "Reporte mensual de demoras"

    date_from = fields.Date(
        required=True, default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(required=True, default=lambda self: date.today())
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company)

    def _get_rows(self):
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        company = self.company_id

        paid = {}
        carriers = {}
        customers = {}

        carrier_invoices = self.env["demurrage.carrier.invoice"].search([
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
            ("company_id", "=", company.id),
        ])
        for inv in carrier_invoices:
            for line in inv.line_ids:
                container = line.container_id
                customer = container.partner_id
                carrier = inv.shipping_line_id
                key = (customer.id, carrier.id)
                paid[key] = paid.get(key, 0.0) + (line.amount_usd or 0.0)
                customers[key] = customer.name
                carriers[key] = carrier.name

        containers = self.env["demurrage.container"].search([
            ("invoiced", "=", True),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
            ("company_id", "=", company.id),
        ])
        recovered = {}
        for c in containers:
            customer = c.partner_id
            carrier = c.shipping_line_id
            key = (customer.id, carrier.id)
            recovered[key] = recovered.get(key, 0.0) + (c.invoiced_customer_usd or 0.0)
            customers[key] = customer.name
            carriers[key] = carrier.name

        rows = []
        for key in sorted(set(paid) | set(recovered)):
            p = paid.get(key, 0.0)
            r = recovered.get(key, 0.0)
            rows.append({
                "customer": customers.get(key),
                "carrier": carriers.get(key),
                "paid": p,
                "recovered": r,
                "difference": r - p,
            })
        return rows

    def action_print(self):
        self.ensure_one()
        rows = self._get_rows()
        report = self.env.ref("container_demurrage.action_report_demurrage_monthly")
        return report.report_action(
            self,
            data={
                "rows": rows,
                "date_from": self.date_from,
                "date_to": self.date_to,
            },
        )
