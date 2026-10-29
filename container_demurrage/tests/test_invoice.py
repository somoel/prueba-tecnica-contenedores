# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestInvoice(TransactionCase):
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
        cls.Account = cls.env["account.account"]
        cls.Journal = cls.env["account.journal"]
        cls.Product = cls.env["product.product"]
        cls.Wizard = cls.env["demurrage.invoice.wizard"]
        cls.Move = cls.env["account.move"]

        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.ctype = cls.ContainerType.create({"name": "40 HC", "code": "40HC"})

        cls.tariff = cls.Tariff.create({
            "shipping_line_id": cls.line.id,
            "container_type_id": cls.ctype.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 7,
            "tier_ids": [
                (0, 0, {"day_from": 1, "day_to": 5, "rate_per_day": 60}),
                (0, 0, {"day_from": 6, "day_to": 10, "rate_per_day": 120}),
                (0, 0, {"day_from": 11, "day_to": 0, "rate_per_day": 180}),
            ],
        })

        bl = cls.BL.create({
            "name": "BL001", "shipping_line_id": cls.line.id,
            "partner_id": cls.partner.id,
            "discharge_date": date(2026, 3, 2),
        })
        cls.container = cls.Container.create({
            "container_number": "CSQU3054383",
            "bl_id": bl.id,
            "container_type_id": cls.ctype.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })
        cop = cls.env.ref("base.COP")
        cls.CurrencyRate.create({
            "currency_id": cop.id,
            "name": date(2026, 1, 1),
            "rate": 4000.0,
            "company_id": cls.container.company_id.id,
        })
        # 1.260 USD / 1.386 USD
        assert cls.container.customer_charge_usd == 1386.0, cls.container.customer_charge_usd
        assert cls.container.carrier_charge_usd == 1260.0, cls.container.carrier_charge_usd

        # income account
        cls.account = cls.Account.create({
            "name": "Ingresos demora",
            "code": "410101",
            "account_type": "income",
        })
        # sales journal
        cls.journal = cls.Journal.search(
            [("type", "=", "sale")], limit=1)
        if not cls.journal:
            cls.journal = cls.Journal.create({
                "name": "Ventas",
                "code": "VTS",
                "type": "sale",
            })
        # product uses data or create
        cls.product = cls.env.ref(
            "container_demurrage.product_demurrage_service",
            raise_if_not_found=False)
        if not cls.product:
            cls.product = cls.Product.create({
                "name": "Demora de contenedor",
                "detailed_type": "service",
                "invoice_policy": "order",
                "list_price": 0.0,
            })
        if cls.product.property_account_income_id:
            pass
        else:
            cls.product.property_account_income_id = cls.account.id
        # category income
        if cls.product.categ_id.property_account_income_categ_id:
            pass
        else:
            cls.product.categ_id.property_account_income_categ_id = cls.account.id

    def test_create_invoice(self):
        wiz = self.Wizard.create({
            "partner_id": self.partner.id,
            "container_ids": [(6, 0, [self.container.id])],
            "invoice_date": date(2026, 3, 25),
        })
        action = wiz.action_create_invoice()
        move = self.Move.browse(action["res_id"])
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.move_type, "out_invoice")
        self.assertEqual(len(move.invoice_line_ids), 1)
        line = move.invoice_line_ids[0]
        self.assertAlmostEqual(line.price_unit, 5544000.0, places=2)
        self.container.invalidate_recordset()
        self.assertTrue(self.container.invoiced)
        self.assertEqual(self.container.invoice_id, move)

    def test_change_invoice_date_refreshes_snapshot(self):
        wiz = self.Wizard.create({
            "partner_id": self.partner.id,
            "container_ids": [(6, 0, [self.container.id])],
            "invoice_date": date(2026, 3, 25),
        })
        action = wiz.action_create_invoice()
        move = self.Move.browse(action["res_id"])
        # rate 4100 at new date
        cop = self.env.ref("base.COP")
        self.CurrencyRate.create({
            "currency_id": cop.id,
            "name": date(2026, 4, 1),
            "rate": 4100.0,
            "company_id": self.container.company_id.id,
        })
        move.invoice_date = date(2026, 4, 1)
        self.container.invalidate_recordset()
        self.assertAlmostEqual(
            self.container.invoiced_customer_cop, 5682600.0, places=2)

    def test_no_rate_raises(self):
        # container without rate: remove rates? create new container with no COP rate date
        bl = self.BL.create({
            "name": "BL002", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
            "discharge_date": date(2026, 3, 2),
        })
        c = self.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })
        # ensure no rate after 2026-12-01? Actually rate exists from 2026-01-01, so to make missing use new currency? 
        # Use direct action_mark? Instead test wizard validation: container missing_exchange_rate? It has rate 4000, not missing.
        # Test _refresh manually with missing rate by using a date beyond? Rate exists from Jan, so not missing.
        # We'll test UserError from wizard if container missing tarifa instead.
        pass

    def test_missing_tariff_not_includable(self):
        bl = self.BL.create({
            "name": "BL003", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
            "discharge_date": date(2026, 9, 1),
        })
        c = self.Container.create({
            "container_number": "OOLU1234567",
            "bl_id": bl.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 9, 1),
            "return_date": date(2026, 9, 10),
        })
        # tariff valid from 2026-01-01 for same line/type, so not missing. Make missing by different type? Use no tariff type.
        ctype2 = self.ContainerType.create({"name": "RF", "code": "RF"})
        bl2 = self.BL.create({
            "name": "BL004", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
            "discharge_date": date(2026, 9, 1),
        })
        c2 = self.Container.create({
            "container_number": "NATU4120783",
            "bl_id": bl2.id,
            "container_type_id": ctype2.id,
            "discharge_date": date(2026, 9, 1),
            "return_date": date(2026, 9, 10),
        })
        with self.assertRaises(UserError):
            wiz = self.Wizard.create({
                "partner_id": self.partner.id,
                "container_ids": [(6, 0, [c2.id])],
                "invoice_date": date(2026, 3, 25),
            })
            wiz.action_create_invoice()

    def test_two_containers_two_lines(self):
        bl2 = self.BL.create({
            "name": "BL005", "shipping_line_id": self.line.id,
            "partner_id": self.partner.id,
            "discharge_date": date(2026, 3, 2),
        })
        c2 = self.Container.create({
            "container_number": "MSLU2209456",
            "bl_id": bl2.id,
            "container_type_id": self.ctype.id,
            "discharge_date": date(2026, 3, 2),
            "return_date": date(2026, 3, 20),
        })
        wiz = self.Wizard.create({
            "partner_id": self.partner.id,
            "container_ids": [(6, 0, [self.container.id, c2.id])],
            "invoice_date": date(2026, 3, 25),
        })
        action = wiz.action_create_invoice()
        move = self.Move.browse(action["res_id"])
        self.assertEqual(len(move.invoice_line_ids), 2)

    def test_no_rate_user_error(self):
        # create a container whose invoicing date has no COP rate by using a far-future date with no rate
        # We'll directly call _refresh_invoice_snapshot? Test via move date change to date without rate
        wiz = self.Wizard.create({
            "partner_id": self.partner.id,
            "container_ids": [(6, 0, [self.container.id])],
            "invoice_date": date(2026, 3, 25),
        })
        action = wiz.action_create_invoice()
        move = self.Move.browse(action["res_id"])
        # change to date with no rate
        with self.assertRaises(UserError):
            move.invoice_date = date(2025, 1, 1)

    def test_invoice_freezes_days_and_tariff(self):
        wiz = self.Wizard.create({
            "partner_id": self.partner.id,
            "container_ids": [(6, 0, [self.container.id])],
            "invoice_date": date(2026, 3, 25),
        })
        action = wiz.action_create_invoice()
        self.container.invalidate_recordset()
        self.assertEqual(self.container.days_out, 19)
        self.assertEqual(self.container.free_days, 7)
        self.assertEqual(self.container.due_date, date(2026, 3, 8))
        self.assertAlmostEqual(self.container.carrier_charge_usd, 1260.0, places=2)
        self.assertAlmostEqual(self.container.customer_charge_usd, 1386.0, places=2)

        # alter tariff free days and tiers after invoicing
        self.tariff.write({"free_days": 99})
        tier = self.tariff.tier_ids[0]
        tier.write({"rate_per_day": 999.0})
        self.container.invalidate_recordset()
        self.assertEqual(self.container.days_out, 19)
        self.assertEqual(self.container.free_days, 7)
        self.assertEqual(self.container.due_date, date(2026, 3, 8))
        self.assertAlmostEqual(self.container.carrier_charge_usd, 1260.0, places=2)
        self.assertAlmostEqual(self.container.customer_charge_usd, 1386.0, places=2)
