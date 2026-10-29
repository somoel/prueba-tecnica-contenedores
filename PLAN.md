# Plan de ejecución y trazabilidad

Proyecto: **Prueba técnica — Control de demoras de contenedores**  
Módulo: `container_demurrage` (Odoo 17 Community)  
Repositorio: `https://github.com/somoel/prueba-tecnica-contenedores`  
Metodología: **TDD** (prueba primero, rojo → verde → refactor)  
Commits: **en español**, pequeños y descriptivos  
Subagente de código: **Beam de OpenCode Go** (`opencode-go/beam-free#high`)  
Fecha de inicio: 2026-10-29

---

## 1. Objetivo y alcance

Implementar un módulo instalable en Odoo 17 que controle la demora de contenedores:

- Catálogo de navieras, tipos de contenedor y tarifas con vigencia y tramos.
- Acuerdos por cliente y naviera: días libres extra y porcentaje de administración.
- Registro de BL con todos sus contenedores en una pantalla.
- Cálculo automático de días afuera, días libres, días de demora, cobro de naviera y cobro al cliente.
- Validaciones ISO 6346, fechas y solapamiento de periodos.
- Flujo de estados con bloqueo posterior a facturación y reapertura auditada.
- Adjuntos EIR.
- Filtros operativos para Operaciones.
- Permisos Operaciones / Facturación / Gerencia.
- Pruebas automatizadas de los nueve casos de verificación.

Además se implementan **todos** los deseables y extras:

- Cron diario de actividades.
- Importador de Excel/CSV con filas rechazadas y motivos.
- Registro de factura de naviera y diferencia contra lo calculado.
- Conversión a COP con tasas de Odoo y decisión de TRM.
- Factura en borrador al cliente, una línea por contenedor.
- PDF/HTML de liquidación por contenedor.
- Reporte mensual pagado a navieras vs facturado a clientes.

---

## 2. Decisiones de negocio

| # | Tema | Decisión |
|---|---|---|
| 1 | Conteo de días | Inclusivo: descarga y devolución cuentan. `días_afuera = (devolución - descarga).days + 1`. |
| 2 | Mismo día descarga/devolución | 1 día afuera. |
| 3 | Tarifa aplicable | La vigente en la **fecha de descarga**, aunque la devolución caiga en otra vigencia. |
| 4 | Fecha de descarga del BL | El BL tiene fecha por defecto; cada contenedor puede sobrescribirla. |
| 5 | Correcciones después de facturar | Facturado queda bloqueado. Solo Facturación/Gerencia reabre con motivo; queda auditoría y la factura se marca para revisión. Operaciones solo solicita. |
| 6 | Edición de tarifas | Solo Facturación/Gerencia. Operaciones solo lectura. |
| 7 | Porcentaje de administración | `cobro_cliente = cobro_naviera × (1 + %/100)`. |
| 8 | Días libres extra | Acuerdo por cliente + naviera, no global. |
| 9 | Tarifa faltante | No calcular cero: marcar `missing_tariff` y bloquear facturación. |
| 10 | Contenedor afuera | Estimar con `as_of_date` y marcar como estimado. |
| 11 | TRM | La de la fecha de factura al cliente, tomada de `res.currency.rate`. Sin tasa: bloquear. |
| 12 | Redondeo | 2 decimales, `HALF_UP`, con `Decimal`. |
| 13 | Festivos | Cuentan como días calendario. |
| 14 | “Recobrado” | Significa facturado al cliente, no cobrado. Se documenta. |
| 15 | Un BL, un cliente/naviera | Se asume; se deja como pregunta al cliente. |

---

## 3. Decisiones técnicas

- **Un solo módulo** `container_demurrage`, dependencias `base`, `mail`, `base_setup`, `account`.
- Cálculo puro en `utils/calculator.py`, sin ORM.
- ISO 6346 en `utils/iso6346.py`, sin ORM.
- Parseo y normalización en `utils/parsing.py`.
- Estados derivados de fechas y banderas `invoiced` / `cancelled`.
- Snapshot al facturar para inmutabilidad.
- `as_of_date` para estimados deterministas y testeables.
- Multi-compañía en todos los modelos.
- UI en español; identificadores, campos y métodos en inglés.
- Repositorio público con CI en GitHub Actions.
- Instalación limpia con y sin datos demo.

---

## 4. Entorno local

Sin Docker ni `sudo` en la máquina de desarrollo:

- Python 3.12 con `uv`.
- Odoo 17 clonado en `.odoo/odoo` (no versionado).
- PostgreSQL 16 embebido con `pgserver` en `.pgdata` (no versionado).
- Dependencias: `psycopg2-binary`, `openpyxl` opcional para XLSX.
- CI usa `odoo:17.0` + `postgres:16` en GitHub Actions.

Comandos base:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python pgserver openpyxl "psycopg2-binary==2.9.9"
git clone --depth 1 --branch 17.0 https://github.com/odoo/odoo.git .odoo/odoo
grep -vE '^(psycopg2|python-ldap)' .odoo/odoo/requirements.txt > /tmp/odoo-req.txt
uv pip install --python .venv/bin/python -r /tmp/odoo-req.txt "psycopg2-binary==2.9.9" openpyxl
.venv/bin/python scripts/pg.py start
```

---

## 5. Política TDD y de commits

### Ciclo

1. Escribir la prueba que falla.
2. Ejecutarla y confirmar el rojo correcto.
3. Implementar lo mínimo.
4. Ejecutar la suite completa.
5. Refactorizar con la suite verde.
6. Commit de prueba y commit de implementación.

### Formato de commits (español)

```text
prueba(alcance): especifica <comportamiento>
feat(alcance): implementa <comportamiento>
refactor(alcance): <cambio sin comportamiento>
fix(alcance): <corrección>
docs(alcance): <documentación>
chore(alcance): <herramientas>
ci: <pipeline>
```

Ejemplos:

```text
prueba(iso): especifica dígitos de control válidos e inválidos
feat(iso): normaliza y valida números de contenedor
prueba(calculo): especifica conteo inclusivo de días
feat(calculo): cuenta descarga y devolución de forma inclusiva
```

Cada commit debe incluir en el cuerpo el comando de prueba y el resultado rojo/verde.

### Ramas y PRs

- `main` siempre verde.
- Cada fase en rama `feat/...` o `docs/...`.
- PR en draft mientras haya rojos; CI se salta drafts.
- Merge con rebase para conservar commits pequeños.
- No squash.

---

## 6. Estructura del módulo

```text
container_demurrage/
├── __manifest__.py
├── models/
├── utils/
├── wizards/
├── views/
├── report/
├── security/
├── data/
├── demo/
└── tests/
```

---

## 7. Lista de tareas y estado

Leyenda: `[ ]` pendiente, `[~]` en curso, `[x]` hecho.

| ID | Tarea | Prueba | Estado | Commit |
|---|---|---|---|---|
| F0.1 | Repositorio, `.gitignore`, licencia, `PLAN.md` | — | [ ] | |
| F0.2 | Scripts de entorno `pg.py`, `run_odoo.sh`, `run_tests.sh` | Arranque local | [ ] | |
| F0.3 | Esqueleto del módulo | Instalación vacía | [ ] | |
| F0.4 | Workflow CI | Workflow verde | [ ] | |
| F1.1 | Tipos de contenedor | `test_container_type.py` | [ ] | |
| F1.2 | Navieras | `test_shipping_line.py` | [ ] | |
| F1.3 | Tarifas y vigencia | `test_tariff.py` | [ ] | |
| F1.4 | Tramos y continuidad | `test_tariff_tiers.py` | [ ] | |
| F1.5 | Solapamiento de tarifas | `test_tariff_overlap.py` | [ ] | |
| F1.6 | Acuerdos cliente/naviera | `test_agreement.py` | [ ] | |
| F1.7 | Grupos y ACL | `test_security.py` | [ ] | |
| F2.1 | BL y unicidad | `test_bl.py` | [ ] | |
| F2.2 | Contenedor base | `test_container.py` | [ ] | |
| F2.3 | ISO 6346 | `test_iso6346.py` | [ ] | |
| F2.4 | Validación de fechas | `test_container_dates.py` | [ ] | |
| F2.5 | Solapamiento de periodos | `test_container_overlap.py` | [ ] | |
| F2.6 | Fecha de BL y override | `test_bl_dates.py` | [ ] | |
| F2.7 | Resolución de tarifa | `test_tariff_resolution.py` | [ ] | |
| F2.8 | Resolución de acuerdo | `test_agreement_resolution.py` | [ ] | |
| F3.1 | Días y demora | `test_dates.py` | [ ] | |
| F3.2 | Cálculo por tramos | `test_calculator.py` | [ ] | |
| F3.3 | Nueve casos | `test_acceptance_cases.py` | [ ] | |
| F3.4 | Estimado `as_of_date` | `test_estimate.py` | [ ] | |
| F3.5 | Vencimiento y filtros base | `test_due.py` | [ ] | |
| F3.6 | COP/TRM | `test_currency.py` | [ ] | |
| F4.1 | Estado calculado | `test_state.py` | [ ] | |
| F4.2 | Bloqueo posfactura | `test_invoice_lock.py` | [ ] | |
| F4.3 | Reapertura auditada | `test_reopen.py` | [ ] | |
| F4.4 | Cancelación | `test_cancel.py` | [ ] | |
| F4.5 | EIR | `test_eir.py` | [ ] | |
| F5.1 | Vistas de contenedores y filtros | `test_filters.py` | [ ] | |
| F5.2 | Vista de BL y onchange | `test_bl_form.py` | [ ] | |
| F5.3 | Vistas de tarifas/acuerdos/partner | Smoke | [ ] | |
| F5.4 | Menús y accesos | Manual/ACL | [ ] | |
| F5.5 | Kanban, pivote, gráfica | Smoke | [ ] | |
| F6.1 | Cron `as_of_date` | `test_cron.py` | [ ] | |
| F6.2 | Actividades idempotentes | `test_cron.py` | [ ] | |
| F6.3 | Parseo de Excel | `test_parsing.py` | [ ] | |
| F6.4 | Asistente: analizar | `test_import_analyze.py` | [ ] | |
| F6.5 | Asistente: importar 6/4 | `test_import.py` | [ ] | |
| F6.6 | Importación idempotente | `test_import.py` | [ ] | |
| F7.1 | Factura naviera | `test_carrier_invoice.py` | [ ] | |
| F7.2 | Varianza y sobrecobro | `test_carrier_variance.py` | [ ] | |
| F8.1 | Producto de servicio | `test_invoice.py` | [ ] | |
| F8.2 | Asistente de factura | `test_invoice.py` | [ ] | |
| F8.3 | Líneas por contenedor y COP | `test_invoice.py` | [ ] | |
| F8.4 | Snapshot y bloqueo | `test_invoice_snapshot.py` | [ ] | |
| F8.5 | Fecha de factura en borrador | `test_invoice_date.py` | [ ] | |
| F9.1 | Liquidación PDF/HTML | `test_report_settlement.py` | [ ] | |
| F9.2 | Reporte mensual | `test_monthly_report.py` | [ ] | |
| F10.1 | Demo data | Instalación con demo | [ ] | |
| F10.2 | README instalación/pruebas | Manual | [ ] | |
| F10.3 | README modelo/decisiones | Manual | [ ] | |
| F10.4 | README Excel/casos/preguntas | Manual | [ ] | |
| F10.5 | README limitaciones/guion | Manual | [ ] | |
| F10.6 | `docs/tdd.md` | Manual | [ ] | |
| F10.7 | Instalación limpia y simulación evaluador | Script | [ ] | |
| F10.8 | Release `v1.0.0` | GitHub | [ ] | |

---

## 8. Casos de aceptación

| # | Días afuera | Libres | Demora | Naviera USD | Cliente USD |
|---|---:|---:|---:|---:|---:|
| 1 | 19 | 7 | 12 | 1.260,00 | 1.386,00 |
| 2 | 12 | 12 | 0 | 0,00 | 0,00 |
| 3 | 18 | 13 | 5 | 375,00 | 393,75 |
| 4 | 14 | 4 | 10 | 2.000,00 | 2.200,00 |
| 5 | 16 (estimado) | 8 | 8 | 410,00 | 451,00 |
| 6 | 7 | 7 | 0 | 0,00 | 0,00 |
| 7 | 8 | 7 | 1 | 35,00 | 38,50 |
| 8 | 1 | 7 | 0 | 0,00 | 0,00 |
| 9 | 18 | — | — | Sin tarifa 40RF Mar del Sur: bloquear | — |

Caso 5 con fecha de corte 2026-09-20. Caso 9 exige `missing_tariff`, no cero.

---

## 9. Errores del Excel y decisiones

| Fila | Error | Decisión |
|---:|---|---|
| 2 | Espacios, minúsculas, `20'`, variantes de naviera/cliente | Normalizar; la observación de +5 días ya está en el acuerdo |
| 3 | `40 dv`; `15-jul` sin año | Normalizar e inferir 2026 desde la descarga |
| 4 | `reefer` | Tipo 40RF; observación como nota |
| 5 | Duplicado de fila 4 | Rechazar por duplicado/solapamiento |
| 6 | `MSLU6135877` con dígito de control inválido (esperado 6) | Rechazar y sugerir `MSLU6135876`; no autocorregir |
| 7 | Devolución 18/09 anterior a descarga 20/09 | Rechazar |
| 8 | Cliente vacío; devolución vacía; “DEVUELTO el viernes” | Rechazar por cliente; no inferir fecha |
| 9 | “Bajó al otro día” | Fecha propia del contenedor |
| 10 | Mar del Sur 40RF sin tarifa | Importar con advertencia y bloquear facturación |

Resultado esperado: **6 importadas, 4 rechazadas**.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Alcance completo en 5 días | Gate del día 2: obligatorio verde antes de extras |
| `account` en base nueva | Job de instalación limpia en CI y local |
| Sin plan contable | Pruebas crean diario/cuentas mínimas; solo borrador |
| `wkhtmltopdf` ausente | Reporte HTML probado; PDF manual |
| Commits rojos | PRs en draft; CI solo en ready |
| Fechas reales | `as_of_date` y `freezegun` |
| Disco limitado | No versionar `.odoo`, `.venv`, `.pgdata` |

---

## 11. Bitácora de ejecución

Se actualiza al cerrar cada tarea.

| Fecha | Tarea | Resultado | Commit |
|---|---|---|---|
| 2026-10-29 | Prueba de Beam | `BEAM_OK`; subagente disponible | — |
| 2026-10-29 | Plan y trazabilidad | `PLAN.md` creado | pendiente |
