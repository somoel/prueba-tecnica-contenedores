# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DemurrageTariff(models.Model):
    _name = "demurrage.tariff"
    _description = "Tarifa de demoras"
    _order = "shipping_line_id, container_type_id, valid_from desc"

    name = fields.Char(compute="_compute_name", store=True)
    shipping_line_id = fields.Many2one(
        "demurrage.shipping.line", required=True, ondelete="restrict")
    container_type_id = fields.Many2one(
        "demurrage.container.type", required=True, ondelete="restrict")
    valid_from = fields.Date(required=True)
    valid_to = fields.Date()
    free_days = fields.Integer(required=True, default=0)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda self: self.env.ref("base.USD").id)
    tier_ids = fields.One2many(
        "demurrage.tariff.tier", "tariff_id", string="Tramos")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    tier_count = fields.Integer(compute="_compute_tier_count")

    @api.depends("shipping_line_id.code", "container_type_id.code", "valid_from")
    def _compute_name(self):
        for record in self:
            line_code = record.shipping_line_id.code or ""
            type_code = record.container_type_id.code or ""
            vf = record.valid_from.strftime("%Y-%m-%d") if record.valid_from else ""
            record.name = f"{line_code}-{type_code}-{vf}"

    @api.depends("tier_ids")
    def _compute_tier_count(self):
        for record in self:
            record.tier_count = len(record.tier_ids)

    @api.constrains("valid_from", "valid_to")
    def _check_validity_dates(self):
        for record in self:
            if record.valid_to and record.valid_to < record.valid_from:
                raise ValidationError(
                    "La fecha de fin de vigencia no puede ser anterior a la de inicio.")

    @api.constrains("free_days")
    def _check_free_days(self):
        for record in self:
            if record.free_days < 0:
                raise ValidationError("Los días libres no pueden ser negativos.")

    @api.constrains("shipping_line_id", "container_type_id", "valid_from",
                    "valid_to", "company_id", "active")
    def _check_overlap(self):
        for record in self:
            if not record.active:
                continue
            if not (record.shipping_line_id and record.container_type_id
                    and record.valid_from):
                continue
            others = self.search([
                ("id", "!=", record.id),
                ("shipping_line_id", "=", record.shipping_line_id.id),
                ("container_type_id", "=", record.container_type_id.id),
                ("company_id", "=", record.company_id.id),
                ("active", "=", True),
            ])
            rec_end = record.valid_to or date.max
            for other in others:
                other_end = other.valid_to or date.max
                if record.valid_from <= other_end and other.valid_from <= rec_end:
                    raise ValidationError(
                        "Existe otra tarifa solapada para la misma naviera, "
                        "tipo de contenedor y compañía.")


class DemurrageTariffTier(models.Model):
    _name = "demurrage.tariff.tier"
    _description = "Tramo de tarifa"
    _order = "tariff_id, day_from"

    _sql_constraints = [
        (
            "tariff_day_from_unique",
            "unique(tariff_id, day_from)",
            "El día de inicio del tramo debe ser único dentro de la tarifa.",
        ),
    ]

    tariff_id = fields.Many2one(
        "demurrage.tariff", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    day_from = fields.Integer(required=True, default=1)
    day_to = fields.Integer(default=0)
    rate_per_day = fields.Monetary(
        currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        related="tariff_id.currency_id", store=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("day_from", "day_to")
    def _compute_name(self):
        for record in self:
            if record.day_to == 0:
                record.name = f"Día {record.day_from} en adelante"
            else:
                record.name = f"Días {record.day_from}–{record.day_to}"

    @api.constrains("rate_per_day")
    def _check_rate(self):
        for record in self:
            if record.rate_per_day <= 0:
                raise ValidationError("La tarifa por día debe ser mayor a cero.")

    @api.constrains("day_from", "day_to")
    def _check_day_range(self):
        for record in self:
            if record.day_to != 0 and record.day_to < record.day_from:
                raise ValidationError(
                    "El día fin no puede ser menor que el día inicio.")

    @api.constrains("tariff_id", "day_from", "day_to")
    def _check_continuity(self):
        for record in self:
            tariff = record.tariff_id
            tiers = tariff.tier_ids.sorted(key=lambda t: t.day_from)
            if not tiers:
                continue
            if tiers[0].day_from != 1:
                raise ValidationError("Los tramos deben comenzar en el día 1.")
            for i, tier in enumerate(tiers):
                if tier.day_to == 0 and i != len(tiers) - 1:
                    raise ValidationError(
                        "Solo el último tramo puede ser abierto.")
            if tiers[-1].day_to != 0:
                raise ValidationError("El último tramo debe ser abierto.")
            for i in range(1, len(tiers)):
                if tiers[i].day_from != tiers[i - 1].day_to + 1:
                    raise ValidationError(
                        "Los tramos deben ser continuos, sin huecos ni solapamientos.")
