# Sismos en Panamá – Proyecto de Probabilidad Aplicada a TIC

Universidad Tecnológica de Panamá · Grupo 1SG-131 · Prof. Alberto Quintero

Integrantes: Margel Pérez, Diego Alvarez, Alexis Gonzalez, Angelica Montenegro

## Qué hace este repositorio

1. **Recolecta** automáticamente, cada 4 horas, los sismos de Panamá y sus costas desde la API pública del
   [EMSC](https://www.seismicportal.eu), que difunde los datos de la red del Instituto de Geociencias (IGC-UP).
2. **Guarda** todo en `data/sismos.csv`, sin duplicados.
3. **Analiza** los datos con las distribuciones del curso (binomial, hipergeométrica, Poisson, normal, Chebyshev).
4. **Publica** un tablero web en GitHub Pages.

## Estructura

| Ruta | Qué es |
| --- | --- |
| `.github/workflows/recolectar.yml` | El "servidor": GitHub Actions corre la recolección cada 4 horas |
| `scripts/comun.py` | Consulta a la API, clasificación por región y magnitud, manejo del CSV |
| `scripts/historial.py` | Descarga inicial de 12 meses (se corre una sola vez) |
| `scripts/recolectar.py` | Descarga las últimas 8 horas (lo corre Actions) |
| `data/sismos.csv` | La base de datos |
| `analisis/` | Scripts de análisis estadístico |
| `docs/` | Tablero web (GitHub Pages) |

## Columnas de `data/sismos.csv`

| Columna | Ejemplo | Tipo de variable |
| --- | --- | --- |
| event_id | 20261119_0000246 | Identificador |
| fecha_hora_utc | 2026-11-19 18:52:28 | Cuantitativa, intervalo |
| fecha_local / hora_local | 2026-11-19 / 13:52:28 | Hora de Panamá (UTC-5) |
| latitud / longitud | 7.5967 / -80.6593 | Cuantitativa |
| profundidad_km | 8.0 | Cuantitativa continua, razón |
| magnitud | 4.5 | Cuantitativa continua, intervalo |
| region | Azuero-Soná | Cualitativa nominal |
| pais | Panamá, Frontera Panamá-Costa Rica, Costa Rica, Colombia, Mar afuera | Cualitativa nominal |
| categoria | Ligero (4.0-4.9) | Cualitativa ordinal |
| superficial | Sí (< 70 km) | Cualitativa dicotómica |
| autor | IGC, UNA, NEIC, EMSC | Red que reportó el sismo (IGC = Panamá, UNA = Costa Rica, NEIC = EE. UU.) |

## Uso local

```
python -m pip install requests pandas
python scripts/historial.py      # una sola vez
python scripts/recolectar.py     # prueba de la recolección
```
