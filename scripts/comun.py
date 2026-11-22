"""
Funciones compartidas por historial.py y recolectar.py

- consultar_emsc(): descarga sismos de la API del EMSC para un rango de fechas
- clasificar():     asigna región, categoría de magnitud y si es superficial
- leer_csv() / guardar_csv(): manejan data/sismos.csv sin duplicados
"""
import csv
import time
from datetime import timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
URL_EMSC = "https://www.seismicportal.eu/fdsnws/event/1/query"

# Rectángulo que cubre Panamá y sus costas
ZONA = {"minlat": 5, "maxlat": 10, "minlon": -84, "maxlon": -77}

LIMITE = 1000          # máximo de sismos que pedimos por consulta
CSV = Path(__file__).resolve().parent.parent / "data" / "sismos.csv"
HEADERS = {"User-Agent": "UTP-Proyecto-Probabilidad/1.0 (sismos-panama)"}

COLUMNAS = [
    "event_id", "fecha_hora_utc", "fecha_local", "hora_local",
    "latitud", "longitud", "profundidad_km", "magnitud", "tipo_magnitud",
    "region", "pais", "categoria", "superficial", "autor", "lugar",
]


# ---------------------------------------------------------------------------
# Clasificación (ajustar los límites cuando veamos el mapa de los datos)
# ---------------------------------------------------------------------------
def region(lat, lon):
    """Asigna una región aproximada según latitud y longitud."""
    if lat < 6.5:
        return "Pacífico sur"
    if lon < -81.6:
        return "Chiriquí y frontera"
    if lon <= -79.8 and lat <= 8.2:
        return "Azuero-Soná"
    if lon > -78.8:
        return "Este y Darién"
    return "Centro y Caribe"


def pais(lugar):
    """Agrupa el texto de 'lugar' que reporta el EMSC en categorías simples."""
    t = (lugar or "").upper()
    if "PANAMA" in t and "COSTA RICA" in t:
        return "Frontera Panamá-Costa Rica"
    if "PANAMA" in t and "COLOMBIA" in t:
        return "Frontera Panamá-Colombia"
    if "PANAMA" in t:
        return "Panamá"
    if "COSTA RICA" in t:
        return "Costa Rica"
    if "COLOMBIA" in t:
        return "Colombia"
    return "Mar afuera"


def categoria(mag):
    if mag < 3.0:
        return "Menor (<3.0)"
    if mag < 4.0:
        return "Leve (3.0-3.9)"
    if mag < 5.0:
        return "Ligero (4.0-4.9)"
    return "Moderado o mayor (>=5.0)"


# ---------------------------------------------------------------------------
# Consulta a la API del EMSC
# ---------------------------------------------------------------------------
def _pedir(inicio, fin):
    """Una sola consulta. Devuelve la lista de filas (dict) del formato texto del EMSC."""
    params = {
        "format": "text",
        "start": inicio.strftime("%Y-%m-%dT%H:%M:%S"),
        "end": fin.strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": LIMITE,
        "orderby": "time-asc",
        **ZONA,
    }
    for intento in range(3):
        r = requests.get(URL_EMSC, params=params, headers=HEADERS, timeout=60)
        if r.status_code == 204:          # 204 = no hubo sismos en ese rango
            return []
        if r.status_code == 200:
            return parsear_texto(r.text)
        print(f"  Aviso: código {r.status_code}, reintentando ({intento + 1}/3)...")
        time.sleep(5 * (intento + 1))
    r.raise_for_status()
    return []


def parsear_texto(texto):
    """Convierte el formato texto del EMSC (columnas separadas por |) en filas limpias."""
    filas = []
    for linea in texto.splitlines():
        if not linea.strip() or linea.startswith("#"):
            continue
        p = linea.split("|")
        if len(p) < 13:
            continue
        try:
            filas.append(armar_fila(
                event_id=p[0], tiempo=p[1], lat=float(p[2]), lon=float(p[3]),
                prof=float(p[4]), autor=p[5], tipo_mag=p[9], mag=float(p[10]), lugar=p[12],
            ))
        except ValueError:
            continue  # fila con datos incompletos: se ignora
    return filas


def consultar_emsc(inicio, fin):
    """Descarga todos los sismos entre inicio y fin (datetime en UTC).
    Si una consulta llega al límite, divide el rango en dos y vuelve a pedir."""
    filas = _pedir(inicio, fin)
    if len(filas) >= LIMITE and (fin - inicio) > timedelta(hours=1):
        medio = inicio + (fin - inicio) / 2
        return consultar_emsc(inicio, medio) + consultar_emsc(medio, fin)
    return filas


# ---------------------------------------------------------------------------
# Armar filas y manejar el CSV
# ---------------------------------------------------------------------------
def armar_fila(event_id, tiempo, lat, lon, prof, autor, tipo_mag, mag, lugar):
    from datetime import datetime
    t_utc = datetime.strptime(tiempo[:19], "%Y-%m-%dT%H:%M:%S")
    t_local = t_utc - timedelta(hours=5)          # Panamá = UTC-5 todo el año
    return {
        "event_id": event_id.strip(),
        "fecha_hora_utc": t_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_local": t_local.strftime("%Y-%m-%d"),
        "hora_local": t_local.strftime("%H:%M:%S"),
        "latitud": round(lat, 4),
        "longitud": round(lon, 4),
        "profundidad_km": round(prof, 1),
        "magnitud": round(mag, 1),
        "tipo_magnitud": tipo_mag.strip(),
        "region": region(lat, lon),
        "pais": pais(lugar),
        "categoria": categoria(mag),
        "superficial": "Sí" if prof < 70 else "No",
        "autor": autor.strip(),
        "lugar": lugar.strip(),
    }


def leer_csv():
    """Devuelve un dict {event_id: fila} con lo que ya está guardado."""
    if not CSV.exists():
        return {}
    with open(CSV, newline="", encoding="utf-8-sig") as f:
        return {fila["event_id"]: fila for fila in csv.DictReader(f)}


def guardar_csv(existentes, nuevas):
    """Une lo guardado con lo nuevo (sin duplicados), ordena por fecha y escribe el CSV.
    Si un sismo ya existía, se reemplaza: así se recogen correcciones de magnitud."""
    nuevos_ids = 0
    for fila in nuevas:
        if fila["event_id"] not in existentes:
            nuevos_ids += 1
        existentes[fila["event_id"]] = fila
    for fila in existentes.values():          # filas antiguas sin la columna 'pais'
        if not fila.get("pais"):
            fila["pais"] = pais(fila.get("lugar", ""))
    filas = sorted(existentes.values(), key=lambda f: f["fecha_hora_utc"])
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    return nuevos_ids, len(filas)
