# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

try:
    from psycopg2 import IntegrityError
except Exception:  # pragma: no cover
    IntegrityError = Exception


class TestTariff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.ctype = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})
        cls.other_type = cls.ContainerType.create({"name": "20 DRY", "code": "20DRY"})

    def _tariff_vals(self, **kwargs):
        vals = {
            "shipping_line_id": self.line.id,
            "container_type_id": self.ctype.id,
            "valid_from": "2026-01-01",
        }
        vals.update(kwargs)
        return vals

    def test_create_tariff_with_tiers(self):
        tariff = self.Tariff.create(self._tariff_vals(
            free_days=5,
            tier_ids=[
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 10}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 20}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 30}),
            ],
        ))
        self.assertTrue(tariff.id)
        self.assertEqual(tariff.name, "ATL-40HC-2026-01-01")
        self.assertEqual(tariff.free_days, 5)
        self.assertEqual(tariff.tier_count, 3)

    def test_valid_to_before_valid_from_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(
                valid_from="2026-02-01",
                valid_to="2026-01-01",
            ))

    def test_overlap_same_line_type_raises(self):
        self.Tariff.create(self._tariff_vals(valid_to="2026-06-30"))
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(valid_from="2026-03-01"))

    def test_adjacent_validity_allowed(self):
        self.Tariff.create(self._tariff_vals(valid_to="2026-06-30"))
        tariff2 = self.Tariff.create(self._tariff_vals(valid_from="2026-07-01"))
        self.assertTrue(tariff2.id)

    def test_overlap_other_type_allowed(self):
        self.Tariff.create(self._tariff_vals(valid_to="2026-06-30"))
        tariff2 = self.Tariff.create(self._tariff_vals(
            container_type_id=self.other_type.id,
            valid_from="2026-03-01",
        ))
        self.assertTrue(tariff2.id)

    def test_tier_rate_zero_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 1, "day_to": 0, "rate_per_day": 0}),
            ]))

    def test_tier_day_to_less_than_day_from_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 5, "day_to": 3, "rate_per_day": 10}),
            ]))

    def test_tiers_with_gap_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 10}),
                (0, 0, {"day_from": 7, "day_to": 0, "rate_per_day": 20}),
            ]))

    def test_tiers_not_starting_at_one_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 2, "day_to": 5, "rate_per_day": 10}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 20}),
            ]))

    def test_open_tier_not_last_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 1, "day_to": 0, "rate_per_day": 10}),
                (0, 0, {"day_from": 2, "day_to": 5, "rate_per_day": 20}),
            ]))

    def test_duplicate_day_from_raises(self):
        with self.assertRaises((IntegrityError, ValidationError)):
            self.Tariff.create(self._tariff_vals(tier_ids=[
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 10}),
                (0, 0, {"day_from": 1, "day_to": 0, "rate_per_day": 20}),
            ]))

    def test_negative_free_days_raises(self):
        with self.assertRaises(ValidationError):
            self.Tariff.create(self._tariff_vals(free_days=-1))
