# Bitácora TDD

Cada comportamiento se especificó primero con una prueba. Los commits `prueba(...)` contienen la especificación en rojo y los `feat(...)` la implementación en verde. El push se hizo por hitos verdes; el HEAD de `main` está verde.

Comando general:

```bash
scripts/run_tests.sh
```

## Ciclos principales

| Ciclo | Prueba | Implementación | Commits |
|---|---|---|---|
| Catálogo de tipos y navieras | `tests/test_catalog.py` | `models/demurrage_container_type.py`, `demurrage_shipping_line.py` | `2bb1c28` / `1ba5d3e` |
| Tarifas, vigencia y tramos | `tests/test_tariff.py` | `models/demurrage_tariff.py` | `348c832` / `f695c61` |
| Acuerdos por cliente y naviera | `tests/test_agreement.py` | `models/demurrage_customer_agreement.py` | `3e69a3f` / `3ac60bf` |
| ISO 6346 | `tests/test_iso6346.py` | `utils/iso6346.py` | `6aece53` / `dad3472` |
| BL y contenedores | `tests/test_bl_container.py` | `models/demurrage_bl.py`, `demurrage_container.py` | `6de150f` / `1fc6f2a` |
| Fechas y solapamiento | `tests/test_container_constraints.py` | `models/demurrage_container.py` | `06728a3` / `c50623e` |
| Días y tramos | `tests/test_calculator.py` | `utils/dates.py`, `utils/calculator.py` | `b3a9265` / `ea57f5e` |
| Casos 1–5 | `tests/test_acceptance_cases.py` | campos calculados del contenedor | `e2cc906` / `1df9fc2` |
| Casos 6–9, vencimiento y TRM | `tests/test_extended_cases.py` | `_get_exchange_rate`, `is_due_soon`, `is_overdue` | `071bf31` / `872aaef` |
| Seguridad y ACL | `tests/test_security.py` | grupos, CSV de ACL, `demurrage.correction` | `30b85b5` / `32d178f` |
| Estados, bloqueo y reapertura | `tests/test_states.py` | `action_mark_invoiced`, `action_reopen`, snapshots | `bf59b16` / `7c6247d` |
| EIR | `tests/test_eir.py` | M2M de adjuntos y validaciones | `8848eb3` / `d663ac5` |
| Wizards de estado | `tests/test_state_wizards.py` | `wizards/demurrage_state_wizards.py` | `1687681` / `b1570e1` |
| Vistas, filtros y menús | `tests/test_views.py` | `views/*.xml` | `4131a02` / `8de5f0f` |
| Parseo de importación | `tests/test_parsing.py` | `utils/parsing.py` | `4933f5e` / `20415e5` |
| Importador 6/4 | `tests/test_import.py` | `models/demurrage_import.py` | `7a50247` / `0bd4b76` |
| Cron y actividades | `tests/test_cron.py` | `_cron_daily`, `data/ir_cron.xml` | `4515f6e` / `ba77a74` |
| Conciliación naviera | `tests/test_carrier_invoice.py` | `demurrage_carrier_invoice.py` | `451bde1` / `fe7c4f6` |
| Factura en borrador | `tests/test_invoice.py` | `wizards/demurrage_invoice_wizard.py`, `account_move.py` | `2f86e04` / `d82421c` |
| Reportes | `tests/test_reports.py` | QWeb, wizard mensual | `ab6bb54` / `6f96f97` |
| Demo | instalación con demo | `demo/demurrage_demo.xml` | `3d56468` |

## Correcciones durante el ciclo

- `3647551` — se separó el estado del cálculo de la alerta de TRM para que los casos USD no dependieran de una tasa configurada.
- `a7dc964` — se reemplazaron números ISO inválidos en pruebas de BL.
- `30ffb9f` — el CI de Odoo necesitó `HOST/PORT/USER/PASSWORD` porque la imagen oficial agrega sus propios parámetros de base de datos.

## Evidencia de rojo/verde

Cada commit `prueba(...)` incluye en su cuerpo el comando y el fallo observado. Los commits `feat(...)` incluyen el comando y el resultado verde. Ejemplos:

```text
prueba(iso): especifica validación de números de contenedor

Rojo: ImportError al importar normalize_container_number.
Comando: scripts/run_tests.sh --test-tags=/container_demurrage:TestISO6346
```

```text
feat(iso): agrega normalización y validación ISO 6346

Verde: 12 pruebas, 0 fallos.
Comando: scripts/run_tests.sh --test-tags=/container_demurrage:TestISO6346
```

## Resultado final

```text
container_demurrage: 204 tests
0 failed, 0 error(s)
```
