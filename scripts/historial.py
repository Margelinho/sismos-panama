"""
Descarga el historial de sismos (por defecto, los últimos 12 meses) y crea data/sismos.csv.
Se corre UNA sola vez, desde la PC, antes de activar el servidor.

Uso:
    python scripts/historial.py          -> últimos 12 meses
    python scripts/historial.py 24       -> últimos 24 meses
"""
import sys
from datetime import datetime, timedelta, timezone

from comun import consultar_emsc, guardar_csv, leer_csv

meses = int(sys.argv[1]) if len(sys.argv) > 1 else 12
fin = datetime.now(timezone.utc).replace(tzinfo=None)
inicio = fin - timedelta(days=30 * meses)

print(f"Descargando sismos desde {inicio:%Y-%m-%d} hasta {fin:%Y-%m-%d}, semana por semana...\n")

existentes = leer_csv()
total_nuevos = 0
desde = inicio
while desde < fin:
    hasta = min(desde + timedelta(days=7), fin)
    filas = consultar_emsc(desde, hasta)
    nuevos, total = guardar_csv(existentes, filas)   # guarda en cada paso por si se corta
    total_nuevos += nuevos
    print(f"  {desde:%Y-%m-%d} a {hasta:%Y-%m-%d}: {len(filas):4d} sismos")
    desde = hasta

print(f"\nListo. Sismos nuevos: {total_nuevos}. Total en data/sismos.csv: {total}")
