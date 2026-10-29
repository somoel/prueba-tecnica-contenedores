# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import UserError, AccessError


class TestStateWizards(TransactionCase):
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
            "name": "BL-WIZ",
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
            cls.env, login="billing_user_wiz",
            groups="base.group_user,container_demurrage.group_demurrage_billing")
        cls.ops_user = new_test_user(
            cls.env, login="ops_user_wiz",
            groups="base.group_user,container_demurrage.group_demurrage_operations")

    def test_mark_invoiced_wizard(self):
        c = self.container
        wizard = self.env["demurrage.mark.invoiced.wizard"].create({
            "container_id": c.id,
            "invoice_reference": "FAC-001",
            "invoice_date": date(2026, 9, 10),
        })
        wizard.with_user(self.billing_user).action_confirm()
        c.invalidate_recordset()
        self.assertEqual(c.state, "invoiced")
        self.assertEqual(c.invoice_reference, "FAC-001")

    def test_ops_cannot_reopen_wizard(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        wizard = self.env["demurrage.reopen.wizard"].create({
            "container_id": c.id,
            "reason": "motivo",
        })
        with self.assertRaises(AccessError):
            wizard.with_user(self.ops_user).action_confirm()

    def test_reopen_wizard_billing(self):
        c = self.container.with_user(self.billing_user)
        c.action_mark_invoiced()
        before_corr = self.Correction.search_count(
            [("container_id", "=", c.id)])
        wizard = self.env["demurrage.reopen.wizard"].create({
            "container_id": c.id,
            "reason": "motivo de reapertura",
        })
        wizard.with_user(self.billing_user).action_confirm()
        c.invalidate_recordset()
        self.assertEqual(c.state, "returned")
        self.assertFalse(c.invoiced)
        self.assertTrue(c.invoice_needs_review)
        self.assertEqual(
            self.Correction.search_count([("container_id", "=", c.id)]),
            before_corr + 1)

    def test_correction_request_wizard(self):
        c = self.container
        wizard = self.env["demurrage.correction.request.wizard"].create({
            "container_id": c.id,
            "reason": "solicitar corrección",
        })
        wizard.action_confirm()
        c.invalidate_recordset()
        self.assertTrue(c.activity_ids)

    def test_cancel_wizard(self):
        c = self.container
        wizard = self.env["demurrage.cancel.wizard"].create({
            "container_id": c.id,
            "reason": "cancelar",
        })
        wizard.action_confirm()
        c.invalidate_recordset()
        self.assertEqual(c.state, "cancelled")

    def test_action_open_wizards(self):
        c = self.container
        cases = [
            ("action_open_reopen_wizard", "demurrage.reopen.wizard"),
            ("action_open_correction_request_wizard",
             "demurrage.correction.request.wizard"),
            ("action_open_cancel_wizard", "demurrage.cancel.wizard"),
            ("action_open_mark_invoiced_wizard",
             "demurrage.mark.invoiced.wizard"),
        ]
        for method, model in cases:
            action = getattr(c, method)()
            self.assertEqual(action["res_model"], model)
            self.assertEqual(action["target"], "new")
