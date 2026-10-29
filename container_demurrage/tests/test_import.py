# -*- coding: utf-8 -*-
from datetime import date
from pathlib import Path

from odoo.tests.common import TransactionCase


class TestImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.Partner = cls.env["res.partner"]
        cls.Agreement = cls.env["demurrage.customer.agreement"]
        cls.Wizard = cls.env["demurrage.import.wizard"]
        cls.Line = cls.env["demurrage.import.line"]
        cls.Container = cls.env["demurrage.container"]
        cls.BL = cls.env["demurrage.bl"]

        cls.atl = cls.ShippingLine.create({"name": "Naviera Atlántico", "code": "ATL"})
        cls.msl = cls.ShippingLine.create({"name": "Mar del Sur Line", "code": "MSL"})

        cls.t20dv = cls.ContainerType.create({"name": "20 DV", "code": "20DV"})
        cls.t40dv = cls.ContainerType.create({"name": "40 DV", "code": "40DV"})
        cls.t40hc = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})
        cls.t40rf = cls.ContainerType.create({"name": "40 RF", "code": "40RF"})

        cls.Tariff.create({
            "shipping_line_id": cls.atl.id,
            "container_type_id": cls.t40hc.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 60}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 120}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 180}),
            ],
        })
        cls.Tariff.create({
            "shipping_line_id": cls.atl.id,
            "container_type_id": cls.t20dv.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 35}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 70}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 110}),
            ],
        })
        cls.Tariff.create({
            "shipping_line_id": cls.atl.id,
            "container_type_id": cls.t40rf.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 4,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 150}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 250}),
            ],
        })
        cls.Tariff.create({
            "shipping_line_id": cls.msl.id,
            "container_type_id": cls.t40dv.id,
            "valid_from": date(2026, 1, 1),
            "valid_to": date(2026, 6, 30),
            "free_days": 10,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 75}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 150}),
            ],
        })
        cls.Tariff.create({
            "shipping_line_id": cls.msl.id,
            "container_type_id": cls.t20dv.id,
            "valid_from": date(2026, 7, 1),
            "free_days": 8,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 45}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 95}),
            ],
        })

        cls.sol = cls.Partner.create({"name": "Importadora Sol S.A.S."})
        cls.tornillo = cls.Partner.create({"name": "Ferretería El Tornillo S.A.S."})
        cls.textiles = cls.Partner.create({"name": "Textiles Andinos Ltda."})
        cls.frutas = cls.Partner.create({"name": "Frutas del Valle Export S.A.S."})

        cls.Agreement.create({
            "partner_id": cls.tornillo.id,
            "shipping_line_id": cls.atl.id,
            "extra_free_days": 5,
            "admin_fee_percent": 10.0,
        })
        cls.Agreement.create({
            "partner_id": cls.textiles.id,
            "shipping_line_id": cls.msl.id,
            "extra_free_days": 3,
            "admin_fee_percent": 5.0,
        })

        cls.csv_path = Path(__file__).parent / "data" / "control_contenedores_2026.csv"

    def _make_wizard(self):
        wiz = self.Wizard.create({"company_id": self.env.company.id})
        data = self.csv_path.read_bytes()
        wiz.write({"file": data, "filename": self.csv_path.name})
        return wiz

    def test_analyze(self):
        wiz = self._make_wizard()
        wiz.action_analyze()
        self.assertEqual(wiz.state, "analyzed")
        self.assertEqual(len(wiz.line_ids), 10)
        self.assertEqual(wiz.total_count, 10)
        rejected = wiz.line_ids.filtered(lambda l: l.status == "rejected")
        importable = wiz.line_ids.filtered(lambda l: l.status in ("ok", "normalized", "warning"))
        self.assertEqual(len(rejected), 4)
        self.assertEqual(len(importable), 6)
        rejected_rows = sorted(rejected.mapped("row_number"))
        self.assertEqual(rejected_rows, [5, 6, 7, 8])
        msg5 = wiz.line_ids.filtered(lambda l: l.row_number == 5).message
        self.assertIn("Duplicado", msg5)
        msg6 = wiz.line_ids.filtered(lambda l: l.row_number == 6).message
        self.assertIn("contenedor", msg6.lower())
        msg7 = wiz.line_ids.filtered(lambda l: l.row_number == 7).message
        self.assertTrue("devolución" in msg7.lower() or "fecha" in msg7.lower())
        msg8 = wiz.line_ids.filtered(lambda l: l.row_number == 8).message
        self.assertIn("Cliente", msg8)
        row10 = wiz.line_ids.filtered(lambda l: l.row_number == 10)
        self.assertEqual(row10.status, "warning")
        self.assertTrue("tarifa" in row10.message.lower() or "Sin tarifa" in row10.message)

    def test_import(self):
        wiz = self._make_wizard()
        wiz.action_analyze()
        wiz.action_import()
        self.assertEqual(wiz.state, "done")
        self.assertEqual(wiz.imported_count, 6)
        self.assertEqual(wiz.rejected_count, 4)
        self.assertGreaterEqual(wiz.warning_count, 1)
        bl = self.BL.search([("name", "=", "NAT-26-0311")])
        self.assertEqual(len(bl.container_ids), 2)
        row3 = wiz.line_ids.filtered(lambda l: l.row_number == 3)
        c = row3.container_id
        self.assertAlmostEqual(c.carrier_charge_usd, 375.0, places=2)
        self.assertAlmostEqual(c.customer_charge_usd, 393.75, places=2)
        row10 = wiz.line_ids.filtered(lambda l: l.row_number == 10)
        self.assertTrue(row10.container_id.missing_tariff)

    def test_second_import(self):
        wiz1 = self._make_wizard()
        wiz1.action_analyze()
        wiz1.action_import()
        wiz2 = self._make_wizard()
        wiz2.action_analyze()
        wiz2.action_import()
        self.assertEqual(wiz2.imported_count, 0)
        self.assertEqual(self.Container.search_count([]), 6)
