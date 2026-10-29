# -*- coding: utf-8 -*-
"""Utilidades puras de parseo y normalización para la importación."""

import re
import unicodedata
from datetime import date


def normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def _strip_accents(text):
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_key(value):
    text = normalize_text(value)
    text = _strip_accents(text)
    return text.upper()


_MONTHS = {
    "enero": 1, "ene": 1, "january": 1, "jan": 1,
    "febrero": 2, "feb": 2, "february": 2,
    "marzo": 3, "mar": 3, "march": 3,
    "abril": 4, "abr": 4, "apr": 4, "april": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6, "june": 6,
    "julio": 7, "jul": 7, "july": 7,
    "agosto": 8, "ago": 8, "aug": 8, "august": 8,
    "septiembre": 9, "sep": 9, "sept": 9, "september": 9,
    "octubre": 10, "oct": 10, "october": 10,
    "noviembre": 11, "nov": 11, "november": 11,
    "diciembre": 12, "dic": 12, "dec": 12, "december": 12,
}


def _month_number(value):
    key = normalize_key(value).lower().rstrip(".")
    if key in _MONTHS:
        return _MONTHS[key]
    if len(key) >= 3 and key[:3] in _MONTHS:
        return _MONTHS[key[:3]]
    raise ValueError("Mes inválido: %r" % value)


def normalize_container_type(value):
    if is_blank(value):
        return None
    key = normalize_key(value)
    aliases = {
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
    normalized_aliases = {normalize_key(k): v for k, v in aliases.items()}
    return normalized_aliases.get(key)


def normalize_bl(value):
    if value is None:
        return ""
    text = str(value).upper()
    text = re.sub(r"\s*-\s*", "-", text)
    return " ".join(text.split())


def is_blank(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _to_year(value):
    value = int(value)
    if value < 100:
        if value >= 70:
            value += 1900
        else:
            value += 2000
    return value


def parse_date(value, default_year=None):
    if isinstance(value, date):
        return value
    if value is None:
        raise ValueError("Fecha inválida: None")
    text = str(value).strip()
    if text == "":
        raise ValueError("Fecha vacía")

    if "T" in text:
        text = text.split("T")[0]

    # slash formats: dd/mm/yyyy, d/m/yyyy, dd/mm/yy
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 3:
            raise ValueError("Fecha inválida: %r" % value)
        day = int(parts[0])
        month = int(parts[1])
        year = _to_year(parts[2])
        return date(year, month, day)

    if "-" in text:
        parts = text.split("-")
        # ISO yyyy-mm-dd
        if len(parts) >= 3 and len(parts[0]) == 4 and parts[1].isdigit():
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            return date(year, month, day)
        # dd-mmm or dd-mmm-yyyy (month name)
        if len(parts) >= 2 and not parts[1].isdigit():
            day = int(parts[0])
            month = _month_number(parts[1])
            if len(parts) == 2:
                if default_year is None:
                    raise ValueError("Falta año por defecto")
                year = default_year
                if isinstance(year, str):
                    year = _to_year(year)
                elif year < 100:
                    year = _to_year(year)
                return date(year, month, day)
            if len(parts) == 3:
                year = _to_year(parts[2])
                return date(year, month, day)
            raise ValueError("Fecha inválida: %r" % value)
        # dd-mm-yyyy (numeric)
        if len(parts) == 3:
            day = int(parts[0])
            month = int(parts[1])
            year = _to_year(parts[2])
            return date(year, month, day)
        # dd-mm with default year
        if len(parts) == 2 and default_year is not None:
            day = int(parts[0])
            month = int(parts[1])
            year = default_year
            if isinstance(year, str):
                year = _to_year(year)
            elif year < 100:
                year = _to_year(year)
            return date(year, month, day)
        raise ValueError("Fecha inválida: %r" % value)

    raise ValueError("Fecha inválida: %r" % value)
