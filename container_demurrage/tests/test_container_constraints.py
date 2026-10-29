# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestContainerConstraints(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]

        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.ctype = cls.ContainerType.create({"name": "Dry 20", "code": "20DRY"})

    def _bl_vals(self, **kwargs):
        vals = {
            "name": "BL001",
            "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return vals

    def _container_vals(self, bl, **kwargs):
        vals = {
            "container_number": "CSQU3054383",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
        }
        vals.update(kwargs)
        return vals

    def test_iso_invalid_raises(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, container_number="CSQU3054384"))
        self.assertIn("se esperaba 3", str(cm.exception))

    def test_spaces_lowercase_normalized_no_error(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(
            bl, container_number=" csqu 305438 3 "))
        self.assertEqual(container.container_number, "CSQU3054383")

    def test_return_without_discharge_raises(self):
        bl = self.BL.create(self._bl_vals())
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, discharge_date=False, return_date=date(2026, 1, 20)))
        self.assertIn("La fecha de devolución requiere fecha de descarga.",
                      str(cm.exception))

    def test_return_before_discharge_raises(self):
        bl = self.BL.create(self._bl_vals())
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, discharge_date=date(2026, 1, 20),
                return_date=date(2026, 1, 10)))
        self.assertIn("La fecha de devolución no puede ser anterior a la descarga.",
                      str(cm.exception))

    def test_future_return_raises(self):
        bl = self.BL.create(self._bl_vals())
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, discharge_date=date(2026, 1, 10),
                return_date=date(2099, 1, 1)))
        self.assertIn("La fecha de devolución no puede ser futura.",
                      str(cm.exception))

    def test_overlap_closed_periods_raises(self):
        bl = self.BL.create(self._bl_vals())
        self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10),
            return_date=date(2026, 1, 20)))
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, container_number="CSQU3054383",
                discharge_date=date(2026, 1, 15),
                return_date=date(2026, 1, 25)))
        self.assertIn("El contenedor ya está registrado como afuera en ese periodo.",
                      str(cm.exception))

    def test_open_period_blocks_new_raises(self):
        bl = self.BL.create(self._bl_vals())
        self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10)))
        with self.assertRaises(ValidationError) as cm:
            self.Container.create(self._container_vals(
                bl, container_number="CSQU3054383",
                discharge_date=date(2026, 1, 15),
                return_date=date(2026, 1, 25)))
        self.assertIn("El contenedor ya está registrado como afuera en ese periodo.",
                      str(cm.exception))

    def test_non_overlapping_periods_allowed(self):
        bl = self.BL.create(self._bl_vals())
        self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10),
            return_date=date(2026, 1, 20)))
        second = self.Container.create(self._container_vals(
            bl, container_number="CSQU3054383",
            discharge_date=date(2026, 2, 1),
            return_date=date(2026, 2, 10)))
        self.assertTrue(second.id)

    def test_cancelled_does_not_block(self):
        bl = self.BL.create(self._bl_vals())
        first = self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10),
            return_date=date(2026, 1, 20)))
        first.cancelled = True
        second = self.Container.create(self._container_vals(
            bl, container_number="CSQU3054383",
            discharge_date=date(2026, 1, 15),
            return_date=date(2026, 1, 25)))
        self.assertTrue(second.id)

    def test_same_number_different_bl_non_overlapping_allowed(self):
        bl1 = self.BL.create(self._bl_vals(name="BL001"))
        bl2 = self.BL.create(self._bl_vals(name="BL002"))
        self.Container.create(self._container_vals(
            bl1, discharge_date=date(2026, 1, 10),
            return_date=date(2026, 1, 20)))
        second = self.Container.create(self._container_vals(
            bl2, discharge_date=date(2026, 2, 1),
            return_date=date(2026, 2, 10)))
        self.assertTrue(second.id)

    def test_valid_dates_no_error(self):
        bl = self.BL.create(self._bl_vals())
        container = self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10),
            return_date=date(2026, 1, 20)))
        self.assertTrue(container.id)