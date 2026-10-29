# -*- coding: utf-8 -*-
"""Utilidades puras para validar números de contenedor ISO 6346."""

_LETTER_VALUES = {
    "A": 10, "B": 12, "C": 13, "D": 14, "E": 15, "F": 16, "G": 17,
    "H": 18, "I": 19, "J": 20, "K": 21, "L": 23, "M": 24, "N": 25,
    "O": 26, "P": 27, "Q": 28, "R": 29, "S": 30, "T": 31, "U": 32,
    "V": 34, "W": 35, "X": 36, "Y": 37, "Z": 38,
}

_VALID_FOURTH_LETTERS = {"U", "J", "Z"}


def normalize_container_number(raw):
    if raw is None:
        return ""
    return str(raw).replace(" ", "").upper()


def _is_valid_format(number):
    if len(number) != 11:
        return False
    if not number[:4].isalpha() or not number[:4].isascii():
        return False
    if number[3] not in _VALID_FOURTH_LETTERS:
        return False
    if not number[4:].isdigit():
        return False
    return True


def calculate_check_digit(number):
    if not isinstance(number, str):
        number = "" if number is None else str(number)
    number = number.replace(" ", "").upper()
    if not _is_valid_format(number):
        return None
    total = 0
    for index, char in enumerate(number[:10]):
        if char.isdigit():
            value = int(char)
        else:
            value = _LETTER_VALUES[char]
        total += value * (2 ** index)
    remainder = total % 11
    if remainder == 10:
        return 0
    return remainder


def validate_container_number(raw):
    number = normalize_container_number(raw)
    if len(number) != 11:
        return (False, "El número debe tener 11 caracteres.", None)
    if not (number[:4].isalpha() and number[:4].isascii()):
        return (False, "Los primeros 4 caracteres deben ser letras.", None)
    if number[3] not in _VALID_FOURTH_LETTERS:
        return (False, "La cuarta letra debe ser U, J o Z.", None)
    if not (number[4:].isdigit() and number[4:].isascii()):
        return (False, "Los últimos 7 caracteres deben ser dígitos.", None)

    expected = calculate_check_digit(number)
    provided = int(number[10])
    if provided != expected:
        return (False, "Dígito de control inválido: se esperaba {}.".format(expected), expected)
    return (True, None, expected)
