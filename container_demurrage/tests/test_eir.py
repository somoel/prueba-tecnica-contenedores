# -*- coding: utf-8 -*-
import base64
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestEIR(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.ShippingLine = cls.env["demurrage.shipping.line"]
        cls.ContainerType = cls.env["demurrage.container.type"]
        cls.BL = cls.env["demurrage.bl"]
        cls.Container = cls.env["demurrage.container"]
        cls.Attachment = cls.env["ir.attachment"]

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

    def _make_attachment(self, name, mimetype, data_bytes):
        return self.Attachment.create({
            "name": name,
            "datas": base64.b64encode(data_bytes).decode(),
            "mimetype": mimetype,
        })

    def test_no_eir(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        self.assertTrue(container.missing_eir)
        self.assertEqual(container.eir_count, 0)

    def test_attach_pdf(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        att = self._make_attachment("eir.pdf", "application/pdf", b"%PDF-1.4\nsmall")
        container.write({"eir_attachment_ids": [(4, att.id)]})
        self.assertEqual(container.eir_count, 1)
        self.assertFalse(container.missing_eir)

    def test_attach_image_jpeg(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        import base64 as _b
        jpeg_b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi6KKK+ZP3E//Z"
        att = self.Attachment.create({
            "name": "eir.jpg",
            "datas": jpeg_b64,
            "mimetype": "image/jpeg",
        })
        container.write({"eir_attachment_ids": [(4, att.id)]})
        self.assertEqual(container.eir_count, 1)
        self.assertFalse(container.missing_eir)

    def test_attach_text_plain_raises(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        att = self._make_attachment("eir.txt", "text/plain", b"hello")
        with self.assertRaises(ValidationError) as cm:
            container.write({"eir_attachment_ids": [(4, att.id)]})
        self.assertTrue(str(cm.exception))

    def test_attach_large_pdf_raises(self):
        bl = self.BL.create(self._bl_vals(discharge_date=date(2026, 1, 10)))
        container = self.Container.create(self._container_vals(bl))
        big = b"%PDF-1.4\n" + (b"x" * (11 * 1024 * 1024))
        att = self._make_attachment("big.pdf", "application/pdf", big)
        with self.assertRaises(ValidationError):
            container.write({"eir_attachment_ids": [(4, att.id)]})
