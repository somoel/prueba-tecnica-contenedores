# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

try:
    from psycopg2 import IntegrityError
except Exception:  # pragma: no cover
    IntegrityError = Exception


class TestAgreement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.Agreement = cls.env["demurrage.customer.agreement"]
        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.other_line = cls.ShippingLine.create({"name": "Pacific", "code": "PAC"})

    def _vals(self, **kwargs):
        vals = {
            "partner_id": self.partner.id,
            "shipping_line_id": self.line.id,
        }
        vals.update(kwargs)
        return vals

    def test_create_agreement(self):
        agreement = self.Agreement.create(self._vals(
            extra_free_days=3, admin_fee_percent=5.0, notes="nota"))
        self.assertTrue(agreement.id)
        fetched = self.Agreement.browse(agreement.id)
        self.assertEqual(fetched.partner_id, self.partner)
        self.assertEqual(fetched.shipping_line_id, self.line)
        self.assertEqual(fetched.extra_free_days, 3)
        self.assertEqual(fetched.admin_fee_percent, 5.0)
        self.assertTrue(fetched.active)
        self.assertEqual(fetched.notes, "nota")

    def test_duplicate_raises(self):
        self.Agreement.create(self._vals())
        with self.assertRaises((IntegrityError, ValidationError)):
            self.Agreement.create(self._vals())

    def test_same_partner_other_line_allowed(self):
        self.Agreement.create(self._vals())
        other = self.Agreement.create(self._vals(shipping_line_id=self.other_line.id))
        self.assertTrue(other.id)

    def test_negative_extra_free_days_raises(self):
        with self.assertRaises(ValidationError):
            self.Agreement.create(self._vals(extra_free_days=-1))

    def test_admin_fee_negative_raises(self):
        with self.assertRaises(ValidationError):
            self.Agreement.create(self._vals(admin_fee_percent=-1))

    def test_admin_fee_over_100_raises(self):
        with self.assertRaises(ValidationError):
            self.Agreement.create(self._vals(admin_fee_percent=101))

    def test_partner_agreement_ids(self):
        agreement = self.Agreement.create(self._vals())
        self.assertIn(agreement, self.partner.agreement_ids)

    def test_archive_hides_from_default_search(self):
        agreement = self.Agreement.create(self._vals())
        agreement.active = False
        self.assertFalse(agreement.active)
        self.assertTrue(self.Agreement.with_context(active_test=False).search([("id", "=", agreement.id)]))
        self.assertFalse(self.Agreement.search([("id", "=", agreement.id)]))
