# -*- coding: utf-8 -*-
"""Utilidades puras de fechas para el control de demoras."""

from datetime import date, timedelta


def days_between(discharge, end):
    """Días inclusivos entre descarga y fin."""
    if end < discharge:
        raise ValueError("La fecha final no puede ser anterior a la de descarga.")
    return (end - discharge).days + 1


def last_free_day(discharge, free_days):
    """Último día libre (inclusive) dado el número de días libres."""
    return discharge + timedelta(days=free_days - 1)
