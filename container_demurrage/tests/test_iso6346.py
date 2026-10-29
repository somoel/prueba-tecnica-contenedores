# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

from odoo.addons.container_demurrage.utils.iso6346 import (
    normalize_container_number,
    calculate_check_digit,
    validate_container_number,
)


class TestISO6346(TransactionCase):
    def test_normalize_none_or_empty(self):
        self.assertEqual(normalize_container_number(None), "")
        self.assertEqual(normalize_container_number(""), "")

    def test_normalize_removes_spaces_and_uppercases(self):
        self.assertEqual(normalize_container_number("natu 508163 4"), "NATU5081634")
        self.assertEqual(normalize_container_number("  csqu 305438 3 "), "CSQU3054383")

    def test_calculate_check_digit_valid(self):
        self.assertEqual(calculate_check_digit("CSQU3054383"), 3)

    def test_calculate_check_digit_invalid_format_returns_none(self):
        self.assertIsNone(calculate_check_digit("CSQU305438"))
        self.assertIsNone(calculate_check_digit("CSQU305438A"))
        self.assertIsNone(calculate_check_digit("12345678901"))
        self.assertIsNone(calculate_check_digit("CSQX3054383"))

    def test_validate_valid_number(self):
        is_valid, error, expected = validate_container_number("CSQU3054383")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(expected, 3)

    def test_validate_invalid_check_digit_returns_expected(self):
        is_valid, error, expected = validate_container_number("CSQU3054384")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Dígito de control inválido: se esperaba 3.")
        self.assertEqual(expected, 3)

    def test_validate_natu_with_spaces_and_lowercase(self):
        is_valid, error, expected = validate_container_number("natu 508163 4")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(expected, 4)

    def test_validate_mslu_expected_six(self):
        is_valid, error, expected = validate_container_number("MSLU6135877")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Dígito de control inválido: se esperaba 6.")
        self.assertEqual(expected, 6)

    def test_validate_fourth_letter_invalid(self):
        is_valid, error, expected = validate_container_number("CSQA3054383")
        self.assertFalse(is_valid)
        self.assertEqual(error, "La cuarta letra debe ser U, J o Z.")
        self.assertIsNone(expected)

    def test_validate_wrong_length(self):
        is_valid, error, expected = validate_container_number("CSQU305438")
        self.assertFalse(is_valid)
        self.assertEqual(error, "El número debe tener 11 caracteres.")
        self.assertIsNone(expected)

    def test_validate_non_alphanumeric(self):
        is_valid, error, expected = validate_container_number("CSQU305438!")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Los últimos 7 caracteres deben ser dígitos.")
        self.assertIsNone(expected)

    def test_validate_first_chars_not_letters(self):
        is_valid, error, expected = validate_container_number("12343054383")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Los primeros 4 caracteres deben ser letras.")
        self.assertIsNone(expected)
