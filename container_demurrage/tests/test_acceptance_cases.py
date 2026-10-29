# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase


class TestAcceptanceCases(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.Agreement = cls.env["demurrage.customer.agreement"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]

        cls.line_atl = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.line_msl = cls.ShippingLine.create({"name": "Maersk", "code": "MSL"})

        cls.type_20dv = cls.ContainerType.create({"name": "20 DV", "code": "20DV"})
        cls.type_40dv = cls.ContainerType.create({"name": "40 DV", "code": "40DV"})
        cls.type_40hc = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})
        cls.type_40rf = cls.ContainerType.create({"name": "40 RF", "code": "40RF"})

        cls.partner_sol = cls.Partner.create({"name": "Importadora Sol"})
        cls.partner_ferreteria = cls.Partner.create({"name": "Ferreteria El Tornillo"})
        cls.partner_textiles = cls.Partner.create({"name": "Textiles Andinos"})
        cls.partner_frutas = cls.Partner.create({"name": "Frutas del Valle"})

        cls.tariff_atl_20dv = cls.Tariff.create({
            "shipping_line_id": cls.line_atl.id,
            "container_type_id": cls.type_20dv.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 35}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 70}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 110}),
            ],
        })
        cls.tariff_atl_40hc = cls.Tariff.create({
            "shipping_line_id": cls.line_atl.id,
            "container_type_id": cls.type_40hc.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 60}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 120}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 180}),
            ],
        })
        cls.tariff_atl_40rf = cls.Tariff.create({
            "shipping_line_id": cls.line_atl.id,
            "container_type_id": cls.type_40rf.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 4,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 150}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 250}),
            ],
        })
        cls.tariff_msl_20dv_old = cls.Tariff.create({
            "shipping_line_id": cls.line_msl.id,
            "container_type_id": cls.type_20dv.id,
            "valid_from": date(2026, 1, 1),
            "valid_to": date(2026, 6, 30),
            "free_days": 10,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 7, "rate_per_day": 40}),
                (0, 0, {"day_from": 8, "day_to": 0, "rate_per_day": 85}),
            ],
        })
        cls.tariff_msl_20dv_new = cls.Tariff.create({
            "shipping_line_id": cls.line_msl.id,
            "container_type_id": cls.type_20dv.id,
            "valid_from": date(2026, 7, 1),
            "free_days": 8,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 7, "rate_per_day": 45}),
                (0, 0, {"day_from": 8, "day_to": 0, "rate_per_day": 95}),
            ],
        })
        cls.tariff_msl_40dv_old = cls.Tariff.create({
            "shipping_line_id": cls.line_msl.id,
            "container_type_id": cls.type_40dv.id,
            "valid_from": date(2026, 1, 1),
            "valid_to": date(2026, 6, 30),
            "free_days": 10,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 7, "rate_per_day": 75}),
                (0, 0, {"day_from": 8, "day_to": 0, "rate_per_day": 150}),
            ],
        })

        cls.agreement_ferreteria = cls.Agreement.create({
            "partner_id": cls.partner_ferreteria.id,
            "shipping_line_id": cls.line_atl.id,
            "extra_free_days": 5,
            "admin_fee_percent": 10.0,
        })
        cls.agreement_textiles = cls.Agreement.create({
            "partner_id": cls.partner_textiles.id,
            "shipping_line_id": cls.line_msl.id,
            "extra_free_days": 3,
            "admin_fee_percent": 5.0,
        })

        bl1 = cls.BL.create({
            "name": "BL-C1", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 3, 2),
        })
        cls.c1 = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": bl1.id,
            "container_type_id": cls.type_40hc.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })

        bl2 = cls.BL.create({
            "name": "BL-C2", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_ferreteria.id,
            "discharge_date": date(2026, 4, 10),
        })
        cls.c2 = cls.Container.create({
            "container_number": "NATU4120783",
            "bl_id": bl2.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 4, 10),
            "return_date": date(2026, 4, 21),
        })

        bl3 = cls.BL.create({
            "name": "BL-C3", "shipping_line_id": cls.line_msl.id,
            "partner_id": cls.partner_textiles.id,
            "discharge_date": date(2026, 6, 28),
        })
        cls.c3 = cls.Container.create({
            "container_number": "NATU5081634",
            "bl_id": bl3.id,
            "container_type_id": cls.type_40dv.id,
            "discharge_date": date(2026, 6, 28),
            "return_date": date(2026, 7, 15),
        })

        bl4 = cls.BL.create({
            "name": "BL-C4", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_frutas.id,
            "discharge_date": date(2026, 8, 1),
        })
        cls.c4 = cls.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": bl4.id,
            "container_type_id": cls.type_40rf.id,
            "discharge_date": date(2026, 8, 1),
            "return_date": date(2026, 8, 14),
        })

        bl5 = cls.BL.create({
            "name": "BL-C5", "shipping_line_id": cls.line_msl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 9, 5),
        })
        cls.c5 = cls.Container.create({
            "container_number": "NATU7713041",
            "bl_id": bl5.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 9, 5),
            "as_of_date": date(2026, 9, 20),
        })

    def test_case_1(self):
        c = self.c1
        self.assertEqual(c.days_out, 19)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 12)
        self.assertEqual(c.carrier_charge_usd, 1260)
        self.assertEqual(c.customer_charge_usd, 1386)
        self.assertFalse(c.is_estimate)
        self.assertEqual(c.calculation_status, "ok")
        self.assertEqual(c.admin_fee_percent, 10.0)

    def test_case_2(self):
        c = self.c2
        self.assertEqual(c.days_out, 12)
        self.assertEqual(c.free_days, 12)
        self.assertEqual(c.demurrage_days, 0)
        self.assertEqual(c.carrier_charge_usd, 0)
        self.assertEqual(c.customer_charge_usd, 0)
        self.assertEqual(c.calculation_status, "ok")

    def test_case_3(self):
        c = self.c3
        self.assertEqual(c.days_out, 18)
        self.assertEqual(c.free_days, 13)
        self.assertEqual(c.demurrage_days, 5)
        self.assertEqual(c.carrier_charge_usd, 375)
        self.assertEqual(c.customer_charge_usd, 393.75)
        self.assertEqual(c.tariff_id, self.tariff_msl_40dv_old)
        self.assertEqual(c.admin_fee_percent, 5.0)
        self.assertEqual(c.calculation_status, "ok")

    def test_case_4(self):
        c = self.c4
        self.assertEqual(c.days_out, 14)
        self.assertEqual(c.free_days, 4)
        self.assertEqual(c.demurrage_days, 10)
        self.assertEqual(c.carrier_charge_usd, 2000)
        self.assertEqual(c.customer_charge_usd, 2200)
        self.assertEqual(c.calculation_status, "ok")

    def test_case_5(self):
        c = self.c5
        self.assertEqual(c.days_out, 16)
        self.assertEqual(c.free_days, 8)
        self.assertEqual(c.demurrage_days, 8)
        self.assertEqual(c.carrier_charge_usd, 410)
        self.assertEqual(c.customer_charge_usd, 451)
        self.assertTrue(c.is_estimate)
        self.assertEqual(c.tariff_id, self.tariff_msl_20dv_new)
        self.assertEqual(c.calculation_status, "ok")

    def test_fallback_admin_fee_sol(self):
        self.assertEqual(self.c1.admin_fee_percent, 10.0)

    def test_tier_breakdown_contains_expected(self):
        self.assertIn("USD 180,00", self.c1.tier_breakdown)
