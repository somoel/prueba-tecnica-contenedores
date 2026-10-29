# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase

from odoo.addons.container_demurrage.utils.parsing import (
    normalize_text,
    normalize_key,
    normalize_container_type,
    normalize_bl,
    parse_date,
    is_blank,
)


class TestParsing(TransactionCase):
    def test_normalize_text_none_and_spaces(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text("  Hola   mundo  "), "Hola mundo")
        self.assertEqual(normalize_text("a\t\tb"), "a b")

    def test_normalize_key_accents_and_spaces(self):
        self.assertEqual(normalize_key("  Naviera   Marítima "), "NAVIERA MARITIMA")
        self.assertEqual(normalize_key("café"), "CAFE")
        self.assertEqual(normalize_key(None), "")

    def test_normalize_container_type_aliases(self):
        cases = {
            "20DV": "20DV",
            "20 DV": "20DV",
            "20'": "20DV",
            "20’": "20DV",
            "20 PIES": "20DV",
            "40DV": "40DV",
            "40 DV": "40DV",
            "40HC": "40HC",
            "40 HC": "40HC",
            "CUARENTA HC": "40HC",
            "HIGH CUBE": "40HC",
            "40RF": "40RF",
            "40 RF": "40RF",
            "REEFER": "40RF",
            "REFRIGERADO": "40RF",
        }
        for alias, expected in cases.items():
            self.assertEqual(
                normalize_container_type(alias), expected,
                msg="alias %r" % alias,
            )
        self.assertIsNone(normalize_container_type("DESCONOCIDO"))
        self.assertIsNone(normalize_container_type(None))
        self.assertIsNone(normalize_container_type(""))

    def test_normalize_bl(self):
        self.assertEqual(normalize_bl("MSL- 0628-A"), "MSL-0628-A")
        self.assertEqual(normalize_bl("  msl  -  0628  -  a  "), "MSL-0628-A")
        self.assertEqual(normalize_bl(None), "")

    def test_parse_date_dd_mm_yyyy(self):
        self.assertEqual(parse_date("02/03/2026"), date(2026, 3, 2))

    def test_parse_date_iso(self):
        self.assertEqual(parse_date("2026-06-28"), date(2026, 6, 28))

    def test_parse_date_dd_mmm_default_year(self):
        self.assertEqual(parse_date("15-jul", default_year=2026), date(2026, 7, 15))

    def test_parse_date_dd_mmm_yyyy(self):
        self.assertEqual(parse_date("15-jul-2026"), date(2026, 7, 15))

    def test_parse_date_dd_mm_yyyy_alt(self):
        self.assertEqual(parse_date("10/04/2026"), date(2026, 4, 10))

    def test_parse_date_single_digits(self):
        self.assertEqual(parse_date("1/2/2026"), date(2026, 2, 1))

    def test_parse_date_invalid_raises(self):
        with self.assertRaises(ValueError):
            parse_date("32/13/2026")

    def test_parse_date_no_default_year_raises(self):
        with self.assertRaises(ValueError):
            parse_date("15-jul")

    def test_is_blank(self):
        self.assertTrue(is_blank(None))
        self.assertTrue(is_blank(""))
        self.assertTrue(is_blank("   "))
        self.assertFalse(is_blank("x"))
        self.assertFalse(is_blank(0))
