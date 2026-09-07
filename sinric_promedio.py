"""
Script puente: API (Neon) -> Sinric Pro -> Google Home
No usa ESP32 para nada. Cada cierto tiempo:
1. Consulta /muestras/list en la API real (Render)
2. Calcula el ÚLTIMO valor y el PROMEDIO
3. Empuja ambos a Sinric Pro (dos dispositivos distintos)

Con esto puedes preguntar por voz:
- "Ok Google, ¿qué temperatura hay en AgroIA Ambiente?"  -> último valor real
- "Ok Google, ¿qué temperatura hay en AgroIA Promedio?"  -> promedio real
"""

import asyncio
import os
import requests
from sinricpro import SinricPro, SinricProTemperatureSensor, SinricProConfig

# --- Variables de entorno (hay que configurarlas en Railway) ---
APP_KEY = os.environ["SINRIC_APP_KEY"]
APP_SECRET = os.environ["SINRIC_APP_SECRET"]
DEVICE_ID_AMBIENTE = os.environ["SINRIC_DEVICE_AMBIENTE"]   # "AgroIA Ambiente"
DEVICE_ID_PROMEDIO = os.environ["SINRIC_DEVICE_PROMEDIO"]   # "AgroIA Promedio"
API_URL = os.environ["API_URL"]

INTERVALO_SEGUNDOS = 60  # cada cuánto se actualiza el dato


def obtener_ultimo_y_promedio():
    """Consulta la API real y devuelve (ultimo_valor, promedio) o (None, None)."""
    respuesta = requests.get(f"{API_URL}/muestras/list", timeout=15)
    respuesta.raise_for_status()
    muestras = respuesta.json()

    if not muestras:
        return None, None

    # El más reciente, según fecha
    ordenadas = sorted(
        muestras,
        key=lambda m: m.get("Muestra_FechaHora") or "",
        reverse=True,
    )
    ultimo_valor = ordenadas[0]["Muestra_Valor"]

    # Promedio de todos los valores
    valores = [m["Muestra_Valor"] for m in muestras]
    promedio = sum(valores) / len(valores)

    return ultimo_valor, promedio


async def ciclo_principal():
    client = SinricPro.get_instance()

    sensor_ambiente = SinricProTemperatureSensor(DEVICE_ID_AMBIENTE)
    sensor_promedio = SinricProTemperatureSensor(DEVICE_ID_PROMEDIO)

    client.add(sensor_ambiente)
    client.add(sensor_promedio)

    config = SinricProConfig(app_key=APP_KEY, app_secret=APP_SECRET)
    await client.begin(config)

    print("Conectado a SinricPro. Iniciando ciclo de actualización...")

    while True:
        try:
            ultimo, promedio = obtener_ultimo_y_promedio()
            if ultimo is not None:
                await sensor_ambiente.send_temperature_event(ultimo)
                await sensor_promedio.send_temperature_event(promedio)
                print(f"Enviado -> último: {ultimo} | promedio: {round(promedio, 2)}")
            else:
                print("No hay muestras todavía en la base de datos.")
        except Exception as e:
            print(f"Error en el ciclo: {e}")

        await asyncio.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    asyncio.run(ciclo_principal())
