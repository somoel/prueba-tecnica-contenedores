# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import UserError, AccessError


class TestStates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.Correction = cls.env["demurrage.correction"]
        cls.CurrencyRate = cls.env["res.currency.rate"]

        cls.line = cls.ShippingLine.create({"name": "Naviera Test", "code": "NAV"})
        cls.ctype = cls.ContainerType.create({"name": "20 DV", "code": "20DV"})
        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.tariff = cls.Tariff.create({
            "shipping_line_id": cls.line.id,
            "container_type_id": cls.ctype.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 35}),
                (0, 0, {"day_from": 6, "day_to": 0, "rate_per_day": 70}),
            ],
        })
        cls.bl = cls.BL.create({
            "name": "BL-STATES",
            "shipping_line_id": cls.line.id,
            "partner_id": cls.partner.id,
            "discharge_date": date(2026, 9, 1),
        })
        cls.container = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 9, 1),
            "return_date": date(2026, 9, 10),
        })
        cop = cls.env.ref("base.COP")
        cls.CurrencyRate.create({
            "currency_id": cop.id,
            "name": date(2026, 1, 1),
            "rate": 4000.0,
            "company_id": cls.container.company_id.id,
        })

        cls.billing_user = new_test_user(
            cls.env, login="billing_user_states",
            groups="base.group_user,container_demurrage.group_demurrage_billing")
        cls.ops_user = new_test_user(
            cls.env, login="ops_user_states",
            groups="base.group_user,container_demurrage.group_demurrage_operations")

    def test_mark_invoiced_billing(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        c.invalidate_recordset()
        self.assertEqual(c.state, "invoiced")
        self.assertTrue(c.invoiced)
        self.assertEqual(c.invoice_reference, "Facturación manual")
        self.assertIsNotNone(c.invoice_date)
        self.assertIsNotNone(c.invoiced_at)
        self.assertEqual(c.invoiced_carrier_usd, c.carrier_charge_usd)
        self.assertEqual(c.invoiced_demurrage_days, c.demurrage_days)
        self.assertTrue(c.invoiced_customer_cop)

    def test_change_discharge_date_blocked(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        with self.assertRaises(UserError):
            c.write({"discharge_date": date(2026, 9, 2)})

    def test_change_notes_allowed(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        c.write({"notes": "nota ok"})
        self.assertEqual(c.notes, "nota ok")

    def test_ops_cannot_mark_invoiced(self):
        c = self.container.with_user(self.ops_user)
        with self.assertRaises((AccessError, UserError)):
            c.action_mark_invoiced()

    def test_reopen_requires_reason(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        with self.assertRaises(UserError):
            c.action_reopen("")

    def test_reopen_with_reason(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        before_carrier = c.invoiced_carrier_usd
        corr_count_before = self.Correction.search_count([("container_id", "=", c.id)])
        c.action_reopen("motivo de reapertura")
        c.invalidate_recordset()
        self.assertEqual(c.state, "returned")
        self.assertFalse(c.invoiced)
        self.assertTrue(c.invoice_needs_review)
        self.assertEqual(
            self.Correction.search_count([("container_id", "=", c.id)]),
            corr_count_before + 1)
        # snapshots intact
        self.assertEqual(c.invoiced_carrier_usd, before_carrier)
        # can edit return_date
        c.write({"return_date": date(2026, 9, 11)})
        self.assertEqual(c.return_date, date(2026, 9, 11))

    def test_tariff_change_does_not_alter_snapshot(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        before = c.carrier_charge_usd
        # change tariff rates
        self.tariff.write({"tier_ids": [(1, self.tariff.tier_ids[0].id, {"rate_per_day": 999})]})
        c.invalidate_recordset()
        # carrier_charge_usd should still reflect snapshot? compute sets snapshot
        self.assertEqual(c.carrier_charge_usd, before)

    def test_cancel_open(self):
        # create open container
        bl = self.BL.create({
            "name": "BL-OPEN", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id, "discharge_date": date(2026, 9, 1),
        })
        c = self.Container.create({
            "container_number": "NATU4120783",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 9, 1),
        })
        c.with_user(self.billing_user).action_cancel()
        c.invalidate_recordset()
        self.assertEqual(c.state, "cancelled")

    def test_cancel_invoiced_raises(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        with self.assertRaises(UserError):
            c.action_cancel()

    def test_set_return_today(self):
        bl = self.BL.create({
            "name": "BL-RT", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id, "discharge_date": date(2026, 9, 1),
        })
        c = self.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 9, 1),
        })
        self.assertFalse(c.return_date)
        c.with_user(self.billing_user).action_set_return_today()
        c.invalidate_recordset()
        self.assertEqual(c.return_date, date.today())
        # Actually use fields date
        self.assertTrue(c.return_date)

    def test_request_correction_creates_activity_or_message(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        before_msgs = len(c.message_ids)
        before_acts = len(c.activity_ids)
        c.action_request_correction("please fix")
        c.invalidate_recordset()
        self.assertTrue(len(c.message_ids) > before_msgs or len(c.activity_ids) > before_acts)

    def test_refresh_estimate(self):
        bl = self.BL.create({
            "name": "BL-REF", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id, "discharge_date": date(2026, 9, 1),
        })
        c = self.Container.create({
            "container_number": "TGHU1234567",  # may be invalid? use valid
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 9, 1),
        })
        # ensure valid container number? TGHU... validate maybe. Use known valid
        c.write({"as_of_date": date(2026, 9, 1)})
        c.action_refresh_estimate()
        c.invalidate_recordset()
        self.assertEqual(c.as_of_date, date.today())
