# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

try:
    from psycopg2 import IntegrityError
except Exception:  # pragma: no cover
    IntegrityError = Exception


class TestBLContainer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]

        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.other_partner = cls.Partner.create({"name": "Otro Cliente"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.other_line = cls.ShippingLine.create({"name": "Pacific", "code": "PAC"})
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
            "container_number": "MSCU1234567",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
        }
        vals.update(kwargs)
        return vals

    def test_create_bl_and_read_fields(self):
        bl = self.BL.create(self._bl_vals(
            discharge_date=date(2026, 1, 10), notes="nota BL"))
        self.assertTrue(bl.id)
        fetched = self.BL.browse(bl.id)
        self.assertEqual(fetched.name, "BL001")
        self.assertEqual(fetched.shipping_line_id, self.line)
        self.assertEqual(fetched.partner_id, self.partner)
        self.assertEqual(fetched.discharge_date, date(2026, 1, 10))
        self.assertEqual(fetched.notes, "nota BL")
        self.assertTrue(fetched.active)
        self.assertEqual(fetched.company_id, self.env.company)

    def test_duplicate_bl_same_line_raises(self):
        self.BL.create(self._bl_vals())
        try:
            self.BL.create(self._bl_vals())
        except (IntegrityError, ValidationError):
            return
        self.fail("Se esperaba IntegrityError o ValidationError")

    def test_duplicate_bl_different_line_allowed(self):
        self.BL.create(self._bl_vals())
        other = self.BL.create(self._bl_vals(
            name="BL001", shipping_line_id=self.other_line.id))
        self.assertTrue(other.id)

    def test_create_container_fields_and_related(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        self.assertTrue(container.id)
        self.assertEqual(container.name, "MSCU1234567")
        self.assertEqual(container.display_name, "MSCU1234567 (BL001)")
        self.assertEqual(container.shipping_line_id, self.line)
        self.assertEqual(container.partner_id, self.partner)
        self.assertEqual(container.company_id, self.env.company)
        self.assertEqual(container.bl_id, bl)

    def test_container_inherits_bl_discharge_date(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        self.assertEqual(container.discharge_date, date(2026, 1, 10))

    def test_container_explicit_discharge_date_not_overwritten(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 2, 2)))
        self.assertEqual(container.discharge_date, date(2026, 2, 2))

    def test_container_count_and_mixed_dates(self):
        bl = self.BL.create(self._bl_vals())
        self.Container.create(self._container_vals(
            bl, container_number="MSCU1111111", discharge_date=date(2026, 1, 10)))
        self.Container.create(self._container_vals(
            bl, container_number="MSCU2222222", discharge_date=date(2026, 1, 10)))
        bl.invalidate_recordset()
        self.assertEqual(bl.container_count, 2)
        self.assertFalse(bl.has_mixed_discharge_dates)

        bl2 = self.BL.create({"name": "BL002", "shipping_line_id": self.line.id,
                              "partner_id": self.partner.id})
        self.Container.create(self._container_vals(
            bl2, container_number="MSCU3333333", discharge_date=date(2026, 1, 10)))
        self.Container.create(self._container_vals(
            bl2, container_number="MSCU4444444", discharge_date=date(2026, 2, 2)))
        bl2.invalidate_recordset()
        self.assertTrue(bl2.has_mixed_discharge_dates)

    def test_normalize_container_number_on_create(self):
        bl = self.BL.create(self._bl_vals())
        container = self.Container.create(self._container_vals(
            bl, container_number="natu 508163 4"))
        self.assertEqual(container.container_number, "NATU5081634")
        self.assertEqual(container.name, "NATU5081634")

    def test_state_transitions(self):
        bl = self.BL.create(self._bl_vals())
        container = self.Container.create(self._container_vals(bl))
        self.assertEqual(container.state, "draft")

        container.discharge_date = date(2026, 1, 10)
        self.assertEqual(container.state, "open")

        container.return_date = date(2026, 1, 20)
        self.assertEqual(container.state, "returned")

        container.invoiced = True
        self.assertEqual(container.state, "invoiced")

        container.cancelled = True
        self.assertEqual(container.state, "cancelled")

    def test_state_cancelled_priority(self):
        bl = self.BL.create(self._bl_vals())
        container = self.Container.create(self._container_vals(
            bl, discharge_date=date(2026, 1, 10), invoiced=True, cancelled=True))
        self.assertEqual(container.state, "cancelled")

    def test_as_of_date_defaults_today(self):
        bl = self.BL.create(self._bl_vals())
        container = self.Container.create(self._container_vals(bl))
        self.assertEqual(container.as_of_date, date.today())

    def test_onchange_and_action_fill_empty_only(self):
        bl = self.BL.create(self._bl_vals())
        c1 = self.Container.create(self._container_vals(
            bl, container_number="MSCU1111111"))
        c2 = self.Container.create(self._container_vals(
            bl, container_number="MSCU2222222", discharge_date=date(2026, 5, 5)))
        # onchange
        bl.discharge_date = date(2026, 3, 3)
        bl._onchange_discharge_date()
        c1.invalidate_recordset()
        c2.invalidate_recordset()
        self.assertEqual(c1.discharge_date, date(2026, 3, 3))
        self.assertEqual(c2.discharge_date, date(2026, 5, 5))

        # action
        c3 = self.Container.create(self._container_vals(
            bl, container_number="MSCU3333333"))
        bl.discharge_date = date(2026, 4, 4)
        bl.action_apply_discharge_date()
        c1.invalidate_recordset()
        c2.invalidate_recordset()
        c3.invalidate_recordset()
        self.assertEqual(c3.discharge_date, date(2026, 4, 4))
        self.assertEqual(c2.discharge_date, date(2026, 5, 5))

    def test_duplicate_container_same_bl_raises(self):
        bl = self.BL.create(self._bl_vals())
        self.Container.create(self._container_vals(bl))
        try:
            self.Container.create(self._container_vals(bl))
        except (IntegrityError, ValidationError):
            return
        self.fail("Se esperaba IntegrityError o ValidationError")
