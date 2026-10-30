# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError


class TestSecurity(TransactionCase):
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
        cls.CarrierInvoice = cls.env["demurrage.carrier.invoice"]
        cls.InvoiceWizard = cls.env["demurrage.invoice.wizard"]

        cls.partner = cls.Partner.create({"name": "Cliente Test"})
        cls.line = cls.ShippingLine.create({"name": "Atlantic", "code": "ATL"})
        cls.ctype = cls.ContainerType.create({"name": "Dry 20", "code": "20DRY"})
        cls.tariff_vals = {
            "shipping_line_id": cls.line.id,
            "container_type_id": cls.ctype.id,
            "valid_from": date(2026, 1, 1),
            "free_days": 5,
        }

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

    def test_groups_exist_and_hierarchy(self):
        ops = self.env.ref("container_demurrage.group_demurrage_operations")
        billing = self.env.ref("container_demurrage.group_demurrage_billing")
        manager = self.env.ref("container_demurrage.group_demurrage_manager")
        self.assertTrue(ops)
        self.assertTrue(billing)
        self.assertTrue(manager)
        self.assertIn(ops, billing.implied_ids)
        self.assertIn(billing, manager.implied_ids)

    def test_operations_can_read_tariff_not_create_or_write(self):
        user = new_test_user(
            self.env, login="ops_user",
            groups="base.group_user,container_demurrage.group_demurrage_operations")
        tariff = self.Tariff.create(self.tariff_vals)
        # read
        read_tariff = self.Tariff.with_user(user).browse(tariff.id)
        self.assertEqual(read_tariff.free_days, 5)
        # create
        with self.assertRaises(AccessError):
            self.Tariff.with_user(user).create(self.tariff_vals)
        # write
        with self.assertRaises(AccessError):
            tariff.with_user(user).write({"free_days": 10})

    def test_billing_can_create_tariff(self):
        user = new_test_user(
            self.env, login="billing_user",
            groups="base.group_user,container_demurrage.group_demurrage_billing")
        tariff = self.Tariff.with_user(user).create(self.tariff_vals)
        self.assertTrue(tariff.id)

    def test_operations_can_create_bl_and_container_not_unlink(self):
        user = new_test_user(
            self.env, login="ops_user2",
            groups="base.group_user,container_demurrage.group_demurrage_operations")
        bl = self.BL.with_user(user).create(self._bl_vals())
        container = self.Container.with_user(user).create(
            self._container_vals(bl))
        self.assertTrue(bl.id)
        self.assertTrue(container.id)
        with self.assertRaises(AccessError):
            container.with_user(user).unlink()

    def test_manager_can_unlink_container(self):
        user = new_test_user(
            self.env, login="manager_user",
            groups="base.group_user,container_demurrage.group_demurrage_manager")
        bl = self.BL.with_user(user).create(self._bl_vals(name="BLMGR"))
        container = self.Container.with_user(user).create(
            self._container_vals(bl, container_number="MSLU1458705"))
        container.with_user(user).unlink()
        self.assertFalse(container.exists())

    def test_create_and_read_correction(self):
        bl = self.BL.create(self._bl_vals(name="BLCORR"))
        container = self.Container.create(self._container_vals(bl))
        corr = self.Correction.create({
            "container_id": container.id,
            "reason": "Ajuste de fecha",
        })
        self.assertTrue(corr.id)
        user = new_test_user(
            self.env, login="ops_reader",
            groups="base.group_user,container_demurrage.group_demurrage_operations")
        read_corr = self.Correction.with_user(user).browse(corr.id)
        self.assertEqual(read_corr.reason, "Ajuste de fecha")

    def test_operations_cannot_create_invoice_from_wizard(self):
        user = new_test_user(
            self.env, login="ops_nowiz",
            groups="base.group_user,container_demurrage.group_demurrage_operations")
        with self.assertRaises(AccessError):
            self.InvoiceWizard.with_user(user).create({
                "partner_id": self.partner.id,
                "container_ids": [],
            })

    def test_operations_carrier_invoice_read_only(self):
        ci = self.CarrierInvoice.create({
            "name": "CI001",
            "shipping_line_id": self.line.id,
            "invoice_date": date(2026, 3, 1),
        })
        user = new_test_user(
            self.env, login="ops_ci",
            groups="base.group_user,container_demurrage.group_demurrage_operations")
        read_ci = self.CarrierInvoice.with_user(user).browse(ci.id)
        self.assertEqual(read_ci.name, "CI001")
        with self.assertRaises(AccessError):
            ci.with_user(user).write({"notes": "x"})

    def test_system_group_implies_manager_and_can_read_container(self):
        bl = self.BL.create(self._bl_vals(name="BLSYS"))
        container = self.Container.create(
            self._container_vals(bl, container_number="MSLU1458705"))
        user = new_test_user(
            self.env, login="system_user",
            groups="base.group_system")
        self.assertTrue(user.has_group(
            "container_demurrage.group_demurrage_manager"))
        read_container = self.Container.with_user(user).browse(container.id)
        self.assertEqual(read_container.container_number, "MSLU1458705")