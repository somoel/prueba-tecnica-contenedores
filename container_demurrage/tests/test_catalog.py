# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

try:
    from psycopg2 import IntegrityError
except Exception:  # pragma: no cover
    IntegrityError = Exception


class TestCatalog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]

    def test_create_container_type(self):
        ctype = self.ContainerType.create({
            "name": "Dry 20",
            "code": "20DRY",
            "description": "Contenedor seco de 20 pies",
        })
        self.assertTrue(ctype.id)
        fetched = self.ContainerType.browse(ctype.id)
        self.assertEqual(fetched.name, "Dry 20")
        self.assertEqual(fetched.code, "20DRY")
        self.assertTrue(fetched.active)

    def test_duplicate_container_type_code_raises(self):
        self.ContainerType.create({"name": "Dry 20", "code": "20DRY"})
        with self.assertRaises((ValidationError, IntegrityError)):
            self.ContainerType.create({"name": "Otro", "code": "20DRY"})

    def test_create_shipping_line(self):
        line = self.ShippingLine.create({
            "name": "Maersk",
            "code": "MAERSK",
            "notes": "Naviera de prueba",
        })
        self.assertTrue(line.id)
        fetched = self.ShippingLine.browse(line.id)
        self.assertEqual(fetched.name, "Maersk")
        self.assertEqual(fetched.code, "MAERSK")
        self.assertTrue(fetched.active)

    def test_duplicate_shipping_line_code_raises(self):
        self.ShippingLine.create({"name": "Maersk", "code": "MAERSK"})
        with self.assertRaises((ValidationError, IntegrityError)):
            self.ShippingLine.create({"name": "Otra", "code": "MAERSK"})

    def test_archive_hides_from_default_search(self):
        ctype = self.ContainerType.create({"name": "Dry 20", "code": "20DRY"})
        ctype.active = False
        self.assertFalse(ctype.active)
        self.assertTrue(self.ContainerType.with_context(active_test=False).search([("id", "=", ctype.id)]))
        self.assertFalse(self.ContainerType.search([("id", "=", ctype.id)]))

        line = self.ShippingLine.create({"name": "Maersk", "code": "MAERSK"})
        line.active = False
        self.assertFalse(line.active)
        self.assertTrue(self.ShippingLine.with_context(active_test=False).search([("id", "=", line.id)]))
        self.assertFalse(self.ShippingLine.search([("id", "=", line.id)]))
