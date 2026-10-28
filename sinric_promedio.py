"""
Puente: API de AgroIA (Railway / base Neon)  ->  Sinric Pro  ->  Alexa y app de Sinric Pro
No usa el ESP32 para nada. Cada INTERVALO_SEGUNDOS (60 por defecto):

  1. Lee los datos de la API (con respaldo en ThingSpeak), YA FILTRADOS POR VARIABLE.
  2. Los empuja a Sinric Pro. Cada dispositivo es un "Temperature Sensor" y lleva temperatura Y humedad:

       "AgroIA Ambiente"  ->  temperatura del aire (ultima lectura)  +  humedad del aire (ultima lectura)
       "AgroIA Promedio"  ->  temperatura promedio 24 h              +  humedad del aire promedio 24 h
       "AgroIA Suelo"     ->  humedad del SUELO (ultima lectura)  [opcional; la temperatura que lleva es la del aire]

  3. Si la humedad del suelo baja de 30 % (seco) o pasa de 75 % (encharcado), manda una notificacion push
     a la app de Sinric Pro (una vez por cambio de estado, o cada 3 horas si sigue igual).

Variables de entorno (Railway):
  SINRIC_APP_KEY, SINRIC_APP_SECRET, SINRIC_DEVICE_AMBIENTE, SINRIC_DEVICE_PROMEDIO   obligatorias
  SINRIC_DEVICE_SUELO      opcional (ID de un 3.er dispositivo "AgroIA Suelo", tipo Temperature Sensor)
  API_URL                  opcional (por defecto https://agroiabackend.up.railway.app)
  INTERVALO_SEGUNDOS       opcional (por defecto 60)
"""
import asyncio
import os
import statistics
import time

from sinricpro import SinricPro, SinricProConfig, SinricProTemperatureSensor

import datos_agroia as D

APP_KEY = os.environ.get("SINRIC_APP_KEY")
APP_SECRET = os.environ.get("SINRIC_APP_SECRET")
DISPOSITIVOS = {
    "ambiente": os.environ.get("SINRIC_DEVICE_AMBIENTE"),
    "promedio": os.environ.get("SINRIC_DEVICE_PROMEDIO"),
    "suelo": os.environ.get("SINRIC_DEVICE_SUELO"),          # opcional
}
INTERVALO_SEGUNDOS = int(os.environ.get("INTERVALO_SEGUNDOS", "60"))
SUELO_SECO = D.VARIABLES["humedad_suelo"]["normal"][0]         # 30 %
SUELO_ENCHARCADO = D.VARIABLES["humedad_suelo"]["limite"][1]   # 75 %
HORAS_ENTRE_ALERTAS = 3


def _hum(v):
    return None if v is None else round(max(0.0, min(100.0, float(v))), 1)


def _media(valores):
    return statistics.mean(valores) if valores else None


def calcular(s):
    """Datos -> {dispositivo: (temperatura, humedad)}. Solo incluye lo que realmente hay."""
    u, p, r = s["ultimos"], s["prom24"], s["recientes"]
    out = {}
    if "temperatura" in u:
        out["ambiente"] = (round(u["temperatura"]["valor"], 1), _hum(u.get("humedad_aire", {}).get("valor")))
    prom_t = p.get("temperatura", _media(r.get("temperatura")))          # sin el promedio 24 h, usa las ultimas lecturas
    prom_h = p.get("humedad_aire", _media(r.get("humedad_aire")))
    if prom_t is not None:
        out["promedio"] = (round(prom_t, 1), _hum(prom_h))
    if "humedad_suelo" in u and "temperatura" in u:
        out["suelo"] = (round(u["temperatura"]["valor"], 1), _hum(u["humedad_suelo"]["valor"]))
    return out


def evaluar_alerta(s, estado, ahora=None):
    """-> texto de la notificacion, o None. Avisa al cambiar de estado o cada HORAS_ENTRE_ALERTAS horas."""
    u = s["ultimos"].get("humedad_suelo")
    if not u:
        return None
    ahora = ahora if ahora is not None else time.time()
    v = u["valor"]
    nuevo = "seco" if v < SUELO_SECO else "encharcado" if v > SUELO_ENCHARCADO else "ok"
    if nuevo == "ok":
        estado["alerta"] = "ok"
        return None
    if nuevo != estado.get("alerta") or ahora - estado.get("t", 0) > HORAS_ENTRE_ALERTAS * 3600:
        estado["alerta"], estado["t"] = nuevo, ahora
        return (f"AgroIA: suelo seco ({v:.0f} %). Conviene regar." if nuevo == "seco"
                else f"AgroIA: suelo encharcado ({v:.0f} %). Suspende el riego.")
    return None


async def un_ciclo(sensores, estado):
    """Un ciclo de lectura y envio. Devuelve lo que envio (para pruebas y registro)."""
    s = await asyncio.to_thread(D.snapshot, True, True)
    valores = calcular(s)
    if not valores:
        print("No hay datos disponibles todavía (ni en la API ni en ThingSpeak).")
        return {}
    enviados = {}
    for nombre, (temp, hum) in valores.items():
        sensor = sensores.get(nombre)
        if sensor is None:
            continue
        try:
            await sensor.send_temperature_event(temp, hum)
            enviados[nombre] = (temp, hum)
        except Exception as e:                                            # noqa: BLE001
            print(f"No se pudo enviar a '{nombre}': {e}")
    if enviados:
        print("Enviado -> " + " | ".join(f"{n}: {t} °C, {h if h is not None else '--'} %" for n, (t, h) in enviados.items())
              + f"  (fuente: {s['fuente']})")
    aviso = evaluar_alerta(s, estado)
    if aviso:
        destino = sensores.get("suelo") or sensores.get("ambiente")
        try:
            await destino.send_push_notification(aviso)
            print("Notificación enviada:", aviso)
        except Exception as e:                                            # noqa: BLE001
            print(f"No se pudo enviar la notificación: {e}")
    return enviados


async def ciclo_principal():
    faltan = [n for n, v in (("SINRIC_APP_KEY", APP_KEY), ("SINRIC_APP_SECRET", APP_SECRET),
                             ("SINRIC_DEVICE_AMBIENTE", DISPOSITIVOS["ambiente"]), ("SINRIC_DEVICE_PROMEDIO", DISPOSITIVOS["promedio"])) if not v]
    if faltan:
        raise SystemExit("Faltan variables de entorno en Railway: " + ", ".join(faltan))

    client = SinricPro.get_instance()
    sensores = {}
    for nombre, device_id in DISPOSITIVOS.items():
        if device_id:
            sensores[nombre] = SinricProTemperatureSensor(device_id)
            client.add(sensores[nombre])
    await client.begin(SinricProConfig(app_key=APP_KEY, app_secret=APP_SECRET))
    print(f"Conectado a SinricPro con {len(sensores)} dispositivo(s): {', '.join(sensores)}. Datos desde {D.API_URL}")

    estado = {"alerta": "ok", "t": 0}
    while True:
        try:
            await un_ciclo(sensores, estado)
        except Exception as e:                                            # noqa: BLE001
            print(f"Error en el ciclo: {e}")
        await asyncio.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    asyncio.run(ciclo_principal())
