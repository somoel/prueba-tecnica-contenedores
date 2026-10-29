# -*- coding: utf-8 -*-
from odoo import models


class ReportDemurrageMonthly(models.AbstractModel):
    _name = "report.container_demurrage.report_demurrage_monthly"
    _description = "Reporte mensual de demoras"

    def _get_report_values(self, docids, data=None):
        data = data or {}
        wizard = self.env["demurrage.monthly.report.wizard"].browse(docids)
        if wizard and wizard.exists():
            wiz = wizard[0]
            rows = data.get("rows")
            if rows is None:
                rows = wiz._get_rows()
            date_from = data.get("date_from") or wiz.date_from
            date_to = data.get("date_to") or wiz.date_to
        else:
            rows = data.get("rows", [])
            date_from = data.get("date_from")
            date_to = data.get("date_to")
        return {
            "doc_ids": docids,
            "doc_model": "demurrage.monthly.report.wizard",
            "docs": wizard,
            "rows": rows,
            "date_from": date_from,
            "date_to": date_to,
        }
