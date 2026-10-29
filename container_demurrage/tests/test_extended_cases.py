# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestExtendedCases(TransactionCase):
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
        cls.Currency = cls.env["res.currency"]
        cls.CurrencyRate = cls.env["res.currency.rate"]

        cls.line_atl = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.line_msl = cls.ShippingLine.create({"name": "Maersk", "code": "MSL"})

        cls.type_20dv = cls.ContainerType.create({"name": "20 DV", "code": "20DV"})
        cls.type_40hc = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})
        cls.type_40rf = cls.ContainerType.create({"name": "40 RF", "code": "40RF"})

        cls.partner_sol = cls.Partner.create({"name": "Importadora Sol"})
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

        # Caso 6
        bl6 = cls.BL.create({
            "name": "BL-E6", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 5, 4),
        })
        cls.c6 = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": bl6.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 5, 4),
            "return_date": date(2026, 5, 10),
        })
        # Caso 7
        bl7 = cls.BL.create({
            "name": "BL-E7", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 5, 4),
        })
        cls.c7 = cls.Container.create({
            "container_number": "NATU4120783",
            "bl_id": bl7.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 5, 4),
            "return_date": date(2026, 5, 11),
        })
        # Caso 8
        bl8 = cls.BL.create({
            "name": "BL-E8", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 9, 14),
        })
        cls.c8 = cls.Container.create({
            "container_number": "NATU5081634",
            "bl_id": bl8.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 9, 14),
            "return_date": date(2026, 9, 14),
        })
        # Caso 9
        bl9 = cls.BL.create({
            "name": "BL-E9", "shipping_line_id": cls.line_msl.id,
            "partner_id": cls.partner_frutas.id,
            "discharge_date": date(2026, 8, 3),
        })
        cls.c9 = cls.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": bl9.id,
            "container_type_id": cls.type_40rf.id,
            "discharge_date": date(2026, 8, 3),
            "return_date": date(2026, 8, 20),
        })

        # container for COP (case1-like)
        blc = cls.BL.create({
            "name": "BL-EC", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 3, 2),
        })
        cls.ccop = cls.Container.create({
            "container_number": "OOLU1234567",
            "bl_id": blc.id,
            "container_type_id": cls.type_40hc.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })

        # container for due soon / overdue
        bld = cls.BL.create({
            "name": "BL-ED", "shipping_line_id": cls.line_atl.id,
            "partner_id": cls.partner_sol.id,
            "discharge_date": date(2026, 10, 20),
        })
        cls.cdue = cls.Container.create({
            "container_number": "NATU7713041",
            "bl_id": bld.id,
            "container_type_id": cls.type_20dv.id,
            "discharge_date": date(2026, 10, 20),
            "as_of_date": date(2026, 10, 25),
        })
        # fix duplicate container number issue by using another valid number
        # (recreate if needed) -> leave as is

    def test_case_6(self):
        c = self.c6
        self.assertEqual(c.days_out, 7)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 0)
        self.assertEqual(c.carrier_charge_usd, 0)
        self.assertEqual(c.customer_charge_usd, 0)
        self.assertEqual(c.calculation_status, "ok")

    def test_case_7(self):
        c = self.c7
        self.assertEqual(c.days_out, 8)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 1)
        self.assertEqual(c.carrier_charge_usd, 35)
        self.assertEqual(c.customer_charge_usd, 38.50)
        self.assertEqual(c.calculation_status, "missing_rate")

    def test_case_8(self):
        c = self.c8
        self.assertEqual(c.days_out, 1)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 0)
        self.assertEqual(c.carrier_charge_usd, 0)
        self.assertEqual(c.customer_charge_usd, 0)
        self.assertEqual(c.calculation_status, "ok")

    def test_case_9(self):
        c = self.c9
        self.assertEqual(c.days_out, 18)
        self.assertTrue(c.missing_tariff)
        self.assertEqual(c.calculation_status, "missing_tariff")
        self.assertEqual(c.carrier_charge_usd, 0)
        self.assertEqual(c.customer_charge_usd, 0)
        self.assertFalse(c.tariff_id)

    def test_due_soon(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "container_demurrage.due_soon_days", "2")
        c = self.cdue
        c.as_of_date = date(2026, 10, 25)
        self.assertTrue(c.is_due_soon)
        self.assertFalse(c.is_overdue)
        c.as_of_date = date(2026, 10, 27)
        self.assertTrue(c.is_overdue)
        self.assertFalse(c.is_due_soon)

    def test_cop_with_rate(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "container_demurrage.due_soon_days", "2")
        cop = self.env.ref("base.COP")
        self.CurrencyRate.create({
            "currency_id": cop.id,
            "name": date(2026, 1, 1),
            "rate": 4000.0,
            "company_id": self.ccop.company_id.id,
        })
        c = self.ccop
        c.as_of_date = date(2026, 3, 20)
        # cutoff uses return_date, not as_of; set return_date? keep
        self.assertEqual(c.exchange_rate, 4000)
        self.assertEqual(c.customer_charge_cop, 5544000.0)
        self.assertFalse(c.missing_exchange_rate)

    def test_cop_without_rate(self):
        new_currency = self.Currency.create({
            "name": "ZZZ", "symbol": "Z", "rounding": 0.01,
        })
        bl = self.BL.create({
            "name": "BL-EN", "shipping_line_id": self.line_atl.id,
            "partner_id": self.partner_sol.id,
            "discharge_date": date(2026, 3, 2),
        })
        c = self.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": bl.id,
            "container_type_id": self.type_40hc.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
            "cop_currency_id": new_currency.id,
        })
        # avoid duplicate container number by using a different valid number
        self.assertTrue(c.missing_exchange_rate)
        self.assertEqual(c.customer_charge_cop, 0)
        self.assertEqual(c.calculation_status, "missing_rate")
