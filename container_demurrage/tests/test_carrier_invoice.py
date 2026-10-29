# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestCarrierInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.Invoice = cls.env["demurrage.carrier.invoice"]

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
        # ensure 1260
        assert cls.container.carrier_charge_usd == 1260, cls.container.carrier_charge_usd

    def _invoice_vals(self, **kwargs):
        vals = {
            "name": "INV-001",
            "shipping_line_id": self.line.id,
            "invoice_date": date(2026, 3, 25),
        }
        vals.update(kwargs)
        return vals

    def test_invoice_line_variance_overbilled(self):
        inv = self.Invoice.create(self._invoice_vals())
        line = self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv.id,
            "container_id": self.container.id,
            "amount_usd": 1300.0,
        })
        self.assertEqual(line.expected_usd, 1260.0)
        self.assertEqual(line.variance_usd, 40.0)
        self.assertEqual(inv.total_usd, 1300.0)
        self.assertTrue(self.container.carrier_overbilled)
        self.assertEqual(self.container.carrier_variance_usd, 40.0)
        self.assertEqual(self.container.carrier_invoiced_usd, 1300.0)

    def test_invoice_line_variance_underbilled(self):
        inv = self.Invoice.create(self._invoice_vals(name="INV-002"))
        line = self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv.id,
            "container_id": self.container.id,
            "amount_usd": 1200.0,
        })
        self.assertEqual(line.variance_usd, -60.0)
        self.assertFalse(self.container.carrier_overbilled)

    def test_expected_snapshot_not_changed_by_tariff(self):
        inv = self.Invoice.create(self._invoice_vals(name="INV-003"))
        line = self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv.id,
            "container_id": self.container.id,
            "amount_usd": 1260.0,
        })
        # change tariff rates
        self.tariff.tier_ids[0].rate_per_day = 999
        self.env.cr.flush()
        self.assertEqual(line.expected_usd, 1260.0)
        self.assertEqual(line.variance_usd, 0.0)

    def test_unique_invoice_container(self):
        inv = self.Invoice.create(self._invoice_vals(name="INV-004"))
        self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv.id,
            "container_id": self.container.id,
            "amount_usd": 1260.0,
        })
        with self.assertRaises(ValidationError):
            self.env["demurrage.carrier.invoice.line"].create({
                "invoice_id": inv.id,
                "container_id": self.container.id,
                "amount_usd": 1260.0,
            })

    def test_aggregation_two_lines(self):
        inv1 = self.Invoice.create(self._invoice_vals(name="INV-005"))
        c2_bl = self.BL.create({
            "name": "BL002", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
            "discharge_date": date(2026, 3, 2),
        })
        c2 = self.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": c2_bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })
        self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv1.id,
            "container_id": self.container.id,
            "amount_usd": 1300.0,
        })
        self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv1.id,
            "container_id": c2.id,
            "amount_usd": 1200.0,
        })
        self.assertEqual(self.container.carrier_invoiced_usd, 1300.0)
        self.assertEqual(c2.carrier_invoiced_usd, 1200.0)

    def test_total_usd_sum(self):
        inv = self.Invoice.create(self._invoice_vals(name="INV-006"))
        self.env["demurrage.carrier.invoice.line"].create({
            "invoice_id": inv.id,
            "container_id": self.container.id,
            "amount_usd": 1300.0,
        })
        self.assertEqual(inv.total_usd, 1300.0)
