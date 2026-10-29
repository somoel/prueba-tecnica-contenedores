# -*- coding: utf-8 -*-
from datetime import date

from decimal import Decimal

from odoo.tests.common import TransactionCase

from odoo.addons.container_demurrage.utils.dates import (
    days_between,
    last_free_day,
)
from odoo.addons.container_demurrage.utils.calculator import (
    Tier,
    BreakdownLine,
    Calculation,
    calculate,
)


class TestDates(TransactionCase):
    def test_days_between_inclusive(self):
        self.assertEqual(
            days_between(date(2026, 3, 2), date(2026, 3, 20)), 19
        )

    def test_days_between_same_day(self):
        self.assertEqual(days_between(date(2026, 3, 2), date(2026, 3, 2)), 1)

    def test_days_between_end_before_discharge_raises(self):
        with self.assertRaises(ValueError):
            days_between(date(2026, 3, 20), date(2026, 3, 2))

    def test_last_free_day_seven_days(self):
        self.assertEqual(
            last_free_day(date(2026, 3, 2), 7), date(2026, 3, 8)
        )

    def test_last_free_day_zero(self):
        self.assertEqual(
            last_free_day(date(2026, 3, 2), 0), date(2026, 3, 1)
        )


class TestCalculator(TransactionCase):
    def test_twelve_demurrage_days(self):
        tiers = [
            Tier(1, 5, Decimal("60")),
            Tier(6, 10, Decimal("120")),
            Tier(11, None, Decimal("180")),
        ]
        result = calculate(22, 10, tiers)
        self.assertEqual(result.demurrage_days, 12)
        self.assertEqual(result.carrier_amount, Decimal("1260.00"))
        self.assertEqual(result.customer_amount, Decimal("1386.00"))
        self.assertEqual(len(result.lines), 3)
        self.assertEqual(result.lines[0].days, 5)
        self.assertEqual(result.lines[1].days, 5)
        self.assertEqual(result.lines[2].days, 2)

    def test_ten_demurrage_days(self):
        tiers = [
            Tier(1, 5, Decimal("150")),
            Tier(6, None, Decimal("250")),
        ]
        result = calculate(10, 0, tiers)
        self.assertEqual(result.carrier_amount, Decimal("2000.00"))
        self.assertEqual(result.customer_amount, Decimal("2200.00"))

    def test_five_days_admin_five(self):
        tiers = [Tier(1, None, Decimal("75"))]
        result = calculate(5, 0, tiers, admin_percent=Decimal("5"))
        self.assertEqual(result.carrier_amount, Decimal("375.00"))
        self.assertEqual(result.customer_amount, Decimal("393.75"))

    def test_zero_demurrage(self):
        tiers = [Tier(1, 5, Decimal("60"))]
        result = calculate(5, 5, tiers)
        self.assertEqual(result.demurrage_days, 0)
        self.assertEqual(result.carrier_amount, Decimal("0.00"))
        self.assertEqual(result.customer_amount, Decimal("0.00"))
        self.assertEqual(result.lines, ())

    def test_border_five_vs_six(self):
        tiers = [
            Tier(1, 5, Decimal("35")),
            Tier(6, None, Decimal("70")),
        ]
        r5 = calculate(5, 0, tiers)
        self.assertEqual(r5.carrier_amount, Decimal("175.00"))
        r6 = calculate(6, 0, tiers)
        self.assertEqual(r6.carrier_amount, Decimal("245.00"))

    def test_border_ten_vs_eleven(self):
        tiers = [
            Tier(1, 5, Decimal("35")),
            Tier(6, 10, Decimal("70")),
            Tier(11, None, Decimal("100")),
        ]
        r10 = calculate(10, 0, tiers)
        self.assertEqual(r10.carrier_amount, Decimal("525.00"))
        r11 = calculate(11, 0, tiers)
        self.assertEqual(r11.carrier_amount, Decimal("625.00"))

    def test_incomplete_coverage_raises(self):
        tiers = [
            Tier(1, 5, Decimal("60")),
            Tier(7, None, Decimal("120")),
        ]
        with self.assertRaises(ValueError):
            calculate(6, 0, tiers)

    def test_empty_tiers_with_demurrage_raises(self):
        with self.assertRaises(ValueError):
            calculate(3, 0, [])

    def test_labels(self):
        tiers = [
            Tier(1, 1, Decimal("10")),
            Tier(2, 5, Decimal("20")),
            Tier(6, None, Decimal("30")),
        ]
        result = calculate(6, 0, tiers)
        self.assertEqual(result.lines[0].label, "Día 1")
        self.assertEqual(result.lines[1].label, "Días 2–5")
        self.assertEqual(result.lines[2].label, "Día 6 en adelante")

    def test_days_out_free_days_fields(self):
        tiers = [Tier(1, None, Decimal("10"))]
        result = calculate(7, 3, tiers)
        self.assertEqual(result.days_out, 7)
        self.assertEqual(result.free_days, 3)
        self.assertEqual(result.demurrage_days, 4)
