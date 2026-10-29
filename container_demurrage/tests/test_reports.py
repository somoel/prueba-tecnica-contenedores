# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase


class TestReports(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.CarrierInvoice = cls.env["demurrage.carrier.invoice"]
        cls.CarrierLine = cls.env["demurrage.carrier.invoice.line"]
        cls.Wizard = cls.env["demurrage.monthly.report.wizard"]

        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.ctype = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})

        cls.tariff = cls.Tariff.create({
            "shipping_line_id": cls.line.id,
            "container_type_id": cls.ctype.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 60}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 120}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 180}),
            ],
        })

        bl = cls.BL.create({
            "name": "BL001", "shipping_line_id": cls.line.id,
            "partner_id": cls.partner.id,
            "discharge_date": date(2026, 3, 2),
        })
        cls.container = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })
        cop = cls.env.ref("base.COP")
        cls.env["res.currency.rate"].create({
            "currency_id": cop.id,
            "name": date(2026, 1, 1),
            "rate": 4000.0,
            "company_id": cls.container.company_id.id,
        })
        assert cls.container.customer_charge_usd == 1386.0
        assert cls.container.carrier_charge_usd == 1260.0

        # mark invoiced to customer
        cls.container.action_mark_invoiced(
            invoice_reference="INV-CUST", invoice_date=date(2026, 3, 25))

        # carrier invoice with line 1000
        cls.carrier_invoice = cls.CarrierInvoice.create({
            "name": "CINV-1",
            "shipping_line_id": cls.line.id,
            "invoice_date": date(2026, 3, 25),
        })
        cls.CarrierLine.create({
            "invoice_id": cls.carrier_invoice.id,
            "container_id": cls.container.id,
            "amount_usd": 1000.0,
        })

    def test_settlement_report_html(self):
        report = self.env.ref("container_demurrage.action_report_demurrage_settlement")
        html, _ = report._render_qweb_html(report, [self.container.id])
        text = html.decode() if isinstance(html, (bytes, bytearray)) else html
        self.assertIn("CSQU3054383", text)
        self.assertIn("Días 1–5", text)
        self.assertTrue("1.260,00" in text or "1260" in text)

    def test_monthly_report_rows_and_html(self):
        wizard = self.Wizard.create({
            "date_from": date(2026, 3, 1),
            "date_to": date(2026, 3, 31),
        })
        rows = wizard._get_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertAlmostEqual(row["paid"], 1000.0)
        self.assertAlmostEqual(row["recovered"], 1386.0)
        self.assertAlmostEqual(row["difference"], 386.0)

        # out of range
        wizard2 = self.Wizard.create({
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 30),
        })
        self.assertEqual(wizard2._get_rows(), [])

        report = self.env.ref("container_demurrage.action_report_demurrage_monthly")
        html, _ = report._render_qweb_html(
            report, [wizard.id],
            data={"rows": rows, "date_from": wizard.date_from,
                  "date_to": wizard.date_to})
        text = html.decode() if isinstance(html, (bytes, bytearray)) else html
        self.assertIn(self.partner.name, text)
        self.assertIn(self.line.name, text)
