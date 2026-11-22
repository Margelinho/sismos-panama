"""
Lo ejecuta GitHub Actions cada 4 horas.
Pide los sismos de las últimas 8 horas (el doble del intervalo, para no perder ninguno
si una ejecución se retrasa) y agrega solo los nuevos a data/sismos.csv.

Uso manual (opcional):
    python scripts/recolectar.py          -> últimas 8 horas
    python scripts/recolectar.py 48       -> últimas 48 horas
"""
import sys
from datetime import datetime, timedelta, timezone

from comun import consultar_emsc, guardar_csv, leer_csv

horas = int(sys.argv[1]) if len(sys.argv) > 1 else 8
fin = datetime.now(timezone.utc).replace(tzinfo=None)
inicio = fin - timedelta(hours=horas)

filas = consultar_emsc(inicio, fin)
nuevos, total = guardar_csv(leer_csv(), filas)

print(f"Ventana: {inicio:%Y-%m-%d %H:%M} a {fin:%Y-%m-%d %H:%M} UTC")
print(f"Sismos en la ventana: {len(filas)} | nuevos: {nuevos} | total en el CSV: {total}")
