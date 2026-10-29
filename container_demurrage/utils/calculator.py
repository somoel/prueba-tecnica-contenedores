# -*- coding: utf-8 -*-
"""Calculadora pura de demoras por tramos tarifarios."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple


CENT = Decimal("0.01")


@dataclass(frozen=True)
class Tier:
    day_from: int
    day_to: Optional[int]
    rate: Decimal


@dataclass(frozen=True)
class BreakdownLine:
    label: str
    days: int
    rate: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class Calculation:
    days_out: int
    free_days: int
    demurrage_days: int
    carrier_amount: Decimal
    customer_amount: Decimal
    lines: Tuple[BreakdownLine, ...]


def _q(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _label(day_from, day_to):
    if day_to is None:
        return "Día {} en adelante".format(day_from)
    if day_from == day_to:
        return "Día {}".format(day_from)
    return "Días {}–{}".format(day_from, day_to)


def calculate(days_out, free_days, tiers, admin_percent=Decimal("10")):
    days_out = int(days_out)
    free_days = int(free_days)
    admin_percent = Decimal(str(admin_percent))

    demurrage_days = max(days_out - free_days, 0)

    if demurrage_days == 0:
        return Calculation(
            days_out=days_out,
            free_days=free_days,
            demurrage_days=0,
            carrier_amount=Decimal("0.00"),
            customer_amount=Decimal("0.00"),
            lines=(),
        )

    # Días cubiertos por cada tramo dentro del rango de demora.
    covered_per_tier = []
    for tier in tiers:
        lo = max(tier.day_from, 1)
        hi = tier.day_to if tier.day_to is not None else demurrage_days
        hi = min(hi, demurrage_days)
        days = hi - lo + 1 if hi >= lo else 0
        covered_per_tier.append((tier, days))

    total_covered = sum(d for _, d in covered_per_tier)
    if total_covered != demurrage_days:
        raise ValueError("Los tramos no cubren todos los días de demora")

    lines = []
    carrier = Decimal("0.00")
    for tier, days in covered_per_tier:
        if days <= 0:
            continue
        rate = Decimal(str(tier.rate))
        subtotal = _q(Decimal(days) * rate)
        carrier = carrier + subtotal
        lines.append(
            BreakdownLine(
                label=_label(tier.day_from, tier.day_to),
                days=days,
                rate=rate,
                subtotal=subtotal,
            )
        )

    customer = _q(carrier * (Decimal("1") + admin_percent / Decimal("100")))
    return Calculation(
        days_out=days_out,
        free_days=free_days,
        demurrage_days=demurrage_days,
        carrier_amount=carrier.quantize(CENT, rounding=ROUND_HALF_UP),
        customer_amount=customer,
        lines=tuple(lines),
    )
