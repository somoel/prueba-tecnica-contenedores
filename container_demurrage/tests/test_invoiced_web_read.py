# -*- coding: utf-8 -*-
from datetime import date

from odoo import api
from odoo.tests.common import TransactionCase, new_test_user


class TestInvoicedWebRead(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.Tariff = cls.env["demurrage.tariff"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.CurrencyRate = cls.env["res.currency.rate"]

        cls.line = cls.ShippingLine.create({"name": "MSC", "code": "MSC"})
        cls.ctype = cls.ContainerType.create({"name": "20 DV", "code": "20DV"})
        cls.partner = cls.Partner.create({"name": "Cliente WebRead"})
        cls.tariff = cls.Tariff.create({
            "shipping_line_id": cls.line.id,
            "container_type_id": cls.ctype.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 35}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 70}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 110}),
            ],
        })
        cls.bl = cls.BL.create({
            "name": "BL-WEBREAD",
            "shipping_line_id": cls.line.id,
            "partner_id": cls.partner.id,
            "discharge_date": date(2026, 5, 4),
        })
        cls.container = cls.Container.create({
            "container_number": "MSCU7654329",
            "bl_id": cls.bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 5, 4),
            "return_date": date(2026, 5, 11),
        })
        cop = cls.env.ref("base.COP")
        cls.CurrencyRate.create({
            "currency_id": cop.id,
            "name": date(2026, 1, 1),
            "rate": 4000.0,
            "company_id": cls.container.company_id.id,
        })

        cls.container.with_user(cls.env.user).action_mark_invoiced(
            invoice_date=date(2026, 5, 11))

        cls.billing = new_test_user(
            cls.env, login="new_test_user",
            groups="container_demurrage.group_demurrage_billing,base.group_user")

    def test_invoiced_web_read_no_keyerror(self):
        env_billing = api.Environment(self.env.cr, self.billing.id, {})
        container = env_billing["demurrage.container"].browse(self.container.id)
        spec = {
            "container_number": {},
            "state": {},
            "tariff_id": {"fields": {"display_name": {}}},
            "tier_breakdown": {},
            "carrier_charge_usd": {},
            "customer_charge_usd": {},
            "invoiced_customer_cop": {},
            "display_name": {},
        }
        res = container.web_read(spec)
        self.assertTrue(res)
        row = res[0] if isinstance(res, list) else res
        self.assertNotEqual(row.get("tariff_id"), False)
        tariff = row.get("tariff_id")
        if isinstance(tariff, dict):
            self.assertIn("id", tariff)
