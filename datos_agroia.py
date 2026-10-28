"""
Acceso a los datos de AgroIA (lo usan el bot de Telegram y el puente de Sinric Pro).

Fuente principal: la API en Railway (base Neon).   Respaldo: el canal publico de ThingSpeak.

Esta version es liviana a proposito:
  * NO descarga /muestras/list completo (crece sin parar): lee solo las primeras filas, que vienen
    de la muestra mas reciente a la mas antigua.
  * Los promedios, maximos y demas los calculan los endpoints /menu/* en la base de datos.
  * Guarda el resultado 20 segundos, para que varias preguntas seguidas no repitan las descargas.
"""
import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger("agroia.datos")

# ---------------------------------------------------------------------------
# Configuracion (todas las variables son opcionales)
# ---------------------------------------------------------------------------
API_DEFECTO = "https://agroiabackend.up.railway.app"
# USAR_API=0 -> no consulta la API de AgroIA: usa solo ThingSpeak. Es para el puente de Sinric, que consulta cada 60 s:
# si llamara a la API, Railway (Serverless) nunca podria dormirla.
USAR_API = os.environ.get("USAR_API", "1").strip().lower() not in ("0", "no", "false", "off")
API_URL = (os.environ.get("API_URL") or API_DEFECTO).strip().rstrip("/")
if "onrender.com" in API_URL:                      # Render ya no se usa: toda la API esta en Railway
    log.warning("API_URL apuntaba a Render (%s). Se usa Railway: %s", API_URL, API_DEFECTO)
    API_URL = API_DEFECTO

THINGSPEAK_BASE = os.environ.get("THINGSPEAK_BASE", "https://api.thingspeak.com").rstrip("/")
THINGSPEAK_CANAL = os.environ.get("THINGSPEAK_CANAL", "3540815")
MUESTRAS_EN_UTC = os.environ.get("MUESTRAS_EN_UTC", "1") != "0"   # el backend guarda datetime.now() del servidor (UTC)
TTL_SEGUNDOS = int(os.environ.get("DATOS_TTL_SEGUNDOS", "20"))
MINUTOS_EN_LINEA = 5
OFFSET_COLOMBIA = timedelta(hours=-5)

# Rangos "normales" y limites: los mismos de frontend/js/config.js (RANGOS)
VARIABLES = {
    "temperatura":   {"nombre": "Temperatura del aire", "corto": "temperatura", "unidad": "°C", "dec": 1,
                      "normal": (15, 30), "limite": (10, 35), "campo_ts": 1},
    "humedad_aire":  {"nombre": "Humedad del aire", "corto": "humedad del aire", "unidad": "%", "dec": 0,
                      "normal": (40, 80), "limite": (30, 90), "campo_ts": 2},
    "humedad_suelo": {"nombre": "Humedad del suelo", "corto": "humedad del suelo", "unidad": "%", "dec": 0,
                      "normal": (30, 60), "limite": (20, 75), "campo_ts": 3},
    "tds":           {"nombre": "TDS", "corto": "TDS", "unidad": "ppm", "dec": 0,
                      "normal": (0, 1000), "limite": (0, 1500), "campo_ts": 4},
}
ORDEN = ["temperatura", "humedad_aire", "humedad_suelo", "tds"]       # el pH ya no se mide: el cuarto sensor es el TDS


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def sin_acentos(t):
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("ascii")


def clave_de_nombre(nombre):
    """Reconoce la variable por el NOMBRE del parametro en la base (no por un numero fijo)."""
    n = sin_acentos(nombre).lower()
    if re.search(r"\btds\b|solidos|conductividad|salinidad", n):       # primero: "TDS del suelo" no es la humedad del suelo
        return "tds"
    if "humedad" in n and any(k in n for k in ("aire", "ambient", "relativ")):
        return "humedad_aire"
    if "humedad" in n or "moisture" in n:
        return "humedad_suelo"
    if "temp" in n:
        return "temperatura"
    return None                                                          # (pH y otros parametros viejos se ignoran)


def ahora_colombia():
    return (datetime.now(timezone.utc) + OFFSET_COLOMBIA).replace(tzinfo=None)


def _a_hora_colombia(ts_txt):
    """Texto ISO de la base -> datetime en hora de Colombia (sin zona)."""
    t = str(ts_txt).strip().replace(" ", "T")
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    d = datetime.fromisoformat(t)
    if d.tzinfo is not None:
        return d.astimezone(timezone(OFFSET_COLOMBIA)).replace(tzinfo=None)
    return d + OFFSET_COLOMBIA if MUESTRAS_EN_UTC else d


def _get_json(url, timeout=15, reintentos=1):
    ultimo = None
    for _ in range(reintentos + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:                       # noqa: BLE001
            ultimo = e
            time.sleep(1)
    raise ultimo


def _api(ruta, timeout=15):
    return _get_json(f"{API_URL}{ruta}", timeout=timeout)


# ---------------------------------------------------------------------------
# /muestras/list sin bajarlo completo
# ---------------------------------------------------------------------------
def primeras_muestras(n=150):
    """Lee solo las primeras n filas del arreglo JSON de /muestras/list (de la mas reciente a la mas antigua).
    Si el servidor las devolviera en otro orden, baja la lista completa y la ordena."""
    dec = json.JSONDecoder()
    filas, buf, pos, iniciado = [], "", 0, False
    with requests.get(f"{API_URL}/muestras/list", stream=True, timeout=(10, 25)) as r:
        r.raise_for_status()
        r.encoding = "utf-8"
        for trozo in r.iter_content(chunk_size=8192, decode_unicode=True):
            buf += trozo
            if not iniciado:
                i = buf.find("[")
                if i < 0:
                    continue
                iniciado, pos = True, i + 1
            while True:
                while pos < len(buf) and buf[pos] in " \r\n\t,":
                    pos += 1
                if pos >= len(buf) or buf[pos] == "]":
                    break
                try:
                    obj, fin = dec.raw_decode(buf, pos)
                except ValueError:
                    break                            # el objeto todavia no llego completo
                filas.append(obj)
                pos = fin
                if len(filas) >= n:
                    return _verificar_orden(filas, n)
            buf, pos = buf[pos:], 0
    return _verificar_orden(filas, n)


def _verificar_orden(filas, n):
    f0 = [x.get("Muestra_FechaHora") or "" for x in filas]
    if len(f0) >= 2 and f0[0] < f0[-1]:              # venian de la mas antigua a la mas reciente
        todas = _api("/muestras/list", timeout=30)
        todas.sort(key=lambda m: m.get("Muestra_FechaHora") or "", reverse=True)
        return todas[:n]
    return filas


# ---------------------------------------------------------------------------
# Datos desde la API
# ---------------------------------------------------------------------------
_cache_params = {"t": 0, "ids": {}, "lista": []}


def _parametros():
    if time.time() - _cache_params["t"] < 600 and _cache_params["ids"]:
        return _cache_params["ids"], _cache_params["lista"]
    lista = _api("/parametros/list")
    ids = {}
    for p in lista:
        c = clave_de_nombre(p.get("Parametro_Nombre", ""))
        if c:
            ids.setdefault(p["Parametro_Id"], c)
    _cache_params.update(t=time.time(), ids=ids, lista=lista)
    return ids, lista


def datos_api(n=150):
    """-> (ultimos {clave: {valor, fecha}}, recientes {clave: [valores]}, parametros_db)"""
    ids, lista = _parametros()
    filas = primeras_muestras(n)
    ultimos, recientes = {}, {k: [] for k in ORDEN}
    for m in filas:                                  # ya vienen de la mas reciente a la mas antigua
        c = ids.get(m.get("Parametro_Id"))
        if not c:
            continue
        try:
            v = float(m["Muestra_Valor"])
        except (TypeError, ValueError, KeyError):
            continue
        recientes[c].append(v)
        if c not in ultimos:
            ultimos[c] = {"valor": v, "fecha": _a_hora_colombia(m["Muestra_FechaHora"]), "fuente": "api"}
    return ultimos, {k: v for k, v in recientes.items() if v}, lista


def _pares(detalle):
    """'Humedad del aire: 62.7; Temperatura: 32.8'  ->  {clave: 62.7, ...}"""
    out = {}
    for parte in str(detalle).split(";"):
        if ":" not in parte:
            continue
        nombre, valor = parte.rsplit(":", 1)
        c = clave_de_nombre(nombre)
        try:
            if c:
                out[c] = float(valor.strip().rstrip("%"))
        except ValueError:
            pass
    return out


def _menu(ruta):
    try:
        j = _api(f"/menu/{ruta}", timeout=15)
        return j if isinstance(j, dict) else None
    except Exception as e:                           # noqa: BLE001
        log.warning("No se pudo leer /menu/%s: %s", ruta, e)
        return None


def estadisticas_api(solo_prom=False):
    """Promedios, maximos y demas, que ya calcula la base de datos (endpoints /menu/*)."""
    est = {"prom24": {}, "maxmin": {}, "dias_bajo": None, "por_dia": None, "por_hora": None}
    j = _menu("promedio-24h")
    if j and j.get("linea2") != "Sin datos":
        est["prom24"] = _pares(j.get("detalle", ""))
    if solo_prom:                                    # el puente de Sinric solo necesita el promedio de 24 h
        return est
    j = _menu("max-min-hoy")
    if j and j.get("linea2") != "Sin datos":
        for parte in j.get("detalle", "").split(";"):
            m = re.match(r"\s*(.+?):\s*max=([-\d.]+)\s+min=([-\d.]+)", parte)
            if m and clave_de_nombre(m.group(1)):
                est["maxmin"][clave_de_nombre(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    j = _menu("dias-bajo-umbral")
    if j:
        dias = re.findall(r"(\d{4}-\d{2}-\d{2}):\s*([-\d.]+)%", j.get("detalle", ""))
        est["dias_bajo"] = [(d, float(v)) for d, v in dias]
    j = _menu("muestras-por-dia")
    if j and j.get("linea2") != "Sin datos":
        est["por_dia"] = [(d, int(n)) for d, n in re.findall(r"(\d{4}-\d{2}-\d{2}):\s*(\d+)", j.get("detalle", ""))]
    j = _menu("promedio-por-hora")
    if j and j.get("linea2") != "Sin datos":
        est["por_hora"] = [(h, float(v)) for h, v in re.findall(r"(\d{2}:00):\s*([-\d.]+)%", j.get("detalle", ""))]
    return est


# ---------------------------------------------------------------------------
# Respaldo: ThingSpeak
# ---------------------------------------------------------------------------
def thingspeak_ultimo():
    j = _get_json(f"{THINGSPEAK_BASE}/channels/{THINGSPEAK_CANAL}/feeds/last.json", timeout=12, reintentos=0)
    if not isinstance(j, dict) or "created_at" not in j:
        return {}
    fecha = _a_hora_colombia(j["created_at"])
    out = {}
    for c in ORDEN:
        try:
            out[c] = {"valor": float(j[f"field{VARIABLES[c]['campo_ts']}"]), "fecha": fecha, "fuente": "thingspeak"}
        except (TypeError, ValueError, KeyError):
            pass
    return out


def thingspeak_series(n=40):
    """Solo ThingSpeak -> (recientes {clave: [valores, del mas reciente al mas antiguo]}, prom24 {clave: promedio de las ultimas 24 h})"""
    base = f"{THINGSPEAK_BASE}/channels/{THINGSPEAK_CANAL}/feeds.json"

    def col(feeds, c, orden_inverso):
        campo, out = f"field{VARIABLES[c]['campo_ts']}", []
        for f in (reversed(feeds) if orden_inverso else feeds):
            try:
                out.append(float(f[campo]))
            except (TypeError, ValueError, KeyError):
                pass
        return out

    rec, prom = {}, {}
    j = _get_json(f"{base}?results={n}", timeout=15, reintentos=0)
    feeds = j.get("feeds", []) if isinstance(j, dict) else []
    for c in ORDEN:
        v = col(feeds, c, True)
        if v:
            rec[c] = v
    j = _get_json(f"{base}?days=1&average=60", timeout=15, reintentos=0)           # 24 promedios de una hora
    feeds = j.get("feeds", []) if isinstance(j, dict) else []
    for c in ORDEN:
        v = col(feeds, c, False)
        if v:
            prom[c] = sum(v) / len(v)
    return rec, prom


# ---------------------------------------------------------------------------
# Orden al ESP32 (LED): POST /esp32/comando  { "accion": "encender_led" | "apagar_led" }
# ---------------------------------------------------------------------------
COMANDO_INTENTOS = 6          # el backend puede estar dormido (Railway Serverless): el primer intento puede dar 502 o tardar
COMANDO_ESPERA = 5            # segundos entre intentos
COMANDO_TIMEOUT = 20          # segundos por intento


def enviar_comando(accion):
    """-> (ok, respuesta). El ESP32 la recoge (una sola vez) con GET /esp32/comando.
    Si el servidor estaba dormido (502/503/504 o sin respuesta) espera y reintenta hasta COMANDO_INTENTOS veces."""
    ultimo = {"detalle": "no pude comunicarme con la API"}
    for i in range(COMANDO_INTENTOS):
        try:
            r = requests.post(f"{API_URL}/esp32/comando", json={"accion": accion}, timeout=COMANDO_TIMEOUT)
            if r.status_code in (502, 503, 504):
                ultimo = {"detalle": "el servidor de AgroIA estaba despertando y no alcanzó a responder"}
            else:
                try:
                    d = r.json()
                except ValueError:
                    d = {}
                return (r.ok and d.get("ok") is not False), d
        except Exception as e:                       # noqa: BLE001
            log.warning("No se pudo enviar la orden al ESP32 (intento %s): %s", i + 1, e)
            ultimo = {"detalle": "no pude comunicarme con la API"}
        if i < COMANDO_INTENTOS - 1:
            time.sleep(COMANDO_ESPERA)
    return False, ultimo


# ---------------------------------------------------------------------------
# Foto de suelo -> YOLO (POST /vision/analizar)
# ---------------------------------------------------------------------------
def analizar_foto(contenido, nombre="foto.jpg", tipo="image/jpeg"):
    r = requests.post(f"{API_URL}/vision/analizar", files={"archivo": (nombre, contenido, tipo)}, timeout=90)
    r.raise_for_status()
    return r.json().get("detecciones", [])


# ---------------------------------------------------------------------------
# Resumen completo (con memoria de 20 s)
# ---------------------------------------------------------------------------
_cache = {"t": 0, "snap": None, "basico": None}


def snapshot(forzar=False, basico=False):
    """basico=True: solo lo imprescindible (ultimos valores + promedio 24 h), para el puente de Sinric."""
    if not forzar and _cache["snap"] and _cache["basico"] == basico and time.time() - _cache["t"] < TTL_SEGUNDOS:
        return _cache["snap"]
    s = {"fuente": None, "ultimos": {}, "recientes": {}, "prom24": {}, "maxmin": {}, "dias_bajo": None,
         "por_dia": None, "por_hora": None, "parametros_db": [], "avisos": [], "generado": ahora_colombia()}
    if not USAR_API:                                 # solo ThingSpeak (puente de Sinric): no despierta la API de Railway
        try:
            s["ultimos"] = thingspeak_ultimo()
            s["recientes"], s["prom24"] = thingspeak_series()
            if s["ultimos"]:
                s["fuente"] = "ThingSpeak (canal %s)" % THINGSPEAK_CANAL
        except Exception as e:                       # noqa: BLE001
            log.warning("ThingSpeak no disponible: %s", e)
            s["avisos"].append("ThingSpeak no respondio")
    else:
        try:
            s["ultimos"], s["recientes"], s["parametros_db"] = datos_api()
            if s["ultimos"]:
                s["fuente"] = "API de AgroIA (base de datos)"
            s.update(estadisticas_api(solo_prom=basico))
        except Exception as e:                       # noqa: BLE001
            log.warning("API no disponible: %s", e)
            s["avisos"].append("La API no respondio")
    faltan = [c for c in ORDEN if c not in s["ultimos"]]
    if faltan:                                       # completa con ThingSpeak lo que falte (por ejemplo el TDS)
        try:
            ts = thingspeak_ultimo()
            for c in faltan:
                if c in ts:
                    s["ultimos"][c] = ts[c]
            if ts and not s["fuente"]:
                s["fuente"] = "ThingSpeak (canal %s)" % THINGSPEAK_CANAL
            elif ts and any(c in ts for c in faltan):
                s["fuente"] += " + ThingSpeak"
        except Exception as e:                       # noqa: BLE001
            log.warning("ThingSpeak no disponible: %s", e)
    _cache.update(t=time.time(), snap=s, basico=basico)
    return s


def minutos_desde(fecha):
    return max(0, int((ahora_colombia() - fecha).total_seconds() // 60))
