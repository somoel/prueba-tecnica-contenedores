# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase


class TestCron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.Activity = cls.env["mail.activity"]

        cls.line = cls.ShippingLine.create({"name": "Naviera Cron", "code": "CRON"})
        cls.ctype = cls.ContainerType.create({"name": "20 DV", "code": "20DVC"})
        cls.partner = cls.Partner.create({"name": "Cliente Cron"})
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
            "name": "BL-CRON",
            "shipping_line_id": cls.line.id,
            "partner_id": cls.partner.id,
            "discharge_date": date(2026, 10, 1),
        })

        # por vencer: due 2026-10-26
        cls.c_due_soon = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 10, 20),
        })
        # vencido: due 2026-10-24
        cls.c_overdue = cls.Container.create({
            "container_number": "NATU4120783",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 10, 18),
        })
        # devuelto
        cls.c_returned = cls.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 10, 20),
            "return_date": date(2026, 10, 22),
        })
        # cancelado
        cls.c_cancelled = cls.Container.create({
            "container_number": "NATU5081634",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 10, 20),
            "cancelled": True,
        })

    def test_daily_creates_activities(self):
        today = date(2026, 10, 25)
        created = self.Container._cron_daily(today=today)
        self.assertEqual(created, 2)

        acts = self.Activity.search([
            ("res_model", "=", "demurrage.container"),
        ])
        self.assertEqual(len(acts), 2)

        # por vencer y vencido tienen last_reminder_on
        for c in (self.c_due_soon, self.c_overdue):
            c.invalidate_recordset()
            self.assertEqual(c.last_reminder_on, today)
            self.assertEqual(c.as_of_date, today)

        # devuelto/cancelado no
        self.c_returned.invalidate_recordset()
        self.c_cancelled.invalidate_recordset()
        # no activities for them (activity_ids empty)
        self.assertFalse(self.c_returned.activity_ids.filtered(
            lambda a: (a.summary or "").startswith("Demora:")))
        self.assertFalse(self.c_cancelled.activity_ids.filtered(
            lambda a: (a.summary or "").startswith("Demora:")))

        # idempotencia
        created2 = self.Container._cron_daily(today=today)
        self.assertEqual(created2, 0)
        acts2 = self.Activity.search([
            ("res_model", "=", "demurrage.container"),
        ])
        self.assertEqual(len(acts2), 2)

    def test_operations_user_assignment(self):
        user = self.env["res.users"].create({
            "name": "Ops User",
            "login": "ops_cron_test",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.env["ir.config_parameter"].sudo().set_param(
            "container_demurrage.operations_user_id", str(user.id))
        # reset reminder to allow creation? last_reminder_on already today from previous test? TransactionCase rolls back per test, so no.
        today = date(2026, 10, 25)
        self.Container._cron_daily(today=today)
        acts = self.Activity.search([
            ("res_model", "=", "demurrage.container"),
            ("user_id", "=", user.id),
        ])
        self.assertTrue(len(acts) >= 1)
