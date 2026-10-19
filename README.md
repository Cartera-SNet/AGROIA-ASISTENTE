# AgroIA — Puente a Sinric Pro (v2)

Cada 60 segundos lee los datos de AgroIA y los sube a Sinric Pro, para consultarlos desde la app de Sinric Pro y por voz con **Alexa**.

| Dispositivo (Temperature Sensor) | Temperatura | Humedad |
|---|---|---|
| **AgroIA Ambiente** | temperatura del aire, última lectura | humedad del **aire**, última lectura |
| **AgroIA Promedio** | temperatura promedio de 24 h | humedad del aire promedio de 24 h |
| **AgroIA Suelo** *(opcional)* | la del aire (referencia: no se mide temperatura del suelo) | humedad del **suelo**, última lectura |

Antes mezclaba todas las variables; ahora filtra por variable. Si la humedad del suelo baja de 30 % o pasa de 75 %, envía una notificación push (una vez por cambio de estado, o cada 3 horas si sigue igual).

## Variables de entorno (Railway)
| Variable | Obligatoria |
|---|---|
| `SINRIC_APP_KEY`, `SINRIC_APP_SECRET` | sí |
| `SINRIC_DEVICE_AMBIENTE`, `SINRIC_DEVICE_PROMEDIO` | sí (los IDs de siempre) |
| `SINRIC_DEVICE_SUELO` | no: ID del tercer dispositivo |
| `API_URL` | no: `https://agroiabackend.up.railway.app` por defecto (si aún apunta a Render se corrige sola) |

## Crear «AgroIA Suelo» (opcional)
1. En Sinric Pro: Devices → Add Device → nombre **AgroIA Suelo**, tipo **Temperature Sensor**, con tu Device Access Key.
2. Copia su Device ID en la variable `SINRIC_DEVICE_SUELO` de Railway.
3. Para recibir avisos, activa las notificaciones push en la app de Sinric Pro.

## Cómo subirlo
Sube **el contenido** de esta carpeta al repositorio del puente en GitHub. Railway vuelve a desplegar solo. En el registro (logs) debe verse: `Conectado a SinricPro con 2 (o 3) dispositivo(s)` y, cada minuto, `Enviado -> ambiente: ...`.

Frases de voz y comprobaciones: ver `FRASES_DE_VOZ_Y_COMPROBACIONES.txt`.
