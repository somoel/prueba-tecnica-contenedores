# Control de demoras de contenedores — Odoo 17

Módulo `container_demurrage` para **Logística Puerto Alto S.A.S.** (caso ficticio de la prueba técnica).

![CI](https://github.com/somoel/prueba-tecnica-contenedores/actions/workflows/ci.yml/badge.svg)

- **Repositorio:** https://github.com/somoel/prueba-tecnica-contenedores
- **Release:** https://github.com/somoel/prueba-tecnica-contenedores/releases/tag/v1.0.1
- **Plataforma:** Odoo 17 Community, Python 3.12, PostgreSQL 16
- **Estado:** instalable en base nueva, con y sin datos demo
- **Pruebas:** 204 pruebas ejecutadas, 0 fallos, 0 errores
- **Metodología:** TDD, con commits pequeños en español
- **Trazabilidad:** [`PLAN.md`](PLAN.md) y [`docs/tdd.md`](docs/tdd.md)

---

## 1. Qué resuelve

El módulo reemplaza el control en Excel de demoras de contenedores:

1. Catálogo de navieras, tipos de contenedor y tarifas con vigencia y tramos variables.
2. Acuerdos por cliente + naviera: días libres extra y porcentaje de administración.
3. Registro de un BL con todos sus contenedores en una sola pantalla.
4. Cálculo automático de días afuera, días libres, días de demora, cobro de naviera y cobro al cliente.
5. Validaciones ISO 6346, fechas y solapamiento de periodos.
6. Flujo de estados con bloqueo posterior a facturación y reapertura auditada.
7. Adjuntos EIR.
8. Filtros operativos: por vencer, vencidos, devueltos sin facturar.
9. Permisos Operaciones / Facturación / Gerencia.
10. Pruebas automatizadas de los nueve casos de verificación.

Además incluye todos los deseables y extras:

- Cron diario con actividades para Marcela.
- Importador CSV/XLSX con análisis, filas rechazadas y motivos.
- Factura de naviera y detección de sobrecobro.
- Conversión a COP con tasas de Odoo y decisión de TRM.
- Factura en borrador al cliente, una línea por contenedor.
- PDF de liquidación por contenedor.
- Reporte mensual pagado a navieras vs facturado a clientes.

---

## 2. Requisitos e instalación

### Requisitos

- Odoo 17 Community.
- PostgreSQL 12 o superior.
- Python 3.10 o superior (probado con 3.12).
- `account`, `mail`, `base_setup`, `sale` (dependencias estándar de Odoo).

### Instalación estándar

1. Copia la carpeta `container_demurrage` al directorio de addons de Odoo.
2. Reinicia Odoo.
3. Activa el modo desarrollador.
4. Ve a **Aplicaciones**, actualiza la lista y busca **Control de demoras de contenedores**.
5. Instala el módulo.

### Instalación por línea de comandos

```bash
odoo-bin \
  --addons-path=/ruta/a/addons \
  --db_host=localhost --db_port=5432 \
  --db_user=odoo --db_password=odoo \
  -d demurrage_db -i container_demurrage --stop-after-init
```

Con datos demo:

```bash
odoo-bin ... -d demurrage_demo -i container_demurrage --stop-after-init
```

> El PDF de liquidación usa el motor de reportes de Odoo (`wkhtmltopdf`). El HTML del reporte funciona sin él; el PDF requiere tenerlo instalado.

---

## 3. Cómo probar

### Suite completa

```bash
scripts/run_tests.sh
```

Equivale a:

```bash
odoo-bin \
  --addons-path=.odoo/odoo/addons,. \
  --db_host=.pgdata --db_port=5432 --db_user=odoo --db_password=odoo \
  -d demurrage_test -i container_demurrage --without-demo=all \
  --test-enable --test-tags=/container_demurrage \
  --stop-after-init --log-level=test
```

### Una prueba puntual

```bash
scripts/run_tests.sh --test-tags=/container_demurrage:TestAcceptanceCases
```

### Instalación limpia

```bash
scripts/clean_install.sh demurrage_clean no
scripts/clean_install.sh demurrage_demo demo
```

### Entorno local sin sudo

El repositorio incluye scripts para levantar PostgreSQL embebido y Odoo desde un clon local:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python pgserver openpyxl "psycopg2-binary==2.9.9"
git clone --depth 1 --branch 17.0 https://github.com/odoo/odoo.git .odoo/odoo
grep -vE '^(psycopg2|python-ldap)' .odoo/odoo/requirements.txt > /tmp/odoo-req.txt
uv pip install --python .venv/bin/python -r /tmp/odoo-req.txt "psycopg2-binary==2.9.9" openpyxl
.venv/bin/python scripts/pg.py start
scripts/run_odoo.sh
```

---

## 4. Datos demo

El módulo incluye `demo/demurrage_demo.xml` con:

- Naviera Atlántico y Mar del Sur Line.
- Los cuatro tipos de contenedor.
- Todas las tarifas de la prueba, con sus vigencias y tramos.
- Los cuatro clientes y sus acuerdos.
- Contenedores de los nueve casos.
- Contenedores abiertos para mostrar “por vencer” y “vencido”.
- Caso sin tarifa 40RF Mar del Sur.

La muestra original del Excel está en:

- `sample_data/control_contenedores_2026.csv` (para el usuario).
- `container_demurrage/tests/data/control_contenedores_2026.csv` (para las pruebas).

---

## 5. Modelo de datos

```text
res.partner 1---n demurrage.customer.agreement n---1 demurrage.shipping.line
demurrage.shipping.line 1---n demurrage.tariff 1---n demurrage.tariff.tier
demurrage.shipping.line 1---n demurrage.bl 1---n demurrage.container n---1 demurrage.container.type
demurrage.container n---1 demurrage.tariff           (calculada)
demurrage.container n---n ir.attachment              (EIR)
demurrage.container 1---n demurrage.correction       (auditoría)
demurrage.container 1---n demurrage.carrier.invoice.line n---1 demurrage.carrier.invoice
demurrage.container n---1 account.move               (factura en borrador)
```

| Modelo | Por qué |
|---|---|
| `demurrage.shipping.line` | Naviera; las tarifas y acuerdos dependen de ella. |
| `demurrage.container.type` | Catálogo extensible; la tarifa se resuelve por tipo. |
| `demurrage.tariff` | Tarifa por naviera + tipo + vigencia. Separar la vigencia permite aplicar la tarifa de la fecha de descarga. |
| `demurrage.tariff.tier` | Cada naviera define una cantidad distinta de tramos. Una fila por tramo permite calcular día por día y mostrar el desglose. |
| `demurrage.customer.agreement` | Los días extra y el porcentaje son negociados por cliente **y** naviera. |
| `demurrage.bl` | Cabecera del BL con fecha por defecto y cliente/naviera. |
| `demurrage.container` | Unidad de cálculo y facturación; puede sobrescribir la fecha de descarga del BL. |
| `demurrage.correction` | Auditoría de reaperturas y correcciones posteriores a facturación. |
| `demurrage.carrier.invoice` / `.line` | Registro de lo que cobró la naviera y comparación con lo calculado. |
| `account.move` | Factura en borrador al cliente, una línea por contenedor. |

### Decisiones de modelo

- **Tarifa y tramos separados:** los tramos son variables (2, 3 o más) y deben conservarse históricamente.
- **Acuerdo por cliente + naviera:** Ferretería tiene +5 solo con Atlántico; Textiles +3 solo con Mar del Sur.
- **BL + contenedores:** un BL puede traer de 1 a 30 contenedores y descargarse en días distintos.
- **`as_of_date`:** permite estimar contenedores abiertos con una fecha de corte determinista y testeable.
- **Snapshots al facturar:** los montos, días, porcentaje y TRM se congelan. Cambiar una tarifa después no altera una factura.
- **`invoiced` / `cancelled`:** banderas que gobiernan el estado calculado y el bloqueo.

---

## 6. Reglas de cálculo

1. **Días afuera** (inclusive):
   `días_afuera = (fecha_devolución - fecha_descarga).days + 1`.
2. **Días libres** = días libres de la tarifa + días extra del acuerdo.
3. **Días de demora** = `max(0, días_afuera - días_libres)`.
4. **Cobro escalonado:** cada día de demora se cobra al precio del tramo en el que cae.
5. **Tarifa aplicable:** la vigente en la fecha de descarga.
6. **Sin tarifa:** se marca `missing_tariff`; no se calcula cero silenciosamente y se bloquea la facturación.
7. **Cobro al cliente** = cobro naviera × `(1 + % administración / 100)`.
8. **Contenedor abierto:** se estima hasta `as_of_date` y se marca `is_estimate`.
9. **Monedas:** tarifas en USD; cliente en COP con TRM de la fecha de factura.
10. **Redondeo:** 2 decimales, `HALF_UP`, con `Decimal`.

Ejemplo del caso 1:

```text
Descarga 2026-03-02, devolución 2026-03-20 → 19 días
Atlántico 40HC: 7 días libres
Demora: 12 días
5 × 60 + 5 × 120 + 2 × 180 = USD 1.260
Cliente: 1.260 × 1.10 = USD 1.386
```

---

## 7. Casos de verificación

| # | Cliente | Naviera | Tipo | Descarga | Devolución | Días afuera | Libres | Demora | Naviera USD | Cliente USD |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Importadora Sol | Atlántico | 40HC | 02/03/2026 | 20/03/2026 | 19 | 7 | 12 | 1.260,00 | 1.386,00 |
| 2 | Ferretería El Tornillo | Atlántico | 20DV | 10/04/2026 | 21/04/2026 | 12 | 12 | 0 | 0,00 | 0,00 |
| 3 | Textiles Andinos | Mar del Sur | 40DV | 28/06/2026 | 15/07/2026 | 18 | 13 | 5 | 375,00 | 393,75 |
| 4 | Frutas del Valle | Atlántico | 40RF | 01/08/2026 | 14/08/2026 | 14 | 4 | 10 | 2.000,00 | 2.200,00 |
| 5 | Importadora Sol | Mar del Sur | 20DV | 05/09/2026 | sin devolver | 16 | 8 | 8 | 410,00 (estimado) | 451,00 (estimado) |
| 6 | Importadora Sol | Atlántico | 20DV | 04/05/2026 | 10/05/2026 | 7 | 7 | 0 | 0,00 | 0,00 |
| 7 | Importadora Sol | Atlántico | 20DV | 04/05/2026 | 11/05/2026 | 8 | 7 | 1 | 35,00 | 38,50 |
| 8 | Importadora Sol | Atlántico | 20DV | 14/09/2026 | 14/09/2026 | 1 | 7 | 0 | 0,00 | 0,00 |
| 9 | Frutas del Valle | Mar del Sur | 40RF | 03/08/2026 | 20/08/2026 | 18 | — | — | **Sin tarifa: bloqueado** | — |

El caso 5 usa fecha de corte **2026-09-20**. El caso 9 no es cero: es `missing_tariff`.

---

## 8. Contradicciones y decisiones

| # | Contradicción / vacío | Decisión | Motivo |
|---|---|---|---|
| 1 | Jorge no cuenta el día de descarga; el contrato 4.2 sí. | Contar ambos días, inclusive. | “Cuando una regla choca con una persona, manda el contrato”. Caso 1: 19, no 18. |
| 2 | Descarga y devolución el mismo día. | 1 día afuera. | Misma cláusula. Caso 8. |
| 3 | ¿Tarifa vieja o nueva si la devolución cruza el cambio? | La vigente en la fecha de descarga. | Regla 5. Caso 3 usa tarifa vieja de Mar del Sur. |
| 4 | Marcela carga por BL, pero un BL puede bajar en dos días. | Fecha del BL por defecto; cada contenedor puede sobrescribirla. | Entrevista + regla 3 + fila 9 del Excel. |
| 5 | Marcela necesita corregir; Jorge no quiere cambios después de facturar. | Bloqueo al facturar; solo Facturación/Gerencia reabre con motivo y auditoría. Operaciones solo solicita. | Resuelve ambos sin ediciones silenciosas. |
| 6 | “Las tarifas solo las tocan Jorge o Patricia”. | Grupo Facturación/Gerencia edita; Operaciones solo lectura. | Permisos por grupo + ACL. |
| 7 | “Naviera + 10 %”. | `cobro_cliente = cobro_naviera × (1 + %/100)`. | Regla 7 y casos: 1.260 × 1,10 = 1.386. |
| 8 | ¿Días extra globales o por naviera? | Acuerdo por cliente + naviera. | Ferretería solo Atlántico; Textiles solo Mar del Sur. |
| 9 | Mar del Sur no tiene 40RF. | `missing_tariff` + bloqueo; no cero. | Regla 6 y caso 9. |
| 10 | Contenedor todavía afuera. | Estimado con `as_of_date` y marca visible. | Regla 8. |
| 11 | TRM: ¿factura, pago o descarga? | TRM de la fecha de factura, desde `res.currency.rate`. | Jorge; sin tasa se bloquea. |
| 12 | “Recobrado” en el reporte. | Significa **facturado al cliente**, no cobrado. | El alcance no incluye cobranza. |

---

## 9. Errores encontrados en la muestra del Excel

Resultado del importador: **6 filas importadas, 4 rechazadas**, y la fila 10 con advertencia.

| Fila | Error | Decisión del sistema |
|---:|---|---|
| 1 | Ninguno. | Importada. |
| 2 | `natu 508163 4`, tipo `20'`, naviera/cliente con variantes. | Normaliza a `NATU5081634`, `20DV`, `Naviera Atlántico`, `Ferretería El Tornillo`. La observación de +5 días ya está en el acuerdo. |
| 3 | `40 dv`; `15-jul` sin año. | Normaliza a `40DV` e infiere 2026 desde la descarga. |
| 4 | Observación `reefer`. | Tipo `40RF`; observación como nota. |
| 5 | Duplicado exacto de la fila 4. | Rechazada por duplicado/solapamiento. |
| 6 | `MSLU6135877` con dígito de control inválido (se esperaba 6). | Rechazada; sugiere `MSLU6135876`; no autocorrige. |
| 7 | Devolución 18/09 anterior a descarga 20/09. | Rechazada. |
| 8 | Cliente vacío; devolución vacía; “DEVUELTO el viernes”. | Rechazada por cliente; no se infiere la fecha. |
| 9 | “Bajó al otro día”. | Importada con fecha propia 03/03, dentro del BL 0311. |
| 10 | Mar del Sur 40RF sin tarifa. | Importada con advertencia; `missing_tariff`; facturación bloqueada. |

---

## 10. Estados, bloqueo y permisos

```text
Borrador --descarga--> Afuera --devolución--> Devuelto --facturar--> Facturado
   |                     |                       |                      |
   +----cancelar---------+-----------------------+                      +--reabrir (Facturación + motivo)--> Devuelto
```

- `state` se calcula desde fechas y banderas `invoiced` / `cancelled`.
- Al facturar se guardan snapshots.
- Modificar fechas o identificación de un contenedor facturado lanza error.
- La reapertura exige motivo, crea `demurrage.correction`, deja mensaje y marca `invoice_needs_review`.
- Operaciones puede **solicitar** corrección; no reabrir.

| Acción | Operaciones | Facturación | Gerencia |
|---|---|---|---|
| BL / contenedores | Crear/editar | Crear/editar | Crear/editar/borrar |
| Fechas antes de facturar | Sí | Sí | Sí |
| Tarifas y acuerdos | Solo lectura | CRUD | CRUD |
| EIR | Sí | Sí | Sí |
| Facturar | No | Sí | Sí |
| Reabrir facturado | No | Sí, con motivo | Sí, con motivo |
| Facturas naviera | Lectura | CRUD | CRUD |
| Ajustes | No | Sí | Sí |

---

## 11. TRM y moneda

- Las tarifas están en USD.
- Al cliente se le factura en COP.
- La TRM se toma de las tasas de Odoo (`res.currency.rate`) para la **fecha de la factura**.
- Para un contenedor estimado se usa `as_of_date` y se marca como estimado.
- Si falta la tasa, el sistema marca `missing_exchange_rate`, deja COP en cero y bloquea la facturación. Nunca asume 1.
- El snapshot de TRM y COP se congela al facturar.

Ejemplo con TRM 4.000:

```text
Caso 1: USD 1.386 × 4.000 = COP 5.544.000
```

---

## 12. Deseables y extras implementados

| Requisito | Estado | Dónde |
|---|---|---|
| Cron diario de actividades | Hecho | `_cron_daily`, `data/ir_cron.xml` |
| Importador Excel/CSV | Hecho | `demurrage.import.wizard` |
| Factura naviera y diferencia | Hecho | `demurrage.carrier.invoice` |
| Conversión COP con Odoo | Hecho | `customer_charge_cop`, `_get_exchange_rate` |
| TRM justificada | Hecho | README + pruebas |
| Factura en borrador | Hecho | `demurrage.invoice.wizard` |
| PDF de liquidación | Hecho | Reporte QWeb |
| Reporte mensual | Hecho | `demurrage.monthly.report.wizard` |

---

## 13. TDD y commits

Cada cambio se trabajó con el ciclo:

1. Prueba que falla.
2. Implementación mínima.
3. Suite completa.
4. Commit de prueba y commit de implementación.

El repositorio tiene **50 commits pequeños** (más los de documentación y entrega). Ejemplos:

```text
prueba(iso): especifica validación de números de contenedor
feat(iso): agrega normalización y validación ISO 6346
prueba(calculo): especifica días inclusivos y cálculo por tramos
feat(calculo): agrega calculadora pura de demoras
prueba(estados): especifica bloqueo y reapertura
feat(estados): agrega bloqueo, snapshots y reapertura auditada
```

El detalle de ciclos, comandos y commits está en [`docs/tdd.md`](docs/tdd.md).

### Pruebas principales

- `test_iso6346.py`: ISO 6346 y normalización.
- `test_calculator.py`: días inclusivos, tramos, redondeo.
- `test_acceptance_cases.py`: casos 1–5.
- `test_extended_cases.py`: casos 6–9, vencimiento y COP.
- `test_container_constraints.py`: fechas y solapamiento.
- `test_states.py` y `test_state_wizards.py`: bloqueo y reapertura.
- `test_security.py`: grupos y ACL.
- `test_import.py`: 6/4 y motivos.
- `test_cron.py`: actividades e idempotencia.
- `test_carrier_invoice.py`: sobrecobro.
- `test_currency.py` / casos extendidos: TRM.
- `test_invoice.py`: factura en borrador.
- `test_reports.py`: liquidación y reporte mensual.
- `test_views.py`: vistas, filtros y menús.

---

## 14. Preguntas para el cliente antes de producción

1. ¿El porcentaje de administración aplica solo a la demora o a otros conceptos?
2. ¿Se factura por contenedor o consolidado por BL?
3. ¿La TRM es la de la fecha de factura, de pago o de descarga?
4. ¿La naviera puede facturar en una moneda distinta a USD?
5. ¿Cómo se corrige una factura ya emitida: nota crédito, reapertura o ajuste?
6. ¿Los días extra son por cliente + naviera, por contrato o por BL?
7. ¿Qué fecha se usa si el EIR se emite al día siguiente de la devolución?
8. ¿Qué ocurre si no hay EIR?
9. ¿Cómo se trata un contenedor perdido o que nunca se devuelve?
10. ¿Un BL puede tener clientes o navieras distintas?
11. ¿“Recobrado” significa facturado o efectivamente cobrado?
12. ¿Quién recibe las actividades: Marcela, el vendedor o ambos?
13. ¿Se requiere aprobación adicional de tarifas?
14. ¿Qué tolerancia se acepta contra la factura de la naviera?

---

## 15. Limitaciones y lo que no se hizo

- No hay conexión con navieras ni con la DIAN; está fuera de alcance.
- No hay facturación electrónica.
- No se implementa conciliación de pagos: “recobrado” = facturado.
- Un BL se asume con un solo cliente y una sola naviera.
- Un contenedor tiene una sola fecha de devolución; no se modelan devoluciones parciales.
- Los festivos cuentan como días calendario, según el contrato.
- El PDF requiere `wkhtmltopdf`; las pruebas validan el HTML del reporte.
- La validación de solapamiento es a nivel de aplicación; no se hizo una prueba de concurrencia masiva.
- No hay pruebas E2E de navegador; hay pruebas de vistas, filtros y una demo manual.
- No se implementó una pantalla de conciliación bancaria de la TRM; se usan las tasas de Odoo.

---

## 16. Guion de demostración (30 minutos)

1. **2 min** — problema y alcance.
2. **4 min** — modelo: naviera → tarifa → tramos; cliente → acuerdo; BL → contenedores.
3. **5 min** — caso 1: 19 días, 7 libres, 12 demora, 5×60 + 5×120 + 2×180 = 1.260; cliente 1.386.
4. **3 min** — caso 3: tarifa vieja por fecha de descarga, +3 días y 5 %.
5. **3 min** — caso 9: 40RF Mar del Sur sin tarifa; no cero, bloqueo.
6. **4 min** — estados: facturado bloquea; reapertura con motivo; auditoría.
7. **4 min** — importador: 6/4; fila 6 ISO, fila 7 fecha, fila 5 duplicado, fila 8 cliente.
8. **3 min** — cron y factura naviera: actividad diaria y sobrecobro.
9. **2 min** — TRM/COP y factura en borrador.
10. **2 min** — cambio en vivo: agregar un tramo o cambiar un porcentaje y correr una prueba.

---

## 17. Estructura del repositorio

```text
container_demurrage/
├── models/          # catálogos, BL, contenedor, conciliación, importación
├── utils/           # ISO 6346, fechas, calculadora pura, parsing
├── wizards/         # importación, estados, factura, reporte mensual
├── views/           # pantallas, filtros, menús
├── report/          # QWeb de liquidación y reporte mensual
├── security/        # grupos, ACL
├── data/            # cron, producto
├── demo/            # datos de demostración
└── tests/           # suite automatizada
```

---

## 18. Autor

Samuel — prueba técnica para Desarrollador Odoo Junior.
