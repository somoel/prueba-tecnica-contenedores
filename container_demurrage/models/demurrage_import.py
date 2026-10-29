# -*- coding: utf-8 -*-
import base64
import csv
from datetime import date
import io
import json

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from odoo.addons.container_demurrage.utils.parsing import (
    normalize_text, normalize_key, normalize_container_type, normalize_bl,
    parse_date, is_blank,
)
from odoo.addons.container_demurrage.utils.iso6346 import (
    normalize_container_number, validate_container_number,
)


def _norm_header(h):
    return normalize_key(h).lstrip("#").strip()


_HEADER_MAP = {
    "CONTENEDOR": "container",
    "CONTAINER": "container",
    "NUMERO CONTENEDOR": "container",
    "TIPO": "type",
    "TIPO DE CONTENEDOR": "type",
    "TYPE": "type",
    "NAVIERA": "carrier",
    "CARRIER": "carrier",
    "SHIPPING LINE": "carrier",
    "BL": "bl",
    "BILL OF LADING": "bl",
    "CLIENTE": "customer",
    "CUSTOMER": "customer",
    "PARTNER": "customer",
    "F DESCARGA": "discharge",
    "F. DESCARGA": "discharge",
    "FECHA DESCARGA": "discharge",
    "DISCHARGE": "discharge",
    "DISCHARGE DATE": "discharge",
    "F DEVOLUCION": "return",
    "F. DEVOLUCION": "return",
    "FECHA DEVOLUCION": "return",
    "RETURN": "return",
    "RETURN DATE": "return",
    "OBSERVACIONES": "observations",
    "OBSERVATION": "observations",
    "OBSERVATIONS": "observations",
    "NOTES": "observations",
    "OBS": "observations",
}


class DemurrageImportWizard(models.TransientModel):
    _name = "demurrage.import.wizard"
    _description = "Asistente de importación de contenedores"

    file = fields.Binary(required=True, attachment=True)
    filename = fields.Char()
    line_ids = fields.One2many(
        "demurrage.import.line", "wizard_id", string="Líneas")
    state = fields.Selection(
        [("draft", "Borrador"), ("analyzed", "Analizado"),
         ("done", "Importado")], default="draft")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company)

    total_count = fields.Integer(compute="_compute_counts")
    importable_count = fields.Integer(compute="_compute_counts")
    imported_count = fields.Integer(compute="_compute_counts")
    rejected_count = fields.Integer(compute="_compute_counts")
    warning_count = fields.Integer(compute="_compute_counts")

    @api.depends("line_ids", "line_ids.status", "line_ids.container_id")
    def _compute_counts(self):
        for w in self:
            lines = w.line_ids
            w.total_count = len(lines)
            w.importable_count = len(lines.filtered(
                lambda l: l.status in ("ok", "normalized", "warning")))
            w.imported_count = len(lines.filtered(lambda l: bool(l.container_id)))
            w.rejected_count = len(lines.filtered(lambda l: l.status == "rejected"))
            w.warning_count = len(lines.filtered(lambda l: l.status == "warning"))

    def _read_rows(self):
        if not self.file:
            return []
        raw = self.file
        if isinstance(raw, str):
            raw = raw.encode()
        # Aceptar base64 o bytes crudos
        try:
            data = base64.b64decode(raw, validate=True)
        except Exception:
            data = raw
        # Si el decode produjo vacío o idéntico inválido, usar originales
        if not data:
            data = raw
        name = (self.filename or "").lower()
        is_xlsx = data[:2] == b"PK" or name.endswith(".xlsx") or name.endswith(".xls")
        if is_xlsx:
            try:
                import openpyxl
            except Exception:
                raise ValidationError("openpyxl no está disponible.")
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [str(h) if h is not None else "" for h in rows[0]]
            out = []
            for r in rows[1:]:
                if all(v is None or str(v).strip() == "" for v in r):
                    continue
                out.append((headers, list(r)))
            return out
        # CSV
        text = data.decode("utf-8-sig")
        # detect delimiter
        first = text.splitlines()[0] if text.splitlines() else ""
        delimiter = ";" if first.count(";") > first.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            return []
        headers = rows[0]
        out = []
        for r in rows[1:]:
            if all(str(v).strip() == "" for v in r):
                continue
            out.append((headers, r))
        return out

    def _map_headers(self, headers):
        mapping = {}
        for idx, h in enumerate(headers):
            key = _norm_header(h)
            # direct
            field = _HEADER_MAP.get(key)
            if field is None:
                # try without spaces
                compact = key.replace(" ", "")
                for k, v in _HEADER_MAP.items():
                    if k.replace(" ", "") == compact:
                        field = v
                        break
            if field is not None and field not in mapping.values():
                mapping[field] = idx
        return mapping

    def _find_shipping_line(self, raw):
        key = normalize_key(raw)
        lines = self.env["demurrage.shipping.line"].search([])
        matches = lines.filtered(
            lambda l: normalize_key(l.name) == key or normalize_key(l.code) == key)
        if len(matches) == 1:
            return matches[0]
        # contains
        matches = lines.filtered(
            lambda l: key in normalize_key(l.name) or normalize_key(l.name) in key
            or key in normalize_key(l.code))
        if len(matches) == 1:
            return matches[0]
        return self.env["demurrage.shipping.line"]

    def _find_partner(self, raw):
        key = normalize_key(raw)
        partners = self.env["res.partner"].search([])
        # exact
        exact = partners.filtered(lambda p: normalize_key(p.name) == key)
        if len(exact) == 1:
            return exact[0]
        # prefix or contains
        cand = partners.filtered(
            lambda p: normalize_key(p.name).startswith(key)
            or key.startswith(normalize_key(p.name))
            or key in normalize_key(p.name)
            or normalize_key(p.name) in key)
        if len(cand) == 1:
            return cand[0]
        # if multiple, try exact normalized contains both directions
        if len(cand) > 1:
            # prefer the one where normalized names are closest
            pass
        return self.env["res.partner"] if len(cand) != 1 else cand[0]

    def _find_container_type(self, code):
        ct = self.env["demurrage.container.type"].search(
            [("code", "=", code)], limit=1)
        return ct

    def action_analyze(self):
        self.ensure_one()
        # remove old lines
        self.line_ids.unlink()
        parsed = self._read_rows()
        # We need two passes: first parse each row into a dict of values,
        # then analyze with duplicate detection.
        row_data_list = []
        for headers, r in parsed:
            mapping = self._map_headers(headers)
            def get(field):
                idx = mapping.get(field)
                if idx is None or idx >= len(r):
                    return ""
                v = r[idx]
                return "" if v is None else v
            row_data_list.append({
                "container_raw": get("container"),
                "type_raw": get("type"),
                "carrier_raw": get("carrier"),
                "bl_raw": get("bl"),
                "customer_raw": get("customer"),
                "discharge_raw": get("discharge"),
                "return_raw": get("return"),
                "observations": get("observations"),
            })

        # track previous accepted lines for duplicate detection
        previous_lines = []  # list of (container_number, start, end, row_number)
        # existing containers
        existing_containers = self.env["demurrage.container"].search([])

        new_lines = []
        for i, rd in enumerate(row_data_list, start=1):
            row_number = i
            raw_json = json.dumps({k: (str(v) if v is not None else "") for k, v in rd.items()}, ensure_ascii=False)
            vals = {
                "wizard_id": self.id,
                "row_number": row_number,
                "raw_json": raw_json,
                "container_number": "",
                "type_code": "",
                "carrier_name": normalize_text(rd["carrier_raw"]),
                "customer_name": normalize_text(rd["customer_raw"]),
                "bl_name": normalize_text(rd["bl_raw"]),
                "discharge_raw": normalize_text(rd["discharge_raw"]),
                "return_raw": normalize_text(rd["return_raw"]),
                "observations": normalize_text(rd["observations"]),
                "status": "pending",
                "message": "",
            }

            # container normalize + validate
            container_raw = rd["container_raw"]
            container_number = normalize_container_number(container_raw)
            vals["container_number"] = container_number

            normalized_flag = False
            if str(container_raw).strip() != container_number and str(container_raw).strip() != "":
                normalized_flag = True

            is_valid, err, _ = validate_container_number(container_number)
            if not is_valid:
                vals["status"] = "rejected"
                vals["message"] = "Número de contenedor inválido: %s" % (err or container_number)
                new_lines.append(vals)
                continue

            # type
            type_code = normalize_container_type(rd["type_raw"])
            if not type_code:
                vals["status"] = "rejected"
                vals["message"] = "Tipo de contenedor no reconocido: %s" % normalize_text(rd["type_raw"])
                new_lines.append(vals)
                continue
            vals["type_code"] = type_code
            if normalize_key(rd["type_raw"]) != normalize_key(type_code):
                normalized_flag = True

            # naviera
            shipping_line = self._find_shipping_line(rd["carrier_raw"])
            if not shipping_line:
                vals["status"] = "rejected"
                vals["message"] = "Naviera no encontrada o ambigua: %s" % normalize_text(rd["carrier_raw"])
                new_lines.append(vals)
                continue
            if normalize_key(rd["carrier_raw"]) not in (normalize_key(shipping_line.name), normalize_key(shipping_line.code)):
                normalized_flag = True

            # cliente
            partner = self._find_partner(rd["customer_raw"])
            if not partner:
                vals["status"] = "rejected"
                vals["message"] = "Cliente no encontrado/ambiguo: %s" % normalize_text(rd["customer_raw"])
                new_lines.append(vals)
                continue
            if normalize_text(rd["customer_raw"]) != (partner.name or ""):
                normalized_flag = True

            # BL
            bl_name = normalize_bl(rd["bl_raw"])
            if is_blank(bl_name):
                vals["status"] = "rejected"
                vals["message"] = "BL requerido."
                new_lines.append(vals)
                continue
            vals["bl_name"] = bl_name
            if normalize_text(rd["bl_raw"]) != bl_name:
                normalized_flag = True

            # dates
            discharge_raw = normalize_text(rd["discharge_raw"])
            try:
                discharge_date = parse_date(discharge_raw)
            except Exception:
                vals["status"] = "rejected"
                vals["message"] = "Fecha de descarga inválida: %s" % discharge_raw
                new_lines.append(vals)
                continue
            # discharge must have year: parse_date already requires; if input dd-mmm without year it raises. ok.
            if "/" not in discharge_raw and "-" in discharge_raw:
                # if month name and only 2 parts, would have raised; fine
                pass

            return_raw = normalize_text(rd["return_raw"])
            return_date = None
            if not is_blank(return_raw):
                try:
                    return_date = parse_date(return_raw, default_year=discharge_date.year)
                except Exception:
                    vals["status"] = "rejected"
                    vals["message"] = "Fecha de devolución inválida: %s" % return_raw
                    new_lines.append(vals)
                    continue
                if return_date < discharge_date:
                    vals["status"] = "rejected"
                    vals["message"] = "La fecha de devolución no puede ser anterior a la descarga."
                    new_lines.append(vals)
                    continue
                from odoo import fields as odf
                if return_date > odf.Date.today():
                    vals["status"] = "rejected"
                    vals["message"] = "La fecha de devolución no puede ser futura."
                    new_lines.append(vals)
                    continue
                if return_raw != return_date.isoformat():
                    normalized_flag = True
            if discharge_raw != discharge_date.isoformat():
                normalized_flag = True

            vals["discharge_date"] = discharge_date
            vals["return_date"] = return_date

            # duplicate detection
            rec_start = discharge_date
            rec_end = return_date if return_date else None
            dup_row = None
            for (prev_container, prev_start, prev_end, prev_row) in previous_lines:
                if prev_container == container_number:
                    prev_e = prev_end if prev_end else date.max
                    cur_e = rec_end if rec_end else date.max
                    if rec_start <= prev_e and prev_start <= cur_e:
                        dup_row = prev_row
                        break
            if dup_row is not None:
                vals["status"] = "rejected"
                vals["message"] = "Duplicado de la fila %d." % dup_row
                new_lines.append(vals)
                continue

            # existing containers duplicate
            dup_existing = False
            for oc in existing_containers:
                if oc.container_number != container_number:
                    continue
                if not oc.discharge_date:
                    continue
                other_start = oc.discharge_date
                other_end = oc.return_date if oc.return_date else date.max
                cur_e = rec_end if rec_end else date.max
                if rec_start <= other_end and other_start <= cur_e:
                    dup_existing = True
                    break
            if dup_existing:
                vals["status"] = "rejected"
                vals["message"] = "Ya existe un contenedor con ese número en ese periodo."
                new_lines.append(vals)
                continue

            # tariff check
            tariff = self.env["demurrage.tariff"].search([
                ("shipping_line_id", "=", shipping_line.id),
                ("container_type_id", "=", self.env["demurrage.container.type"].search([("code", "=", type_code)], limit=1).id),
                ("company_id", "=", self.company_id.id),
                ("valid_from", "<=", discharge_date),
                "|", ("valid_to", "=", False),
                ("valid_to", ">=", discharge_date),
                ("active", "=", True),
            ], limit=1)
            if not tariff:
                vals["status"] = "warning"
                vals["message"] = "Sin tarifa para %s / %s / %s." % (
                    shipping_line.name, type_code, discharge_date)
            else:
                vals["status"] = "normalized" if normalized_flag else "ok"
                vals["message"] = ""

            # store normalized partner/shipping? not fields. keep names.
            new_lines.append(vals)
            # track previous if importable (ok/normalized/warning)
            if vals["status"] in ("ok", "normalized", "warning"):
                previous_lines.append((container_number, discharge_date, return_date, row_number))

        # create lines
        for v in new_lines:
            # remove helper non-fields
            self.env["demurrage.import.line"].create(v)

        self.state = "analyzed"


    def action_import(self):
        self.ensure_one()
        for line in self.line_ids.filtered(lambda l: l.status in ("ok", "normalized", "warning")):
            try:
                shipping_line = self._find_shipping_line(line.carrier_name)
                partner = self._find_partner(line.customer_name)
                ctype = self.env["demurrage.container.type"].search(
                    [("code", "=", line.type_code)], limit=1)
                bl_name = normalize_bl(line.bl_name)
                # find or create BL
                bl = self.env["demurrage.bl"].search([
                    ("name", "=", bl_name),
                    ("shipping_line_id", "=", shipping_line.id),
                    ("company_id", "=", self.company_id.id),
                ], limit=1)
                if bl and bl.partner_id != partner:
                    line.status = "rejected"
                    line.message = "El BL %s pertenece a otro cliente." % bl_name
                    continue
                if not bl:
                    bl = self.env["demurrage.bl"].create({
                        "name": bl_name,
                        "shipping_line_id": shipping_line.id,
                        "partner_id": partner.id,
                        "company_id": self.company_id.id,
                        "discharge_date": line.discharge_date,
                    })
                container = self.env["demurrage.container"].create({
                    "container_number": line.container_number,
                    "bl_id": bl.id,
                    "container_type_id": ctype.id,
                    "discharge_date": line.discharge_date,
                    "return_date": line.return_date or False,
                })
                line.bl_id = bl.id
                line.container_id = container.id
                if container.missing_tariff:
                    line.status = "warning"
                    if not line.message:
                        line.message = "Sin tarifa para %s." % shipping_line.name
                else:
                    line.status = "imported"
            except Exception as e:
                line.status = "rejected"
                line.message = str(e)
        self.state = "done"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Importación finalizada",
                "message": "Importación completada.",
                "type": "success",
            },
        }


class DemurrageImportLine(models.TransientModel):
    _name = "demurrage.import.line"
    _description = "Línea de importación"

    wizard_id = fields.Many2one(
        "demurrage.import.wizard", required=True, ondelete="cascade")
    row_number = fields.Integer()
    raw_json = fields.Text()
    container_number = fields.Char()
    type_code = fields.Char()
    carrier_name = fields.Char()
    customer_name = fields.Char()
    bl_name = fields.Char()
    discharge_raw = fields.Char()
    return_raw = fields.Char()
    observations = fields.Text()
    discharge_date = fields.Date()
    return_date = fields.Date()
    status = fields.Selection([
        ("pending", "Pendiente"),
        ("ok", "OK"),
        ("normalized", "Normalizado"),
        ("warning", "Advertencia"),
        ("rejected", "Rechazado"),
        ("imported", "Importado"),
    ], default="pending")
    message = fields.Text()
    container_id = fields.Many2one("demurrage.container")
    bl_id = fields.Many2one("demurrage.bl")
