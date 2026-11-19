# AgroIA — Contexto vivo del proyecto

| | |
|---|---|
| **Versión del documento** | **v1.12** |
| **Última actualización** | 17 de noviembre de 2026 |
| **Proyecto** | AgroIA — Diagnóstico de fertilidad del suelo |
| **Asignatura** | Inteligencia Artificial 26-2 · CUL · Docente: Bryan Josser Fernández Ebrath |

> **Este es el documento maestro y vive en los 4 zips** (frontend, backend, bot de Telegram y asistente Sinric), siempre con **la misma copia**. **Está escrito para poder iniciar un chat nuevo sin perder nada:** súbelo al principio de la conversación (junto con los zips si hay que tocar código) y usa el prompt de la §19.
> Se actualiza **cada vez que se cambia algo** (ver «Reglas de mantenimiento» y «Registro de cambios» al final).
> **No contiene claves ni contraseñas**: solo los *nombres* de las variables. Nunca pegues aquí un token, una clave de ThingSpeak ni una `DATABASE_URL`.

---

## 0. Resumen en 60 segundos (para quien llega nuevo)

- **Qué es:** AgroIA mide el suelo con un **ESP32** (temperatura del aire, humedad del aire, humedad del suelo y **TDS**) y lo muestra en una **página web**, un **bot de Telegram**, **Alexa/Google vía Sinric Pro** y el **menú LCD** del ESP32. Los datos van a **ThingSpeak** (canal 3540815) y a una **API FastAPI + Neon (PostgreSQL)** desplegada en **Railway**.
- **Equipo:** **Víctor** (el usuario de este chat; Punto 2, web, bot, Sinric, Railway y Git), **Thair** (API/SQL, `/chat`), **José** (firmware ESP32), **Julián y Kenny** (Edge Impulse). Docente: Bryan Josser Fernández Ebrath. IA 26-2, CUL.
- **Actualización 17 nov 2026:** se añadió el **modelo de Machine Learning** del Corte 3 (§5.1; árbol de decisión, 87,25 % en validación cruzada, matriz de confusión, conectado al formulario de Predicción). Falta el PowerPoint. El canal de ThingSpeak sigue sin datos nuevos.
- **Dónde estamos (28 oct 2026):** el software (web, bot, Sinric, backend) está terminado y probado **con datos simulados**. Lo que impide verlo funcionar de punta a punta es el **hardware/firmware**: el ESP32 **no envía datos desde ~21 oct** y el **TDS (campo 4) nunca ha llegado**.
- **Logros recientes:** el cuarto sensor pasó de pH a **TDS** en todo el proyecto; el chat web y el bot entienden **faltas de ortografía** y mandan órdenes del **LED**; la página indica **cuánto hace** del último dato; hay una **página de diagnóstico** (`diagnostico.html`); y el **backend ya duerme** (Serverless) en Railway: se confirmó «Sleeping» el 28 oct.
- **Lo más urgente:** (1) que José arregle el envío del ESP32 (ThingSpeak `field4` y `POST /muestras/create`); (2) **volver a montar AGROIA-ASISTENTE** en Railway (se borró a propósito para una prueba; §14.3); (3) **cambiar las claves** por el incidente de seguridad de Railway (§14.4); (4) la **seguridad de la API** (§12); (5) probar todo **1–2 días antes** de presentar (§14.5).
- **Dónde está cada cosa de este documento:** arquitectura §1–§3 · backend §4 · web §5 · bot §6 · Sinric §7 · equipo y pendientes §8 · Git §9 · Railway §10 y §14 · verificación §11 · seguridad §12 · **instalación y versiones §15** · pruebas §16 · **reglas de trabajo §17** · futuro §18 · **prompt para el chat nuevo §19** · historial §20.

---

## 1. Qué es AgroIA y cómo encajan las piezas

Un **ESP32** con sensores mide **temperatura del aire, humedad del aire, humedad del suelo y TDS (sólidos disueltos, ppm)**. Los datos van a la **API** (base de datos Neon) y a **ThingSpeak**. Cuatro programas los consumen:

```
                    ┌────────────────────────────┐
   ESP32 (sensores) │  ThingSpeak  canal 3586784 │──► Frontend (tablero, historial, gráficos)
        │  ├───────►│  (público, 4 campos)       │──► Respaldo del bot y del puente Sinric
        │  │        └────────────────────────────┘
        │  └───────► API (FastAPI, Railway) ──► Neon (PostgreSQL)
        │                │  /muestras  /menu/*  /esp32/comando  /vision/*
        │                ├──► Frontend (pestañas YOLO, cámara, alertas)
        │                ├──► Bot de Telegram (datos + foto → YOLO)
        │                └──► Puente Sinric Pro ──► Alexa / app de Sinric
        └◄── GET /esp32/comando (el ESP32 pregunta por órdenes; falta que el firmware lo haga)
```

| # | Componente | Zip | Repositorio | Servicio |
|---|---|---|---|---|
| 1 | **Frontend** (página web) | `AgroIA_frontend_web.zip` | `Cartera-SNet/PAgroIA` | Railway: servicio **PAgroIA** |
| 2 | **Backend** (API + YOLO) | `AgroIABackend_completo_sleep.zip` | `Cartera-SNet/AgroIABackend` | Railway (Dockerfile): servicio **AgroIABackend** |
| 3 | **Bot de Telegram** | `AgroIA_bot_telegram.zip` | `Cartera-SNet/AgroIA` | Railway: servicio **AgroIA** |
| 4 | **Puente Sinric Pro** | `AGROIA-ASISTENTE_sinric_sin_API.zip` | `Cartera-SNet/AGROIA-ASISTENTE` | Railway: servicio **AGROIA-ASISTENTE** (hoy borrado, ver §14.3) |

Un quinto archivo suelto, `AgroIA_Diagnostico.html`, es la página de diagnóstico (también viene dentro del zip del frontend como `diagnostico.html`).

## 2. Direcciones de producción

| Recurso | URL |
|---|---|
| API | https://agroiabackend.up.railway.app |
| Documentación de la API (Swagger) | https://agroiabackend.up.railway.app/docs |
| Página web | https://agroia-suelo.up.railway.app (tablero: `/dashboard.html`) |
| Canal ThingSpeak (público) | https://thingspeak.mathworks.com/channels/3586784 |
| Channel ID | `3586784` (desde el 18 nov 2026; el canal anterior era `3540815`) |

**Render ya no se usa.** Toda la API está en Railway. Cualquier variable `API_URL` que aún apunte a `onrender.com` debe cambiarse (el bot y el puente la corrigen solos al arrancar, pero conviene dejarla bien).

## 3. Datos

**ThingSpeak** (canal **3586784**, desde el 18 nov 2026): campo 1 = **humedad del suelo (%)** · campo 2 = **temperatura del aire (°C)** · campo 3 = **humedad del aire (%)** · campo 4 = **TDS (ppm)**. *(Antes, en el canal 3540815, el orden era 1 temperatura, 2 humedad del aire, 3 humedad del suelo; lo cambió José al crear el canal nuevo. El orden está en `js/config.js` → `campos`, en `campo_ts` del bot y de Sinric, y en `thingspeakKey/field1..4` del firmware: los cuatro deben coincidir.)* *(El pH ya no se mide.)* Enviar cada **≥ 20 s** (la cuenta gratis exige ≥ 15 s). La *Write API Key* se entrega **solo por privado** a José, nunca al grupo.

**Modelo de datos y nombres oficiales (v1.4).** Cada muestra que el ESP32 envía a la API (`POST /muestras/create`) lleva `Sensor_Id` (qué sensor físico), `Parametro_Id` (qué se midió) y `Muestra_Valor`. El **tipo de sensor** (`TipoSensor_Id`) **no se manda**: cuelga del sensor. La página, el bot, Sinric y el menú del LCD reconocen cada variable por el **nombre del parámetro**, no por un id.

| Variable | Parámetro (`parametros_medidos`) | Tipo de sensor (`tipos_sensor`) | Campo ThingSpeak | Letra LCD |
|---|---|---|---|---|
| Temperatura | Temperatura del aire (°C) | Temperatura del aire *(hoy en la base: «Temperatura», id 2)* | 2 | T |
| Humedad del aire | Humedad del aire (%) | Humedad del aire *(hoy: «Humedad ambiental», id 3)* | 3 | A |
| Humedad del suelo | Humedad del suelo (%) | Humedad del suelo *(id 1)* | 1 | S |
| TDS | TDS (ppm) | TDS *(id 5)* | 4 | D |
| pH | *(retirado: se ignora)* | pH *(id 4, retirado)* | — | — |

Los nombres antiguos («Temperatura», «Humedad ambiental», «TDS del suelo», «Sólidos disueltos totales») también se reconocen **en la página, el bot, Sinric y la página de diagnóstico**; los recomendados son los de la tabla. **Ojo — el backend (código del equipo) es más estricto:** exige que el parámetro se llame exactamente «TDS» y detecta el pH solo si se llama exactamente «pH» (ver §4.1). Un DHT puede ser un solo sensor que envía temperatura y humedad del aire. Para que el TDS quede bien guardado deben existir: el **parámetro «TDS»**, un **sensor de tipo TDS (id 5)**, y el ESP32 debe mandar el `Parametro_Id` del TDS y el `Sensor_Id` de ese sensor. No hay endpoint para borrar: el pH retirado simplemente se ignora.

**Neon (PostgreSQL)**, tablas clave: `muestras_suelo` (`Muestra_Id`, `Sensor_Id`, `Parametro_Id`, `Muestra_Valor`, `Muestra_FechaHora`), `parametros_medidos`, `sensores`, `lotes_tierra`, `usuarios` y otras. El ESP32 envía cada lectura con `POST /muestras/create` `{Sensor_Id, Parametro_Id, Muestra_Valor}`.

**Hora de las muestras:** si no viene fecha, el backend guarda `datetime.now()` **del servidor** (UTC en Railway). Colombia es UTC-5. *Supuesto a confirmar:* que todas las muestras estén en UTC (si hubo pruebas con el backend en un PC local, algunas pueden estar en hora de Colombia).

**Rangos «normales»** (los usan la página, el bot y el puente; salen de `frontend/js/config.js`, `RANGOS`):

| Variable | Normal | Límites de alerta |
|---|---|---|
| Temperatura del aire | 15–30 °C | 10–35 |
| Humedad del aire | 40–80 % | 30–90 |
| Humedad del suelo | 30–60 % | 20–75 |
| TDS | 0–1000 ppm | 0–1500 |

**Modelo YOLO** (`backend/models/best.pt`, base YOLOv8n): **2 clases** — `suelo_humedo` y `suelo_seco`.

## 4. Backend (`AgroIABackend`)

- **Tecnología:** FastAPI + SQLAlchemy + Neon. **Despliegue:** `Dockerfile` (`python:3.12-slim` + `libxcb1`, `libgl1`, `libglib2.0-0`, OpenCV headless). `railway.toml` con `builder = "DOCKERFILE"`, arranque `uvicorn main:app --host 0.0.0.0 --port $PORT`, healthcheck `/docs`. Hay `.dockerignore`; `imagenes/` y `uploads/` no van al despliegue; `models/best.pt` sí.
- **Variables de entorno en Railway** (solo nombres): `DATABASE_URL` (crítica), `BACKUP_CLAVE` (clave maestra de administración; **solo en Railway**), `SECRET_KEY`, `ALGORITHM` (HS256), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (opcionales), `INFLUXDB_URL` / `INFLUXDB_DATABASE` / `INFLUXDB_TOKEN` (**no se usan en la nube**).
- **Rutas principales:** `/auth`, `/users`, `/zonas_geograficas`, `/tipos_suelo`, `/lotes`, `/tipos_sensor`, `/sensores`, `/parametros`, `/muestras`, `/alertas`, `/consultas-llm`, `/iot`, `/vision` (`/analizar`, `/camara`, stream), `/menu`, `/esp32`, `/admin`.
- **Administración (v1.9) — respaldo y pausa de recepción** (`app/routes/admin_routes.py`, `app/core/admin_clave.py`, `app/services/respaldo_service.py`, `app/crud/ajuste_sistema_crud.py`, `app/models/ajuste_sistema_model.py`):
  - **Clave maestra:** la lee de la variable de entorno **`BACKUP_CLAVE`** (Railway). **Nunca está en el código ni en la página.** Si la variable no existe, estas rutas responden 503 (cerradas). La clave viaja en la cabecera `X-Admin-Clave`. Protección: 5 intentos fallidos por origen → bloqueo de 15 min; tope global de 30 fallos / 15 min (429).
  - `GET /admin/estado` (público): `{recepcion: "activada" | "pausada", clave_configurada}`.
  - `POST /admin/recepcion` `{accion: "pausar" | "activar"}` (con clave): fija la pausa. **Pausada:** `POST /muestras/create` **no guarda nada** y responde **202** `{ok:false, pausado:true}` (el ESP32 lo ve como «no guardado»; ThingSpeak no se afecta). La pausa **queda guardada en la base de datos** (tabla `ajustes_sistema`, se crea sola la primera vez con `CREATE TABLE IF NOT EXISTS`) y **sobrevive a reinicios**. Si el estado no se puede leer, se guarda la muestra (falla abierta) y se anota en el log.
  - `POST /admin/respaldo` (con clave): descarga un **.zip con un CSV por tabla** + `LEEME.txt` (fecha y filas por tabla). **Incluye los datos de los usuarios con su contraseña** (hoy en texto plano, ver §12): el archivo debe guardarse en privado.
  - **Si el usuario de Neon no puede crear tablas:** ejecutar una vez en el editor SQL de Neon: `CREATE TABLE IF NOT EXISTS ajustes_sistema ("Ajuste_Clave" VARCHAR(50) PRIMARY KEY, "Ajuste_Valor" VARCHAR(200) NOT NULL, "Ajuste_FechaActualizacion" TIMESTAMP NOT NULL);`
  - **Interfaz:** tarjeta «Administración (respaldo y pausa)» en `pages/configuracion.html` (`js/admin.js`): campo de clave (no se guarda en el navegador), botones Descargar respaldo / Pausar / Reanudar y el estado actual.
  - **Pendiente de Víctor:** crear la variable `BACKUP_CLAVE` en Railway; la clave que se usó al principio **se escribió en un chat** (está expuesta): cambiarla después solo exige editar esa variable, sin tocar código.
- **`/menu/*` (menú LCD del ESP32, teclas 2–7 y A):** `ultimo-registro`, `promedio-24h`, `max-min-hoy`, `promedio-por-hora`, `muestras-por-dia`, `dias-bajo-umbral`, `desviacion`. Respuesta: `{linea1, linea2, detalle}` (línea1 y línea2 ≤ 16 caracteres, para la LCD 16×2). Abreviaturas: **T** temperatura · **A** humedad del aire · **S** humedad del suelo · **D** TDS (ppm). Las teclas 1, 8, 9, 0 y B son locales del ESP32.
- **`/esp32/comando`:** `GET` (el ESP32 consulta; devuelve `{accion: "" | "encender_led" | "apagar_led"}` y limpia) y `POST` (`{accion}` para fijar la orden; **abierto, sin token**). Vive en la memoria del proceso. **Lo usa el chat web para encender y apagar el LED.**
- **InfluxDB:** no hay instancia en la nube. `/iot/ultima-medicion`, `/iot/historial`, `/vision/fusion` y `/vision/reporte-pdf` fallan por eso; la interfaz los tiene **ocultos** (decisión del equipo: el profesor no exige Influx).

- **Login con Google:** completo en `app/routes/auth_routes.py` (`GET /auth/google` → Google → `GET /auth/google/callback` → crea el usuario si no existe y redirige a `{FRONTEND_URL}/index.html?token=JWT`). **No necesita cambios de código**, solo configuración (ver «Login con Google» más abajo). Los usuarios de Google se crean con `TipoUsuario_Id=1` y `EstadoUsuario_Id=1`: esas filas deben existir en Neon.
- **TDS:** el cuarto sensor es el **TDS (ppm)**, campo 4 de ThingSpeak. En el menú del LCD se abrevia **D** (antes compartía la «P» con el pH). En Neon debe existir un parámetro llamado «TDS» (unidad ppm) y el ESP32 debe enviarlo con `POST /muestras/create`; los endpoints `/menu/*` lo recogen solos por su nombre.

**Login con Google (configuración, probada con las respuestas de Google simuladas: 10/10)**
1. **Google Cloud Console** → APIs y servicios → *Pantalla de consentimiento de OAuth* (tipo Externo; alcances `openid`, `email`, `profile`; mientras esté en «Prueba» solo entran los *usuarios de prueba* que se agreguen) → *Credenciales* → *Crear credenciales → ID de cliente de OAuth* → **Aplicación web** → en **URI de redirección autorizados** agregar exactamente `https://agroiabackend.up.railway.app/auth/google/callback` (y `http://localhost:8000/auth/google/callback` para pruebas locales).
2. **Variables del servicio backend en Railway:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` = `https://agroiabackend.up.railway.app/auth/google/callback` (idéntica a la de Google) y `FRONTEND_URL` = `https://agroia-suelo.up.railway.app`. Ya deben existir `SECRET_KEY`, `ALGORITHM` y `DATABASE_URL`.
3. Comprobar que en Neon existan `tipo_usuario` e `estado_usuario` con `id = 1`. Para el login con usuario y contraseña hace falta al menos un usuario creado (`POST /users/create`).

**Cambios de `menu_routes.py` en la v1.3 (por el TDS y por limpieza):** «TDS» se abrevia **D** y se evalúa primero (para que «TDS del suelo» no caiga en «suelo» = S); la línea corta del LCD quita partes enteras en vez de cortar un número («D1200», no «D12»); la humedad del suelo se identifica por «humedad» (no por cualquier nombre con «suelo»); `ultimo-registro` devuelve el último valor de cada variable; hora de Colombia en las teclas 4–7.

**4.1 Lo que corre hoy en producción es el código del equipo, no mis zips anteriores (28 oct).** El 26 oct Thair/Víctor reescribieron partes del backend (commit `bbf1923`, rama `main`: «Guardar el sensor 5 como TDS y dejar el pH fuera del menu»):
- `app/crud/muestra_suelo_crud.py`: si el sensor es de **tipo 5 (TDS)**, la muestra se guarda **siempre** en el parámetro «TDS» (prefiere el id 5; busca el parámetro por nombre **exacto** «tds», sin importar mayúsculas); un sensor de **tipo 4 (pH)** o un parámetro llamado exactamente «pH» se rechaza con 400 («el pH ya no se mide»). Si no existe un parámetro llamado exactamente «TDS» → 404 «Parámetro TDS no encontrado» (**el dato se pierde**).
- `app/routes/menu_routes.py`: versión propia con hora de Colombia, letra D para el TDS, línea corta que no corta números, humedad del suelo por «humedad»+«suelo», `ultimo-registro` con el último valor de cada variable más un campo extra `valores`, y exclusión del pH solo si el parámetro se llama exactamente «pH».
- `vision_routes.py` y `reporte_pdf_service.py`: sin pH. El PDF se genera bien (probado); `/vision/reporte-pdf` depende de InfluxDB y falla en la nube.
- Verificado con pruebas: las **63 rutas** son exactamente las del Swagger; con mis parches el conjunto pasó 25/25 contra PostgreSQL real.
- **Limitaciones conocidas del código del equipo (NO corregidas: el usuario pidió «no más cambios»):** nombres exactos («TDS», «pH»); un parámetro «TDS del suelo» daría 404; «Humedad ambiental» saldría como «H» en el LCD. Existe un parche flexible (reconocer por palabra) descrito en §18, no aplicado.
- **Mis cambios incluidos en `AgroIABackend_completo_sleep.zip` (solo 3 archivos sobre el zip del equipo `AgroIABackend_2.zip`):** `railway.toml` (+`sleepApplication = true`), `app/services/yolo_service.py` (YOLO se carga la primera vez que se usa, con cerrojo: `get_model()`) y `app/core/config.py` (`NullPool`; la variable `DB_POOL=1` devuelve el pool normal). Todo lo demás es idéntico. El zip no trae `.git`.
- **Los «Cambios de `menu_routes.py` en la v1.3» de arriba describen mi versión, que NO es la que corre en producción** (la del equipo la reemplaza).

**Problemas conocidos del backend**
1. **«Hoy» en UTC** en las teclas 4–7 de `/menu`: **corregido en `AgroIA_backend_api.zip` (v1.3)** — `menu_routes.py` usa la hora de Colombia (probado contra PostgreSQL real, 4 horas simuladas, con TDS). *Falta subirlo al repositorio.*
2. **`/menu/ultimo-registro`** devolvía solo la variable que llegó última (filtraba por la fecha exacta de la última muestra, y como cada variable llega en una petición distinta, salía una sola; con «TDS del suelo» además salía con la letra «S»). **Corregido en el mismo archivo:** devuelve el último valor de **cada** variable.
3. **`/chat` no existe.** Ya no bloquea el chat web (responde con su motor local), pero sigue siendo la vía para un chat con IA (Groq) en la página.
4. **Seguridad (verificado con una prueba real el 28 oct):** sin token se puede **crear usuarios** (`POST /users/create`; el usuario creado puede iniciar sesión), **listar usuarios con su contraseña en texto plano** (`/users/list`, `/users/userId/{id}`) y **encender/apagar el LED** (`POST /esp32/comando`). Las contraseñas se guardan y comparan en texto plano. Pendiente de decidir con Thair (ver §12 y §18).
5. El modelo `historial_consultas_llm` apunta a una tabla `"user"` que no existe (debería ser `usuarios`).
6. Cada petición a `/muestras/list` devuelve **todas** las filas (crece sin parar): por eso el bot y el puente leen solo las primeras.

## 5. Frontend (`PAgroIA`)

- **Qué es:** página estática (HTML/CSS/JS, sin librerías) servida con `serve.py` en Railway (`Procfile`). Se publica con el contenido en la raíz del repo.
- **Sesión:** `SESION_OBLIGATORIA = true` en `js/config.js`. Sin token, cualquier pantalla manda a `index.html` (login con usuario y contraseña, o con Google). Ya no existe el enlace «ver el tablero sin iniciar sesión». Al volver de Google, `index.html?token=JWT` guarda la sesión y entra al tablero.
- **`js/config.js`:** `API_PRODUCCION = https://agroiabackend.up.railway.app`, `THINGSPEAK = {channelId: "3540815", campos: {temp:1, humAire:2, humSuelo:3, tds:4}}`, `RANGOS` (`tds` es el rango del campo 4), `CLASIFICADOR.url = ""` (vacío: la predicción usa reglas hasta que el modelo del Punto 3 tenga URL).
- **Gráficas = iframes oficiales de ThingSpeak** (`tsChartUrl` en `js/ts.js`): la dirección sigue la plantilla de los códigos *Embed* F1–F4 del canal (F1–F3 son idénticos; el F4 usa el título y el eje del TDS) (`bgcolor`, `color`, `dynamic=true`, `results=60`, `title`, `type`, `xaxis=Hora`, `yaxis`): F1 temperatura (línea, `#ef4444`), F2 humedad del aire (columnas, `#3b82f6`), F3 humedad del suelo (línea, `#16a34a`), F4 TDS (línea, `#8b5cf6`, título «TDS (ppm)», eje «ppm»). Se usan en **Inicio** (4 tarjetas con etiqueta «Campo N», enlace a ThingSpeak y nivel óptimo/alto/bajo) y **Monitoreo**. El **Historial** muestra los iframes del rango elegido (`start`, `end`, `timezone=America/Bogota`, `average`, `dynamic=false`) junto a la tabla, las tarjetas de promedio y el CSV. No quedan gráficos dibujados por la página, salvo el anillo del % de fertilidad en Predicción.
- **Diseño del Inicio:** tarjetas de valores arriba; gráficas en 2 columnas de 1100 a 1599 px, 4 columnas desde 1600 px y 1 columna en celular. Cada iframe mide 262 px de alto.
- **Campo 4 vacío:** si el canal no trae datos del campo 4, la tarjeta dice «Sin lecturas de TDS en el canal» y el chat explica que el ESP32 aún no envía ese campo.
- **`diagnostico.html` (v1.4):** página de diagnóstico (también suelta como `AgroIA_Diagnostico.html`; se abre con doble clic, sin iniciar sesión, y solo lee). Revisa ThingSpeak (antigüedad de la última entrada y datos por campo) y la API (parámetros, tipos de sensor, sensores, última muestra de cada variable, qué `Sensor_Id`/`Parametro_Id` debe usar el ESP32, lo que mostraría el LCD) y da un semáforo con el cuerpo exacto de cada arreglo en Swagger y un informe para copiar y pegar en el chat. Probada con 3 situaciones simuladas (ESP32 caído, TDS con el sensor equivocado, todo bien).
- **Estado del sistema (v1.4):** si el último dato es viejo, la barra superior dice «Sin datos recientes · hace N día(s)» y el lateral muestra la fecha además de la hora (antes solo la hora, y un dato de hace días parecía vigente).
- **Chat web (Inicio y «Chat con IA»), sin depender del servidor:**
  - `js/chat-nlu.js` entiende el mensaje aunque tenga errores de escritura (tildes, mayúsculas, letras de más, de menos o cambiadas, palabras partidas como «encer der», vocales comidas como «encdre»): corrige cada palabra con el vocabulario del proyecto (parecido por sonido y por consonantes) y luego decide la intención.
  - `js/chat-core.js` contesta con datos reales de ThingSpeak: valores, resumen, promedio de 24 h, máximo y mínimo de hoy, desviación, por hora, por día, días bajo el umbral, riego, alertas, recomendaciones, fertilidad, rango ideal, definiciones, sensor en línea, proyecto, enlaces, YOLO y ayuda.
  - **LED:** «enciende / apaga el led» y sus variantes → `POST {API}/esp32/comando` con `{accion: "encender_led" | "apagar_led"}`. Si el mensaje es ambiguo («led», «no apagues el led», «enciende y apaga el led»), es una pregunta («¿está encendido?») o pide otro aparato (bomba, ventilador), **no envía nada** y aclara. La orden se entrega una sola vez, cuando el ESP32 consulta `GET /esp32/comando`.
  - Orden de respuesta: reglas locales → servidor `POST /chat` solo si no entendió (hoy no existe) → «¿quisiste decir…?» con botones tocables.
- **Preparado para una API dormida (v1.6):** `chatEnviarLed` reintenta la orden del LED (hasta 6 intentos, cada 5 s, 20 s por intento) y avisa «El servidor estaba dormido; despertándolo…» si el servidor devuelve 502/503/504 o no responde; un error real (400, 500) no se reintenta. `verificarApi` (indicador de la barra superior, solo en la pantalla **Chat** y las pantallas antiguas) espera y dice «API despertando…» en vez de «API sin conexión» en rojo. Inicio, Monitoreo, Historial, Predicción y Configuración **no consultan la API al abrirse** (leen ThingSpeak). Los tiempos se pueden cambiar con `window.CHAT_LED` y `window.API_VERIF`.
- **Detalle menor pendiente:** el comentario de `serve.py` todavía dice «backend en Render» (solo es un comentario).
- **Móvil:** barra inferior *Inicio · Monitoreo · Análisis (→ `pages/vision.html`) · Historial · Más*. La cámara en vivo abre la trasera y tiene el botón «Cambiar cámara».
- **Ocultas (no borradas):** Telemetría InfluxDB, Análisis integrado, Reportes PDF, Control IoT.
- **Railway:** `railway.json` con `sleepApplication: true` (ver §10). `requirements.txt` vacío a propósito.
- **Probado (ThingSpeak y API simulados, sobre el zip final descomprimido):** 37/37 batería completa en navegador (iframes F1–F4, Historial, aviso del campo 4, 4 tamaños de pantalla), 11/11 chat pequeño del Inicio (28 consultas con faltas + 13 órdenes del LED mal escritas) · Predicción con TDS · Historial, 7/7 login y Google, 15/15 página de diagnóstico (3 situaciones), 10/10 comportamiento con API dormida (LED con 502, aviso, error real sin reintento, indicador de API) y el entendimiento de mensajes: 144/144 del LED, 93/93 bien escritas, 99,6 % con un error de escritura y 99,4 % con dos (más de 5 900 casos al azar), 14/14 frases ajenas sin confundirse.

### 5.1 Modelo de Machine Learning (Corte 3 · «Propuesta de aula» de Inteligencia Artificial) — añadido el 17 nov 2026

**Qué pide el docente (Word `PROPUESTA_CORTE_3_IA_1.docx`):** aplicativo y circuito funcionando en el computador, poster, presentación en PowerPoint explicando el proceso por etapas, todos los integrantes participando, usar todos los componentes de IA vistos en clase (y aprovechar uno al máximo), no mostrar partes separadas; y como **adición** un algoritmo de Machine Learning con: dataset descargado de una plataforma vista en clase (mostrar la fuente al exponer), **formulario para hacer predicciones**, **métrica mínima de 85 %** y **matriz de confusión**.

**Lo que se hizo:**
- **Dataset:** Kaggle · *Plant-Health-Data* (usuario `ziya07`), https://www.kaggle.com/datasets/ziya07/plant-health-data , licencia CC0, 1 200 filas, 14 columnas, sin nulos. Clases: *Healthy* 299, *Moderate Stress* 401, *High Stress* 500. **Los datos son simulados** (así lo dice la propia página del dataset). Plataforma asumida: Kaggle (**por confirmar con el docente**).
- **Variables de entrada del modelo (las 3 que AgroIA mide y existen en el dataset):** temperatura del aire (`Ambient_Temperature`), humedad del aire (`Humidity`), humedad del suelo (`Soil_Moisture`). **El TDS no existe en ese dataset: no entra al modelo** (en la página sigue en el formulario y en las recomendaciones por rangos). Ningún dataset de Kaggle encontrado trae las 4 variables de AgroIA. Con los nutrientes N-P-K el dataset da ~99,7 %, pero AgroIA no los mide.
- **Algoritmo:** árbol de decisión (`DecisionTreeClassifier`, `max_depth=3`, `min_samples_leaf=10`, elegidos con 5 particiones sobre el 80 % de entrenamiento); modelo final entrenado con las 1 200 filas. Se probaron también Random Forest, Gradient Boosting, regresión logística y kNN: con estas 3 variables rinden ~75–86 %, sin ventaja sobre el árbol.
- **Resultados (honestos):** efectividad oficial = **validación cruzada de 5 partes sobre las 1 200 filas: 87,25 %** (1 047 aciertos; desviación 2,8 puntos). **Prueba 80/20 con semilla 42 (fijada de antemano): 84,58 %**, por debajo del 85 %; con 20 repartos distintos el resultado oscila entre ~82 % y ~91 % y pasa del 85 % en 17 de 20. Por eso se reporta la validación cruzada como cifra oficial y la prueba 80/20 aparte. **Si el docente exige una prueba 80/20 única, decirle las dos cifras con transparencia.**
- **Matriz de confusión (validación cruzada; filas = real, columnas = predicho; Saludable / Moderado / Alto):** [299, 0, 0] · [52, 348, 1] · [51, 49, 400]. Precisión/recall: Saludable 0,74/1,00 · Moderado 0,88/0,87 · Alto 1,00/0,80.
- **Qué aprendió el árbol (limitación a explicar):** solo usa la **humedad del suelo**: ≤ 20 % → estrés alto; 20–30 % → estrés moderado; > 30 % → saludable. En este dataset la temperatura y la humedad del aire casi no aportan (la etiqueta se construyó con humedad del suelo y nutrientes). El modelo predice el **estado de estrés de la planta**, no la fertilidad química del suelo.
- **Integración:** `js/modelo-ml.js` (árbol exportado a JSON, `mlPredecir()`), usado por `js/prediccion.js` (`clasificarLocal`) y cargado en `pages/prediccion.html`. Funciona en el navegador, sin servidor ni cambios en el backend. Si `CLASIFICADOR.url` (config.js, Edge Impulse del Punto 3) tiene una URL, **esa URL tiene prioridad** y se usa el modelo remoto; con `url: ""` se usa el árbol local. Las recomendaciones siguen saliendo de los rangos (`estimarPorReglas`).
- **Reproducir:** `entrenar_modelo.py` (`python entrenar_modelo.py data/plant_health_data.csv salida`; requiere pandas, scikit-learn, matplotlib) genera `modelo_arbol.json`, `metricas.json`, `matriz_confusion.png` y `matriz_confusion_prueba_80_20.png`. El resultado quedó idéntico al de Python en las 1 200 filas (1 200/1 200) y 5/5 casos probados en un navegador real (Chrome sin pantalla), sin errores de JavaScript.
- **Pendiente de este corte:** presentación en PowerPoint (por etapas); confirmar con el docente la plataforma y la métrica (validación cruzada vs. 80/20); que el ESP32 envíe datos para la demostración en vivo (§8).

## 6. Bot de Telegram v2 (`Cartera-SNet/AgroIA`)

**Archivos:** `bot_agroia.py`, `respuestas.py`, `conocimiento.py`, `nlu.py`, `datos_agroia.py`, `Procfile` (`web: python bot_agroia.py`), `requirements.txt`, `PREGUNTAS_QUE_SIEMPRE_CONTESTA.txt`.

**Cómo responde** (en este orden):
1. **Reglas + datos reales** (`respuestas.py`): valores actuales, promedios 24 h, máximo/mínimo de hoy, desviación, por hora, por día, días bajo el umbral, riego, alertas, recomendaciones, fertilidad estimada, estado del sensor, proyecto, YOLO, enlaces, ayuda. No dependen de la IA. Entiende varias variables en una pregunta. Antes de aplicar las reglas, `nlu.py` **corrige las faltas de ortografía** (mismo método que `js/chat-nlu.js` del chat web).
2. **Groq** (`openai/gpt-oss-120b`, respaldo `openai/gpt-oss-20b`) para lo demás, con los datos y el conocimiento de AgroIA como contexto.
3. **Si Groq falla o no hay `GROQ_API_KEY`:** responde con un resumen de datos.
4. **Foto del suelo** → `POST /vision/analizar` → «suelo húmedo / seco» + confianza, comparado con el sensor.
5. `SOLO_DATOS_REALES=1` → nunca usa la IA: lo que no es una pregunta conocida se rechaza con un mensaje (las órdenes del LED siguen funcionando).
6. **Orden del LED:** «enciende / apaga el led» y variantes (también mal escritas) → `POST {API}/esp32/comando`. Ambiguo («led», «no apagues el led»), pregunta de estado u otro aparato → no envía nada y aclara. Si la API falla, dice que no pudo enviarla (nunca «listo» en falso).

**Comandos:** `/start`, `/ayuda`, `/ejemplos`, `/resumen`, `/datos`.

**Datos** (`datos_agroia.py`): API de Railway como fuente principal (lee solo las primeras filas de `/muestras/list` + los `/menu/*`), **ThingSpeak como respaldo** y para completar variables que falten (p. ej. TDS). Caché de 20 s. Si `API_URL` apunta a Render, se corrige sola a Railway.

**Dormir:** el bot funciona con *webhook* (no consulta Telegram), así que Railway puede dormirlo; trae `railway.json` con `sleepApplication: true` y en el panel ya aparece «Sleeping». Si la API está dormida, la orden del LED se reintenta (6 intentos, 5 s entre ellos y 20 s de espera por intento: unos 25 s si el servidor responde 502 enseguida y hasta ~2,5 min si no responde); las preguntas de datos usan ThingSpeak de respaldo.

**Variables (Railway):** `TELEGRAM_TOKEN`, `PUBLIC_URL` (obligatorias) · `GROQ_API_KEY` (recomendada) · opcionales: `API_URL`, `GROQ_MODEL`, `SOLO_DATOS_REALES`, `MUESTRAS_EN_UTC` (`0` si las muestras están en hora de Colombia), `THINGSPEAK_CANAL`, `THINGSPEAK_BASE`, `DATOS_TTL_SEGUNDOS`, `USAR_API` (por defecto 1 en el bot), `PORT` (lo pone Railway).

**Qué es «real» y qué no:** los números, fechas y conteos salen de la API/ThingSpeak. Los **rangos y consejos** son los de la página y consejos agronómicos generales. La **fertilidad** es una estimación por reglas (no es el modelo de IA entrenado). Solo las respuestas de **Groq** pueden incluir texto que no salga de un dato.

**Probado (API simulada con los formatos de los `/menu`):** 64/64 preguntas de la lista, 43/43 variantes, 97/97 comprobaciones del bot, 14/14 de la capa de datos; **LED y faltas de ortografía:** 26 formas de encender y 20 de apagar (con y sin errores) envían la orden correcta, 19 casos que no deben mover el LED no lo mueven, y 1 729 preguntas con 1–2 errores de escritura al azar dan la misma respuesta que la bien escrita (99 %).

## 7. Puente Sinric Pro v2 (`Cartera-SNet/AGROIA-ASISTENTE`)

**Archivos:** `sinric_promedio.py`, `datos_agroia.py` (la misma capa de datos del bot), `Procfile` (`web: python sinric_promedio.py`), `requirements.txt` (`requests`, `sinricpro`), `FRASES_DE_VOZ_Y_COMPROBACIONES.txt`.

Cada **60 s** lee los datos **filtrados por variable** y los envía a dispositivos tipo *Temperature Sensor* (temperatura + humedad):

| Dispositivo | Temperatura | Humedad |
|---|---|---|
| **AgroIA Ambiente** | temperatura del aire (última) | humedad del **aire** (última) |
| **AgroIA Promedio** | promedio de 24 h | humedad del aire, promedio de 24 h |
| **AgroIA Suelo** *(opcional)* | la del aire (referencia; no se mide temperatura del suelo) | humedad del **suelo** (última) |

- **Alerta push** (app de Sinric): suelo < 30 % («seco») o > 75 % («encharcado»); una vez por cambio de estado y cada 3 h si sigue igual.
- Si no hay datos, **no envía nada**; si la API cae, usa ThingSpeak para Ambiente/Suelo y **no inventa** un promedio. Si falta `/menu/promedio-24h`, el promedio se calcula con las últimas lecturas.
- **Variables:** `SINRIC_APP_KEY`, `SINRIC_APP_SECRET`, `SINRIC_DEVICE_AMBIENTE`, `SINRIC_DEVICE_PROMEDIO` (obligatorias) · `SINRIC_DEVICE_SUELO`, `USAR_API`, `API_URL`, `INTERVALO_SEGUNDOS`, `THINGSPEAK_CANAL` (opcionales).
- **Fuente de datos (v1.5):** `USAR_API=0` **por defecto** (`os.environ.setdefault` antes de importar `datos_agroia`): lee **solo ThingSpeak** (último valor, 40 lecturas recientes y 24 promedios por hora) y **no llama a la API de Railway**. Motivo: consultaba cada 60 s y mantenía despierto al backend. Con `USAR_API=1` vuelve a leer la API (`API_URL`) con ThingSpeak de respaldo. Si no hay promedio de 24 h, usa el promedio de las lecturas recientes.
- **Por qué NO dormirlo:** mantiene una conexión permanente con Sinric Pro; si Railway lo durmiera los dispositivos quedarían desconectados. Debe permanecer «Online», sin dominio público («Unexposed service»).
- **Despliegue (observado en los logs del 28 oct):** Railpack 0.43.0, Python 3.13.16, `pip install -r requirements.txt`, arranca con `python sinric_promedio.py` (Procfile). Log de arranque correcto: «Conectado a SinricPro con 2 dispositivo(s): ambiente, promedio. Datos desde ThingSpeak (canal 3540815)». Una advertencia inofensiva al arrancar: «API_URL apuntaba a Render…» (la variable `API_URL` del servicio todavía apuntaba a Render; con `USAR_API=0` no se usa; se puede borrar).
- **Defecto conocido (pendiente de aprobación):** `evaluar_alerta` no revisa la antigüedad de la lectura. Con el ESP32 apagado, al arrancar y cada 3 h envía «AgroIA: suelo seco (15 %). Conviene regar.» con el último dato guardado (de hace días). Propuesta: no alertar si la lectura tiene más de 60 min. El usuario debe aprobarlo con la frase «Aprobado alertas».
- **Estado:** el servicio fue **borrado a propósito el 28 oct** (prueba para confirmar que el backend duerme sin Sinric). Hay que montarlo de nuevo (§14.3).
- **Voz:** la documentación de Sinric documenta las frases de temperatura y humedad **para Alexa**; marca **Google Home como «Not Supported»** para sensores de temperatura. En el Parcial 1 se usó «Ok Google…».
- **Google:** el Asistente se está reemplazando por **Gemini**. Para que funcione hay que: poner Gemini como asistente del teléfono, activar «Hey Google», ejecutar «Configurar Gemini for Home» en la app Google Home y mantener vinculado Sinric Pro. **Estado:** ya responde por voz, pero la **temperatura se dice en inglés**; el idioma se ajusta en Google (Home → Ajustes del hogar → Gemini for Home → Idioma; Gemini → Idiomas; voz de Android), no en el puente. *Pendiente de resolver.*
- **El TDS no se puede consultar por voz** (Sinric no tiene dispositivo de TDS): se pregunta en el bot.
- **Probado (Sinric simulado, desde el zip final):** 25/25, incluidos «con `USAR_API=0` no hace ninguna llamada a la API» y «entrega los 3 dispositivos».

## 8. Reparto del equipo y pendientes

| Punto | Pts | Responsable | Estado |
|---|---|---|---|
| 1. Menú LCD con teclado + SQL | 20 | Thair (API) + José (ESP32) | API `/menu/*` en producción; José debe apuntar el firmware a Railway y probar teclas 2–7 y A |
| 2. ThingSpeak + web | 25 | **Víctor** | Canal público y página en Railway; falta el envío real del ESP32 |
| 3. Edge Impulse | 25 | Julián + Kenny | **Entregado** (según Víctor, 17 nov). Si tienen una URL del modelo, ponerla en `CLASIFICADOR.url` (tendría prioridad sobre el árbol local, §5.1) |
| 4. Chat con IA | 30 | Todos | `/esp32/comando` listo y el chat web y el bot de Telegram ya envían las órdenes del LED; faltan que el firmware consulte `GET /esp32/comando` cada X segundos y, opcional, `/chat` con IA |

**Pendientes abiertos (consolidados al 28 oct 2026)**

*Prioridad alta*
- [ ] **El ESP32 no envía nada desde ~21 oct** (ThingSpeak: «Last entry» de hace días, 854 entradas; el tablero dice «Sin datos recientes · hace N día(s)»). Revisar encendido, WiFi, Write API Key y que envíe cada ≥ 20 s. Mientras no envíe, no aparecerá ningún dato nuevo (ni el TDS); cambiar nombres o ids en la base no afecta a ThingSpeak. Para diagnosticar: `diagnostico.html`.
- [ ] **José, firmware:** (a) enviar `field4` (TDS en ppm) a ThingSpeak **solo si la lectura es válida** (un `nan` hace que ThingSpeak rechace toda la actualización → error 400); (b) enviar también cada lectura a `POST /muestras/create` con el `Sensor_Id` del sensor TDS y el `Parametro_Id` del parámetro «TDS»; (c) consultar `GET /esp32/comando` cada pocos segundos para el LED; (d) **tiempos de espera largos y reintentos** porque la API ahora duerme (código en `Para_Jose_TDS_ThingSpeak.txt`). La Write API Key se entrega **solo por privado**.
- [ ] **Neon:** comprobar (con `diagnostico.html` o `/parametros/list`, `/sensores/list`) que exista un parámetro llamado **exactamente «TDS»** (ppm) y un **sensor de tipo 5 (TDS)**; si no, los datos del TDS se pierden (404). El pH (tipo 4) queda retirado.
- [ ] **Montar de nuevo `AGROIA-ASISTENTE`** (§14.3) y comprobar ~20 min después que **AgroIABackend sigue «Sleeping»** con Sinric corriendo.
- [ ] **Cambiar las claves por el incidente de Railway** (§14.4). Ninguna se ha rotado (por confirmar).
- [ ] **Subir/confirmar los despliegues pendientes** (§14.2, §14.6): backend completo, página y bot, de uno en uno esperando ACTIVE; dejar encendido Serverless en AgroIABackend, PAgroIA y AgroIA.

*Prioridad media*
- [ ] **Seguridad de la API** (§12): proteger `POST /users/create`, `/users/list`, `/users/userId`, `POST /esp32/comando`; no devolver contraseñas; idealmente guardar contraseñas con hash. Decidir con Thair.
- [ ] **Alertas de Sinric con datos viejos** (§7): pendiente de la frase «Aprobado alertas».
- [ ] **Login con Google:** 4 variables en Railway + Google Cloud (§4) y crear al menos un usuario.
- [ ] **Hora de las muestras:** confirmar que están en UTC (si hubo pruebas con el backend en un PC local, algunas pueden estar en hora de Colombia; el bot admite `MUESTRAS_EN_UTC=0`).
- [ ] **Punto 3 (Julián y Kenny):** Edge Impulse; poner su URL en `CLASIFICADOR.url`; el contrato del clasificador ahora lleva `tds` en lugar de `ph` (`{temperatura, humedad_aire, humedad_suelo, tds}`).
- [ ] **Punto 1:** José apunta el firmware a Railway y prueba las teclas 2–7 y A del menú LCD.
- [ ] **Punto 4:** `/chat` con IA en el backend (opcional; el chat web ya responde localmente).

*Prioridad baja / cosmética*
- [ ] Temperatura en inglés al preguntar por voz a Google (se ajusta en el idioma de Google, no en el puente).
- [ ] Variable `API_URL` del bot (debe apuntar a Railway); borrar `API_URL` del servicio Sinric (apunta a Render).
- [ ] Comentario de `serve.py` («backend en Render»); modelo `historial_consultas_llm` apunta a una tabla `"user"` inexistente.
- [ ] **Video de demostración** y ensayo de la presentación (§14.5).
- [ ] Fuera de AgroIA: compilador **Costeñol** (otra asignatura, entrega del 16 oct vencida): falta el documento Word y el script de tokenización.

## 9. Git en el PC de Víctor (lección aprendida)

- En `C:\Users\vyepez` hay un **repositorio de Git escondido** cuyo remoto es `Cartera-SNet/ExtractorTELEGRAM`. Cualquier carpeta dentro de Descargas pertenece a él. **Nunca ejecutes `git add .` ahí.**
- Trabaja siempre en **`C:\proyectos`**: `git clone <repo>`, copia los archivos (`Get-ChildItem -Force -File <origen> | Copy-Item -Destination <clon> -Force`) y sube desde el clon.
- Antes de subir: `git rev-parse --show-toplevel` y `git remote -v` deben mostrar el repositorio correcto, y `git status` debe mostrar rutas cortas (sin `Downloads/...`).
- Si el push dice *rejected*: `git pull --rebase` y luego `git push` (**nunca** `--force`). Después del push, confirmar en Railway que el despliegue diga **Active**.

## 10. Railway: notas

- **Serverless / «sleep application» (v1.5):** `deploy.sleepApplication` **sí es una clave válida** del archivo de configuración de Railway (la genera el propio panel), aunque la lista oficial de ajustes no la mencione; en el backend va en `railway.toml` (`sleepApplication = true`). Railway marca los archivos de configuración como obsoletos desde el **1 dic 2026**, así que el interruptor del **panel** (servicio → Settings → Deploy → Serverless) es lo que perdura: déjalo encendido también. Railway duerme un servicio tras **10 min sin tráfico saliente**; una conexión abierta a la base de datos (un pool) y un cliente que consulte cada pocos minutos lo mantienen despierto. La primera petición tras dormir tarda (arranque en frío) o da 502: los clientes deben reintentar (el bot reintenta la orden del LED; el ESP32 debe hacerlo en el firmware). Antes de una presentación, abrir `/docs` uno o dos minutos antes.
- **Qué impedía dormir el backend y cómo quedó (v1.6):** (1) el puente **AGROIA-ASISTENTE** (Sinric) lo consultaba cada 60 s → ahora lee **solo ThingSpeak** (`USAR_API=0` por defecto); (2) YOLO/torch se cargaban al arrancar → ahora se cargan la **primera vez que se usa `/vision`** (`yolo_service.py`, `get_model()`; baja la RAM base y acorta el arranque en frío); (3) el motor de BD guardaba conexiones abiertas (el pool cuenta como actividad) → ahora **`NullPool`**, una conexión por consulta (`app/core/config.py`; variable `DB_POOL=1` devuelve el pool normal); (4) `railway.toml` con `sleepApplication = true`. Costos: la **primera** imagen de `/vision` tras cada arranque tarda más y, en el WebSocket `/vision/stream`, bloquea el servidor mientras carga el modelo; cada consulta a la base abre una conexión nueva (~100–300 ms).
- **Quién mantiene despierto al backend (v1.6):** el **ESP32** mientras esté encendido (envía muestras y consulta `/esp32/comando`; es inherente: el backend duerme cuando el ESP32 está apagado), las pestañas abiertas de `alertas.html`/`iot.html` (consultan cada 10 s; no están en el menú), la pantalla **Chat** (al abrirse pre-calienta la API; es útil para el LED) y quien use `/vision/stream`. **Ya no:** Sinric, el bot (solo reacciona a mensajes) ni Inicio/Monitoreo/Historial/Predicción/Configuración (leen ThingSpeak).
- **Clientes preparados para una API dormida (v1.6):** la página reintenta la orden del LED (hasta 6 intentos, avisa «despertándolo…») y su indicador de API espera y dice «API despertando…»; el bot reintenta la orden del LED (6 intentos, entre ~25 s y ~2,5 min); el **firmware del ESP32 debe reintentar** (ver `Para_Jose_TDS_ThingSpeak.txt`).
- **No activar Serverless en AGROIA-ASISTENTE:** mantiene una conexión permanente con Sinric Pro; dormirlo desconectaría los dispositivos. **Estado visto el 28 oct (capturas):** PAgroIA, AgroIA (bot), RuntBot, EXPORTECARTERAS y GOOGLE-CALENDAR «Sleeping»; **AgroIABackend «Sleeping» (confirmado; el usuario encendió el interruptor Serverless en el panel)**; ExtractorTELEGRAM «Online»; AGROIA-ASISTENTE borrado a propósito.
- Los servicios del bot y de Sinric usan `Procfile` con `web:`; no escuchan HTTP salvo el bot (webhook de Telegram).
- **Config as Code (v1.7):** en los ajustes de AgroIABackend, «Railway Config File» está **vacío** y Railway avisa que *Config as Code* está obsoleto (los archivos siguen funcionando hasta el **1 dic 2026**; desde el 28 ago 2026 los servicios que nunca lo usaron **no pueden activarlo**). Conclusión: **`railway.toml` probablemente no se lee en el backend** y el modo dormir funciona por el **interruptor del panel**. Dejar `sleepApplication` en los archivos no hace daño. El healthcheck del panel también está vacío.
- **Más detalle del estado de Railway, el incidente, las claves, los costos y cómo pausar sin borrar:** §14.

## 11. Qué está verificado y qué no

**Verificado por mí con datos simulados (resultados finales, sobre los zips descomprimidos; detalle en §16):** página (37/37 + 11/11 + 7/7 + 15/15 + 10/10 en navegador) y entendimiento de mensajes (144/144 del LED, 99,6 %/99,4 % con faltas de escritura), bot (97/97, 43/43, 11/11, capa de datos 23/23), puente Sinric (25/25), backend contra **PostgreSQL real** (las 63 rutas del Swagger, reglas de guardado del sensor TDS, hora de Colombia en 4 franjas, `NullPool` sin conexiones abiertas tras 100 consultas, arranque sin torch, `/docs`, PDF), flujo de login con Google (10/10, con las respuestas de Google simuladas) y la prueba del cargador perezoso de YOLO.

**No verificado contra servicios reales:** la API y la base Neon de producción (el asistente no puede acceder a ellas), **cómo dibuja ThingSpeak los iframes** (no se pudo acceder a su sitio; la dirección sigue la plantilla de los códigos Embed), el login real con Google, que el LED físico responda (depende del firmware), **YOLO real** (en las pruebas se simula; la primera imagen tras cada arranque tarda más y no se midió cuánto), Groq, Telegram, Sinric Pro, Google/Gemini, Alexa, los tiempos reales de despertar en Railway y el contenido exacto de los despliegues actuales. El primer arranque en producción lo confirma (logs de Railway). **Los scripts de prueba del asistente se perdieron** cuando se reinició su entorno (ver §16): las cifras de arriba quedan como constancia, pero hay que reconstruir las pruebas para repetirlas.

## 12. Seguridad

- **Nunca** subir a GitHub ni compartir en el grupo: `.env`, `TELEGRAM_TOKEN`, `GROQ_API_KEY`, `SINRIC_APP_SECRET`, la Write API Key de ThingSpeak, la `DATABASE_URL` de Neon.
- Algunas claves aparecieron en documentos y chats anteriores (por ejemplo la contraseña de Neon y el token de InfluxDB): se recomienda **rotarlas**.
- `.gitignore` de cada repo debe incluir `.env`.
- **Incidente de seguridad de Railway (20–22 oct 2026):** Railway recomienda a todos los clientes registrados antes del 21 oct **cambiar las claves guardadas en sus variables** (lista y método en §14.4). Estado: pendiente.
- **Archivo sensible en las entregas antiguas:** `AgroIA_local_CON_ENV.zip` contiene un `.env` con claves reales. No compartirlo ni subirlo; las claves que contiene deben rotarse.
- **Huecos de la API verificados (28 oct):** crear usuarios sin token, listar usuarios con contraseña en texto plano, encender/apagar el LED sin token (ver §4.1 y §18).
- Los zips y este documento **no contienen claves** (se revisó con búsquedas de patrones de claves en cada entrega).

## 13. Reglas de mantenimiento de este documento

1. **Cada cambio** (código, variables, URLs, pendientes, decisiones) actualiza las secciones afectadas **y** agrega una entrada arriba del «Registro de cambios», con fecha y qué zips se tocaron.
2. Se **sube la versión** del documento (v1.0 → v1.1 → …) y se actualiza la fecha de la cabecera.
3. **La misma copia** va en los 4 zips y como `AgroIA_CONTEXTO.md` suelto. Si un zip no cambió, se le agrega de todos modos el documento nuevo.
4. Sin claves ni contraseñas: solo nombres de variables.
5. Lo no verificado se marca como «por confirmar»; se quita la marca solo cuando alguien lo comprueba.
6. **Chat nuevo:** subir este archivo al principio y pegar el prompt de la §19. No hay memoria entre conversaciones; este documento es la memoria.
7. **Si algo del documento contradice lo que muestran las capturas o los logs del usuario, mandan las capturas y los logs**; corregir el documento.
8. Las reglas de trabajo con el usuario están en la §17 y también son obligatorias.

## 14. Estado actual detallado (28 oct 2026)

### 14.1 Servicios en Railway (proyecto «capable-respect», entorno «production»)

| Servicio | Qué es | Dirección | Estado visto |
|---|---|---|---|
| **PAgroIA** | Frontend (la página) | `agroia-suelo.up.railway.app` | Sleeping |
| **AgroIABackend** | API FastAPI + YOLO | `agroiabackend.up.railway.app` | **Sleeping** (confirmado 28 oct) |
| **AgroIA** | Bot de Telegram (webhook) | `agroia-production.up.railway.app` | Sleeping |
| **AGROIA-ASISTENTE** | Puente Sinric Pro (sin URL pública) | — | **Borrado a propósito el 28 oct; hay que montarlo de nuevo (§14.3)** |
| RuntBot, EXPORTECARTERAS, ExtractorTELEGRAM, GOOGLE-CALENDAR (con el volumen `google-calendar-volume`) | **Otros proyectos de clase; no son de AgroIA** | — | No tocar (ExtractorTELEGRAM aparecía «Online») |

**Ajustes vistos de AgroIABackend (Settings):** repo `Cartera-SNet/AgroIABackend`, rama `main`, **despliegue automático al hacer push**, builder Dockerfile (autodetectado), dominio `agroiabackend.up.railway.app` con puerto 8080 (Railway inyecta `PORT`), 1 réplica en US East, límites de réplica 8 vCPU / 8 GB (plan probablemente Hobby; las réplicas multi-región son solo del plan Pro; *por confirmar*), reinicio «On Failure» con máximo 10 intentos, **Serverless activado por el panel**, «Railway Config File» vacío (ver §10) y healthcheck del panel vacío.

### 14.2 Qué está desplegado y qué falta
- **Backend:** corre el código del equipo (commit `bbf1923`, 26 oct). Después hubo despliegues llamados «Nuevo Cambio» (atascado por el incidente de Railway y reintentado), «Nuevo Backend Inicial» y «Cargue Inicial» (28 oct); **no se verificó** que el contenido sea el de `AgroIABackend_completo_sleep.zip`. Comprobar en GitHub que `app/core/config.py` tenga `NullPool` y `app/services/yolo_service.py` tenga `get_model`.
- **Sinric:** la versión con `USAR_API=0` se desplegó («Actualizar», 28 oct) y funcionó; luego se borró el servicio.
- **Página y bot:** *por confirmar* que las versiones v1.6 estén subidas.

### 14.3 Cómo montar de nuevo AGROIA-ASISTENTE
1. Railway → proyecto *capable-respect* → **Add → GitHub Repo** → `AGROIA-ASISTENTE`. El repositorio debe traer el código con `USAR_API=0` (si no, copiar los archivos de `AGROIA-ASISTENTE_sinric_sin_API.zip`, sin `.git`).
2. **Variables** (solo nombres; los valores salen del panel de Sinric Pro, nunca de GitHub ni de este documento): `SINRIC_APP_KEY`, `SINRIC_APP_SECRET`, `SINRIC_DEVICE_AMBIENTE`, `SINRIC_DEVICE_PROMEDIO` y, opcional, `SINRIC_DEVICE_SUELO`. **No hacen falta** `API_URL` ni `USAR_API`.
3. **No generar dominio público** y **no activar Serverless** (debe aparecer «Unexposed service» y «Online»).
4. En *Deploy Logs* debe verse «Conectado a SinricPro con 2 dispositivo(s): ambiente, promedio. Datos desde ThingSpeak (canal 3540815)». Una advertencia sobre `API_URL` apuntando a Render es inofensiva.
5. Recomendado: **regenerar la App Secret en Sinric Pro** antes de ponerla (incidente de Railway, §14.4); los ID de los dispositivos no cambian.
6. Al arrancar enviará una vez «suelo seco (15 %)» con la última lectura guardada (defecto conocido, §7).
7. Prueba final: ~20 min después, **AgroIABackend debe seguir «Sleeping»**.

### 14.4 Incidente de seguridad de Railway y claves
- **Qué pasó:** entre el 20 y el 22 oct 2026 un atacante accedió a sistemas internos de Railway y pudo descifrar variables de entorno de una fracción de los proyectos (hasta el 1,85 % de los workspaces, según su informe preliminar: `blog.railway.com/p/preliminary-report-october-security-incident`). No accedió a cuentas de usuario. **Railway recomienda a todos los clientes registrados antes del 21 oct cambiar las claves guardadas en Railway.** Los registros nuevos están pausados. Hay actualizaciones diarias en `status.railway.com`.
- **28 oct:** compilaciones fallando o atascadas en US East y EU West («los servicios en marcha no se ven afectados»). Un despliegue de AgroIABackend pasó más de 24 min en «Creating containers…»; mientras tanto el despliegue activo siguió sirviendo; se reintentó y funcionó. Railway también renovó las instalaciones de su GitHub App: si un push no despliega, reconectar GitHub; los commits empujados mientras estuvo pausado el 21 oct pueden no haberse desplegado (hacer redeploy).
- **Claves a cambiar (nombres):** `DATABASE_URL` (Neon: restablecer la contraseña del rol y actualizar la variable), `SECRET_KEY` (invalida las sesiones), `GOOGLE_CLIENT_SECRET`, `GROQ_API_KEY`, `TELEGRAM_TOKEN` (con `/revoke` en BotFather), `SINRIC_APP_SECRET`, y la Write API Key de ThingSpeak **solo si** estuviera en Railway (hoy solo está en el firmware de José). Revisar también el registro de auditoría y las aplicaciones autorizadas de GitHub, y el correo por avisos de Railway/GitHub/Google.
- **Método seguro:** **una variable por vez** (cada cambio puede disparar un redeploy), comprobar `agroiabackend.up.railway.app/docs` después de cada una, **no revocar una clave en su proveedor antes de poder desplegar la nueva**, y hacerlo cuando las compilaciones de Railway funcionen.
- **Estado:** ninguna clave rotada todavía (*por confirmar con el usuario*).

### 14.5 Dormir, costos y pausar
- **Cómo duerme:** Railway Serverless duerme el servicio tras **10 min sin tráfico saliente**; se activa en el panel (servicio → Settings → Deploy → Serverless). Quién lo mantiene despierto: ver §10.
- **Si no duerme:** (1) interruptor encendido; (2) HTTP logs del backend para ver quién lo llama; (3) ESP32 apagado, Sinric solo con ThingSpeak, sin pestañas abiertas de `alertas.html`/`iot.html`; (4) esperar 15–20 min; (5) comprobar que el despliegue tenga `NullPool` y `get_model`.
- **Pausar sin borrar:** en Deployments, menú ⋮ del despliegue activo → **Remove** («elimina el despliegue y detiene cualquier uso posterior», según la documentación de Railway; no probado en este proyecto). Conserva el servicio, sus variables, su dirección y sus ajustes, pero la API queda apagada (no a dormir) hasta un nuevo despliegue. Para volver: `git commit --allow-empty -m "Reactivar backend"` y `git push` (hay despliegue automático). Mientras esté removido: **no hay login en la página** (depende de la API), no funciona el LED, y el bot sigue dando datos con ThingSpeak.
- **No borrar el servicio ni el proyecto:** la URL cambiaría (está escrita en `js/config.js`, el bot, el firmware, el redirect de Google, `FRONTEND_URL` y el webhook), se perderían las variables, y «capable-respect» contiene otros servicios de clase y un volumen con datos. Neon, ThingSpeak y GitHub viven fuera de Railway y no se ven afectados.
- **Costos:** Railway cobra por uso (memoria, CPU, red); no se pudo ver la factura. Revisar *Usage/Billing* y **fijar un límite de uso** (la documentación de Railway menciona límites de uso). Con YOLO cargado perezosamente y el backend durmiendo, el gasto debería ser bajo.
- **Para presentar en la universidad:** desplegar y probar **1–2 días antes**; abrir `/docs` 1–2 min antes para despertarlo; **no redesplegar el mismo día** (las compilaciones de Railway fallaron esta semana). Probar: login, LED desde el chat y desde el bot, una foto en visión (la primera tarda), y que lleguen datos del ESP32.

### 14.6 Entregables finales de este chat (28 oct 2026)

| Archivo | Qué es | Dónde va |
|---|---|---|
| `AgroIA_CONTEXTO.md` | Este documento (v1.7) | Va dentro de los 4 zips; también sirve para iniciar el chat nuevo |
| `AgroIABackend_completo_sleep.zip` | Backend completo (código del equipo + 3 archivos, sin `.git`) | Copiar **encima** del clon de `AgroIABackend`; `git status` debe mostrar solo los archivos esperados |
| `AgroIA_frontend_web.zip` | Página (build v1.6) | Clon de `PAgroIA` |
| `AgroIA_bot_telegram.zip` | Bot de Telegram (v2 con corrector, LED, TDS y reintentos) | Clon de `AgroIA` |
| `AGROIA-ASISTENTE_sinric_sin_API.zip` | Puente Sinric (lee solo ThingSpeak) | Clon de `AGROIA-ASISTENTE` |
| `AgroIA_Diagnostico.html` | Página de diagnóstico suelta (doble clic) | No se sube |
| `Para_Jose_TDS_ThingSpeak.txt` | Instrucciones para José (TDS, ids, reintentos); sin claves | Enviarlo por privado |

**Orden de subida:** (1) montar Sinric, (2) backend, (3) página, (4) bot; **uno a la vez, esperando «Active»**. En cada repo: `git pull`, copiar los archivos encima del clon (nunca el `.git` del zip), `git status`/`git diff`, commit y push.

**Archivos antiguos en la carpeta de entregas (no usar):** `AgroIA_backend_api.zip` (anterior al código del equipo), `AgroIABackend_parche_sleep.zip` y `OPCIONAL_pool_sin_conexiones.zip` (ya incluidos en el backend completo), `AgroIABackend_2_sleep.zip` (zip del equipo con `.git`, 38 MB, solo con `railway.toml`), `AgroIA_asistente_sinric.zip` (nombre antiguo), `AgroIA_endpoints_menu.zip` (obsoleto), `AgroIA_backend_parche_hora_colombia.zip`, `AgroIA_Tablero.zip`, `agroia_frontend.zip`, `agroia_web.zip`, `AgroIA_railway.zip`, `AgroIA_cambio_camara_movil.zip`. **Sensible:** `AgroIA_local_CON_ENV.zip` contiene un `.env` con claves.

## 15. Instalación, comandos y versiones

### 15.1 Versiones (28 oct 2026)

| Pieza | Versión / estado | Runtime | Dependencias principales |
|---|---|---|---|
| Documento | v1.12 | — | — |
| Frontend | build v1.12 (página 10.6: canal nuevo 3586784 y nuevo orden de campos) | HTML/CSS/JS sin librerías; `serve.py` (Python 3) | `requirements.txt` vacío a propósito |
| Backend | código del equipo (`bbf1923`) + 3 archivos (v1.6) | `python:3.12-slim` (Dockerfile) | `fastapi==0.115.12`, `uvicorn==0.34.2`, `starlette==0.46.2`, `SQLAlchemy==2.0.40`, `psycopg2-binary==2.9.12`, `pydantic==2.11.3`, `python-jose==3.5.0`, `python-multipart==0.0.32`, `python-dotenv==1.1.0`, `google-auth==2.59.0`, `httpx==0.28.1`, `requests==2.34.2`, `numpy==2.5.3`, `pillow==12.3.0`, `opencv-python-headless==4.10.0.84`, `reportlab==5.0.1`, `torch==2.14.0`, `torchvision==0.29.0`, `ultralytics==8.4.163`, `ultralytics-platform==0.1.65`, `ultralytics-thop==2.1.6` (70 líneas en total) |
| Bot de Telegram | v2 (+corrector, LED, TDS, reintentos) | Railpack de Railway (la versión de Python del bot: *por confirmar*) | `python-telegram-bot[webhooks]`, `requests`, `python-dotenv`, `groq` (sin versión fijada) |
| Puente Sinric | v2 (+`USAR_API=0`) | Railpack 0.43.0, Python 3.13.16 | `requests`, `sinricpro` |
| Modelo | YOLOv8n, 2 clases (`suelo_humedo`, `suelo_seco`) | `models/best.pt` (también `best_anterior.pt`) | — |
| IA del bot | Groq `openai/gpt-oss-120b` (respaldo `openai/gpt-oss-20b`) | — | — |

### 15.2 Comandos para correr cada pieza en el PC (PowerShell de Windows; carpeta de trabajo `C:\proyectos`)

**Backend**
```powershell
cd C:\proyectos\AgroIABackend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt            # pesado: instala torch (varios GB)
copy .env.example .env                     # llenar DATABASE_URL, SECRET_KEY, ALGORITHM=HS256 (el .env NUNCA se sube)
uvicorn main:app --reload --port 8000      # documentación en http://localhost:8000/docs
```
**Frontend** (`serve.py` usa el puerto 8000 por defecto, el mismo del backend: cambiar `PORT`)
```powershell
cd C:\proyectos\PAgroIA
$env:PORT = 5500; python serve.py          # abrir http://localhost:5500/index.html
```
En local la página usa el backend en `http://localhost:8000`; en Railway usa `https://agroiabackend.up.railway.app` (se decide en `js/config.js` según `location.hostname`).

**Bot de Telegram** (webhook: necesita una URL pública, la de Railway o un túnel)
```powershell
cd C:\proyectos\AgroIA
pip install -r requirements.txt
$env:TELEGRAM_TOKEN = "..."; $env:PUBLIC_URL = "https://<dominio-publico>"; $env:GROQ_API_KEY = "..."
python bot_agroia.py
```
**Puente Sinric**
```powershell
cd C:\proyectos\AGROIA-ASISTENTE
pip install -r requirements.txt
$env:SINRIC_APP_KEY = "..."; $env:SINRIC_APP_SECRET = "..."; $env:SINRIC_DEVICE_AMBIENTE = "..."; $env:SINRIC_DEVICE_PROMEDIO = "..."
python sinric_promedio.py
```
(Los valores salen de cada proveedor; nunca se escriben en archivos del repositorio.)

### 15.3 Git y despliegue (ver también §9)
```powershell
git remote -v                 # confirmar el repositorio correcto
git pull
git status                    # solo deben aparecer los archivos que esperas
git add <archivos>
git commit -m "mensaje"
git push                      # si lo rechaza: git pull --rebase y volver a git push (NUNCA --force)
git commit --allow-empty -m "Reactivar backend"   # fuerza un despliegue nuevo en Railway
git revert HEAD               # deshace el último commit (y luego git push)
```
Un zip se copia **encima del clon** (sin su `.git`): los archivos que no cambian quedan iguales y `git status` muestra solo los modificados.

### 15.4 Comprobaciones rápidas
```powershell
Invoke-RestMethod https://agroiabackend.up.railway.app/menu/ultimo-registro
Invoke-RestMethod -Method Post -Uri https://agroiabackend.up.railway.app/esp32/comando -ContentType "application/json" -Body '{"accion":"encender_led"}'
Invoke-RestMethod https://agroiabackend.up.railway.app/esp32/comando         # el ESP32 la recoge y se limpia
```
- Lo que llega a ThingSpeak: `https://api.thingspeak.com/channels/3586784/feeds.json?results=3` (mirar `created_at` y `field4`).
- Envío de prueba al campo 4 desde el navegador (con la Write API Key **solo en el navegador**, nunca en archivos): `https://api.thingspeak.com/update?api_key=<CLAVE>&field4=450`.
- `AgroIA_Diagnostico.html` (doble clic): revisa ThingSpeak y la API y da el cuerpo exacto de cada arreglo en Swagger.

### 15.5 Entorno de pruebas del asistente (aproximado; se usaba en el sandbox)
```bash
python3 -m venv /tmp/venvtest
/tmp/venvtest/bin/pip install fastapi httpx sqlalchemy psycopg2-binary pgserver python-jose python-multipart python-dotenv requests reportlab pillow numpy google-auth pydantic uvicorn python-telegram-bot groq
npm i puppeteer-core @sparticuz/chromium     # navegador sin pantalla para probar la página
```
`pgserver` da un PostgreSQL real dentro del sandbox. **`ultralytics`/`torch` no se instalan**: se simulan con módulos falsos (`ultralytics`, `cv2`). `sinricpro` también se simula.

## 16. Pruebas: qué existía y qué hay que rehacer

**Los scripts de prueba del asistente se perdieron** cuando se reinició su entorno de trabajo (después del 28 oct). Lo que había, para poder reconstruirlo:

| Suite | Qué comprueba | Último resultado |
|---|---|---|
| Capa de datos del bot y de Sinric | API y ThingSpeak simulados, caídas, TDS solo en ThingSpeak, nombres de la base, modo `USAR_API=0` (sin llamadas a la API), reintentos del LED con 502, error real sin reintento | 23/23 |
| Bot | 64 preguntas de la lista, 43 variantes de redacción (+4 conceptuales que van a la IA), reglas de LED y del pH retirado | 97/97 y 43/43 |
| Bot: LED y faltas de ortografía | 26 formas de encender y 20 de apagar, 19 casos que no deben mover el LED, 1 729 preguntas con 1–2 errores al azar iguales a las bien escritas, preguntas ajenas sin confundirse | 11/11 (99 %) |
| Sinric | 3 dispositivos, alertas por estado, sin datos no envía, sin llamadas a la API con `USAR_API=0` | 25/25 |
| Página en navegador | iframes F1–F4, Historial con rango, aviso del campo 4, 4 tamaños, chat con 27 consultas con faltas y 16+11 formas del LED, sin errores de JS | 37/37 |
| Chat pequeño, Predicción, Historial | 28 consultas con faltas + 13 órdenes de LED mal escritas en el Inicio; formulario con TDS; columna «TDS (ppm)» | 11/11 |
| Login y Google | formulario, token, redirección | 7/7 |
| Página de diagnóstico | 3 situaciones (ESP32 caído, TDS con el sensor equivocado, todo bien) | 15/15 |
| Comportamiento con API dormida | LED con dos 502 y luego OK, aviso «despertándolo…», 6 intentos y rendición, error real sin reintento, indicador de API, Inicio sin llamadas a la API | 10/10 |
| Entendimiento de mensajes (Node) | LED 144 casos; 93 bien escritas; 99,6 % con 1 error y 99,4 % con 2 (más de 5 900 casos); 14 frases ajenas | todo OK |
| Backend con PostgreSQL real | 63 rutas = Swagger; sensor TDS (tipo 5) guarda en TDS aunque el `Parametro_Id` sea otro; pH rechazado; `NullPool` sin conexiones abiertas tras 100 consultas; `/docs`; arranque sin torch; `DB_POOL=1` | 25/25 (con mis parches de nombres) y 7/7 (zip final) |
| Menú LCD y hora de Colombia | teclas 4–7 en 4 horas del día simuladas; línea ≤ 16 caracteres; sin pH | 0 fallas |
| Otros | generación del PDF con y sin telemetría; prueba A del cargador perezoso de YOLO (8 hilos, una sola carga) | OK |

**Cómo reconstruirlas:** (1) un servidor falso que imite la API de AgroIA (`/muestras/list`, `/parametros/list`, `/menu/*`, `/esp32/comando`) **y** ThingSpeak (`feeds/last.json`, `feeds.json?results=N`, `feeds.json?days=1&average=60`), con modos (normal, API caída, ThingSpeak vacío, servidor despertando con 502); (2) probar **siempre desde los zips finales descomprimidos**, cambiando las rutas de trabajo; (3) en el navegador, interceptar las peticiones (ThingSpeak y la API) con `puppeteer-core`; (4) para el backend, PostgreSQL con `pgserver` y la aplicación completa con `TestClient` de FastAPI.

## 17. Reglas de trabajo con el usuario (acordadas en los chats)

1. **Idioma y tono:** español de Colombia, cercano y claro; respuestas concisas, con el riesgo real explicado sin dramatizar. Las órdenes para el PC son de **PowerShell de Windows**, en pasos numerados cortos.
2. **No cambiar nada fuera de lo pedido.** Si aparece algo más, **reportarlo y pedir aprobación**; el usuario aprueba con frases como «Aprobado Cambio 1» o «Aprobado alertas». Cuando dice «no hagas más cambios / déjalo como te lo pasé», solo se hace el cambio mínimo pedido.
3. **Cambios pequeños y reversibles:** mostrar el diff y decir cómo deshacer (`git revert HEAD`).
4. **El código del equipo es la base:** partir del último zip del equipo (hoy `AgroIABackend_2.zip`, commit `bbf1923`), conservar lo de Thair/Víctor y **no tocar archivos que no hacen falta**. Los archivos no modificados deben quedar **idénticos byte a byte** (comparar).
5. **Zips completos cuando los pida:** sin `.git`, sin `.env`, sin claves; con la misma carpeta raíz del original; cada zip lleva el `CONTEXTO.md` vigente.
6. **Adjuntar siempre los archivos** con la herramienta de presentar archivos (el usuario se quejó cuando solo quedaron en la carpeta) y referirse a ellos por su nombre. No dejar archivos viejos mezclados: avisar cuál es el vigente.
7. **Verificar desde el zip final descomprimido** y reportar los números reales. **Decir con claridad qué no se pudo probar** (servicios reales, YOLO real, ThingSpeak real, Railway real). Lo no verificado se marca «por confirmar».
8. **No inventar:** si no se puede comprobar, decirlo; las capturas y los logs del usuario son la fuente de verdad del estado real.
9. **Seguridad:** nunca claves en archivos, zips ni documentos; solo nombres de variables. La Write API Key de ThingSpeak solo por privado a José.
10. **Railway:** un cambio a la vez y esperar «Active»; no empujar varios commits seguidos (sobre todo durante incidentes); **no borrar servicios ni el proyecto**; cambiar claves de una en una comprobando `/docs`.
11. **Git:** seguir la §9 (trabajar en `C:\proyectos`, `git remote -v`, `git status`, nunca `--force`).
12. **Nombres oficiales** (§3): TDS en mayúsculas; el pH está retirado y no se vuelve a presentar como medida; horas en hora de Colombia.
13. **Chat y bot:** el mismo corrector de faltas de ortografía en web y bot; **un mensaje ambiguo, una pregunta o pedir otro aparato nunca mueve el LED** (regla dura); nunca decir «listo» si la orden no se envió.
14. **Mantener este documento** (§13): cada cambio sube la versión y agrega una entrada al registro; la misma copia en los 4 zips.
15. **Mensajes finales:** breves, con lo que cambió, los riesgos, lo que no se probó y el siguiente paso; como máximo **una pregunta** al final.
16. **Lo que el usuario no quiere:** archivos sin entregar, cambios no pedidos, texto largo innecesario, que se «dañe» algo que funciona. Quiere saber si algo es seguro **antes** de aplicarlo.

## 18. Futuro: ideas y trabajo previsto

**Ya decidido o casi (falta ejecutar)**
- Montar Sinric de nuevo; rotar claves; subir los zips finales; configurar el login con Google y crear el primer usuario.
- Que José cierre el firmware (TDS, ids, `/esp32/comando`, reintentos) y que el ESP32 vuelva a enviar.
- Edge Impulse (Punto 3) conectado en `CLASIFICADOR.url`; `/chat` con IA en el backend (Punto 4, opcional).
- Video de demostración y ensayo de la presentación.

**Mejoras propuestas (necesitan aprobación)**
- **Alertas de Sinric:** no avisar si la lectura tiene más de 60 min («Aprobado alertas»).
- **Backend, nombres flexibles:** reconocer el TDS y el pH **por palabra** (por ejemplo `\btds\b|solidos disueltos` y `(^|[^a-z])ph([^a-z]|$)`, también en SQL con `!~*`), de modo que «TDS del suelo» no dé 404 y «pH del suelo» se rechace; abreviar «ambiental»/«ambiente» como A en el LCD. Ya se probó una versión (25/25 en PostgreSQL), pero **no se incluyó** por pedido del usuario.
- **Seguridad de la API:** exigir token en `POST /users/create`, `/users/list`, `/users/userId` y `POST /esp32/comando` (o una clave simple para el ESP32); no devolver contraseñas; guardar contraseñas con hash (bcrypt/argon2) migrando los usuarios existentes; revisar `CORS "*"`.
- **`/muestras/list`** devuelve todas las filas: paginar o limitar; corregir la clave foránea de `historial_consultas_llm` (apunta a `"user"` en vez de `usuarios`).
- **Antes del 1 dic 2026:** decidir si se migra de *Config as Code* a *Infrastructure as Code* o se deja todo por el panel (el interruptor Serverless y el Dockerfile bastan).
- **Dormir con el WebSocket de visión:** la primera imagen bloquea el servidor mientras carga el modelo; si molesta, cargar el modelo en un hilo aparte o precalentarlo al primer `GET /docs`.

**Ideas a más largo plazo (no comprometidas)**
- Alertas proactivas por Telegram (suelo seco, TDS alto) con la misma regla de datos viejos.
- Revisar los rangos del TDS con el docente o con literatura agronómica (hoy: normal 0–1000 ppm, alerta 0–1500; vienen de la configuración heredada).
- Reentrenar el modelo YOLO con más fotos; mostrar la fertilidad estimada por el modelo de Edge Impulse en lugar de reglas.
- Exportar reportes (PDF/CSV) desde la página sin depender de InfluxDB.

## 19. Cómo arrancar el chat nuevo

1. **Sube a la conversación nueva:** este archivo (`AgroIA_CONTEXTO.md`) y, si va a tocar código, los zips que correspondan (`AgroIABackend_completo_sleep.zip`, `AgroIA_frontend_web.zip`, `AgroIA_bot_telegram.zip`, `AGROIA-ASISTENTE_sinric_sin_API.zip`). Las capturas de Railway o ThingSpeak ayudan mucho.
2. **Pega este prompt:**

> Hola. Continúo el proyecto **AgroIA** (IA 26-2, CUL). Soy Víctor y hablo español de Colombia. Adjunto `AgroIA_CONTEXTO.md` (v1.12): es toda la memoria del proyecto. **Léelo completo antes de responder** y sigue sus **reglas de trabajo (§17)**. Primero resúmeme en 10 líneas dónde estamos y qué es lo más urgente, y espera mi instrucción: **no cambies nada sin mi aprobación**. Cuando entregues archivos, adjúntalos, no incluyas claves y verifica desde el zip final descomprimido. Mantén el documento actualizado (§13).

3. **Primeras cosas que probablemente pida el usuario:** montar Sinric de nuevo, cambiar claves, subir los zips, ayudar a José con el firmware, aprobar «alertas», proteger la API, preparar la presentación.
4. **Aviso para el asistente nuevo:** no tiene acceso a la API ni a Railway del usuario; trabaja con lo que el usuario pega o con capturas. Los scripts de prueba anteriores no existen (§16).

## 20. Registro de cambios (lo más reciente arriba)

### v1.12 — 18 nov 2026 — Canal de ThingSpeak nuevo (3586784) y nuevo orden de campos
- **Cambio:** José creó un canal nuevo (**3586784**), con otra Write API Key (la clave del canal anterior, que se había expuesto, ya no sirve para este). Decisión de Víctor: usar **el orden de José**: campo 1 humedad del suelo, 2 temperatura, 3 humedad del aire, 4 TDS.
- **Frontend (zip, página 10.6):** `js/config.js` (`channelId`, `campos`), `dashboard.html` (etiquetas «Campo N»), `diagnostico.html` (canal y campos), `js/configuracion.js` (ejemplo).
- **Bot y Sinric (zips):** `datos_agroia.py` (`THINGSPEAK_CANAL` por defecto y `campo_ts`); bot: enlace del canal en `conocimiento.py`. **En Railway, la variable `THINGSPEAK_CANAL` de ambos servicios, si existe, hay que cambiarla a 3586784** (la variable manda sobre el valor del código).
- **Firmware (archivo aparte, `AgroIA_ESP32_con_ThingSpeak.ino`):** envía field1 = humedad del suelo, field2 = temperatura, field3 = humedad del aire, field4 = TDS. La Write API Key del canal nuevo se pega a mano (el archivo trae un marcador); nunca va en archivos compartidos.
- **Probado:** página en Chrome sin interfaz con datos simulados en el orden nuevo (tarjetas, etiquetas y gráficos correctos, sin errores de JavaScript); bot y Sinric con una respuesta simulada (cada valor en su variable). **No probado:** en el sitio real, ni el firmware en un ESP32 con el canal nuevo.
- **Pendiente:** el canal nuevo debe ser **público** (si no, las gráficas del tablero no cargan); renombrar los campos y los títulos de las gráficas en ThingSpeak según el orden nuevo; que el ESP32 envíe con la clave nueva.

### v1.11 — 18 nov 2026 — TDS del tablero desde la base de datos
- **Problema:** el TDS llega a la base de datos (Sensor_Id 5) pero no a ThingSpeak `field4`; el tablero solo leía ThingSpeak. Nada de lo que hay en el backend, la web, el bot o Sinric escribe en ThingSpeak (solo leen); quien lo alimenta (campos 1–3) es algo externo: otra versión del firmware o el backend viejo de Render. **Pendiente de averiguar con José.** El código de José que se revisó (MQTT + `POST /muestras/create` a Render) no tiene ThingSpeak.
- **Cambio (solo frontend, página 10.5):** nuevo `js/tds-bd.js`; `js/dashboard.js` usa la base de datos (`GET /muestras/list`, filtra Sensor_Id 5, pide como mucho 1 vez por minuto) **solo si ThingSpeak no trae el campo 4**: tarjeta con el último valor, gráfica propia y etiqueta «Campo 4 · Base de datos». Si ThingSpeak vuelve a traer TDS, regresa solo a la gráfica oficial. `js/charts.js`: opción `sinDer`.
- **Límite conocido:** `/muestras/list` devuelve **toda** la tabla; con el tiempo será pesado. Mejora futura (requiere cambiar el backend y aprobación): filtro `?sensor_id=&limite=`.
- **Probado:** Chrome sin interfaz con datos simulados (caso base de datos y caso ThingSpeak normal, sin errores de JavaScript). No probado en el sitio real.
- **Aviso de seguridad:** la Write API Key de ThingSpeak se mostró en capturas y en texto pegado en el chat: hay que **generar una nueva** (después de saber quién envía, para actualizarla allí).
- **Si el ESP32 manda a Render y no a Railway,** la pausa de recepción (v1.9) no lo frena.

### v1.10 — 18 nov 2026 — Alertas leen de ThingSpeak
- **Problema:** la página Alertas mostraba «No fue posible obtener la telemetría» porque pedía los datos a `/iot/ultima-medicion`, que necesita InfluxDB (no existe en la nube).
- **Arreglo (frontend, página 10.4):** `js/alertas.js` ahora lee los datos en vivo de ThingSpeak (igual que el tablero). Las alertas del backend no cambian. Solo el frontend; backend, bot y Sinric sin cambios de código.
- **Probado:** con datos simulados (humedad baja, temperatura alta, TDS sin dato). No probado en el sitio real.
- **Observado hoy:** el ESP32 vuelve a enviar; la BD recibe el TDS (Sensor_Id 5; primero 0, luego 99) pero ThingSpeak `field4` sigue vacío: el firmware no lo envía a ese campo (pendiente de José).

### v1.9 — 18 nov 2026 — Respaldo de la base de datos y pausa de recepción
- **Pedido de Víctor (dos ideas):** (1) botón para exportar un respaldo de la base de datos protegido con una clave maestra; (2) forma de apagar el envío de datos a la base de datos hasta que se vuelva a encender. Aprobado con «Aprobado respaldo y pausa».
- **Decisiones:** la clave vive solo en la variable `BACKUP_CLAVE` de Railway; la pausa se guarda en la base de datos (sobrevive a reinicios); pausar solo afecta a la base de datos, no a ThingSpeak ni al ESP32; lo recibido en pausa se descarta.
- **Backend (zip):** nuevos `app/core/admin_clave.py`, `app/routes/admin_routes.py`, `app/services/respaldo_service.py`, `app/crud/ajuste_sistema_crud.py`, `app/models/ajuste_sistema_model.py`; modificados `main.py` (ruta `/admin`), `app/routes/muestra_suelo_routes.py` (revisa la pausa antes de guardar) y `.env.example` (nombre de la variable, sin valor). Detalle en §4.
- **Frontend (zip):** nuevo `js/admin.js`; `pages/configuracion.html` gana la tarjeta de administración; `js/config.js` → página 10.3.
- **Verificado:** 18/18 pruebas locales con SQLite (clave ausente/mala/buena, bloqueo por intentos, pausar/activar, 202 sin guardar, la pausa sobrevive al reinicio, activar vuelve a guardar, el .zip trae un CSV por tabla y la clave no está dentro) y prueba de punta a punta en Chrome sin interfaz (estado, clave mala, pausar, descarga del respaldo, reanudar; sin errores de JavaScript y sin guardar la clave en el navegador).
- **NO se probó:** contra Neon/PostgreSQL ni en Railway (hay que probarlo tras subirlo), ni con el firmware real de José.
- **Bot y Sinric:** sin cambios de código; solo este documento.

### v1.8 — 17 nov 2026 — Modelo de Machine Learning para el Corte 3
- **Contexto:** el docente publicó la «Propuesta de aula» del Corte 3 (ver §5.1). Víctor indicó que lo de Julián y Kenny (Edge Impulse) y el poster ya están hechos; faltan el ML y el PowerPoint.
- **Frontend (zip):** nuevo `js/modelo-ml.js` (árbol de decisión entrenado con Plant-Health-Data de Kaggle); `js/prediccion.js` usa el modelo local cuando `CLASIFICADOR.url` está vacío (antes usaba reglas) y muestra la fuente en pantalla; `pages/prediccion.html` carga `modelo-ml.js`. El resto del frontend, idéntico a la v1.6.
- **Resultados:** 87,25 % (validación cruzada de 5 partes), 84,58 % (prueba 80/20, semilla 42) y matriz de confusión; ver §5.1. Entregados aparte: `entrenar_modelo.py`, `metricas.json`, `matriz_confusion.png`, `matriz_confusion_prueba_80_20.png`, `reglas_arbol.txt`, `plant_health_data.csv`.
- **Backend, bot y Sinric:** sin cambios de código; solo se actualiza este documento.
- **Estado:** el canal de ThingSpeak sigue sin recibir datos (última entrada hace 27 días el 17 nov, 854 entradas; campo 4 vacío), según captura de Víctor.
- **No verificado:** que Kaggle sea la plataforma que pide el docente; cómo se ve en producción (Railway); la demo en vivo depende del ESP32.

### v1.7 — 28 oct 2026 — Documento completo para iniciar un chat nuevo
- **Documento:** nuevas secciones §0 (resumen), §4.1 (código del equipo frente a mis parches), §14 (estado detallado), §15 (instalación, comandos y versiones), §16 (pruebas), §17 (reglas de trabajo), §18 (futuro) y §19 (prompt para el chat nuevo); el registro pasa a ser la §20. Actualizadas §1, §3, §5, §6, §7, §8 (pendientes consolidados), §10–§13.
- **Estado reflejado:** AgroIABackend en «Sleeping»; AGROIA-ASISTENTE borrado a propósito; «Railway Config File» vacío (el sleep funciona por el panel); incidente de seguridad y de compilaciones de Railway; control de costos y cómo pausar; entregables finales y archivos antiguos.
- **Código:** sin cambios respecto a la v1.6 (solo este documento). **Zips tocados:** los 4 (solo `CONTEXTO.md`).
- **Aviso:** los scripts de prueba del asistente se perdieron con el reinicio de su entorno (§16).

### v1.6 — 28 oct 2026 — Todo el ecosistema preparado para dormir
- **Backend (zip completo):** además de `railway.toml` y `yolo_service.py`, `app/core/config.py` con `NullPool` (pasó de opcional a incluido). Probado contra PostgreSQL real: 100 consultas sin dejar ninguna conexión abierta; arranca sin torch; `/docs` y 63 rutas.
- **Página:** `chatEnviarLed` reintenta con aviso «despertándolo…» si el servidor devuelve 502/503/504 o no responde; `verificarApi` espera y muestra «API despertando…» en vez de «API sin conexión» en rojo. Probado en navegador (10 comprobaciones nuevas, sin regresiones). Ya traía `railway.json` con `sleepApplication`.
- **Bot:** `datos_agroia.py` con reintentos del LED y `railway.json` con `sleepApplication: true`.
- **Sinric:** sin cambios de código; **no** se le activa Serverless (conexión permanente con Sinric Pro).
- **Hallazgos:** las pantallas Inicio/Monitoreo/Historial/Predicción/Configuración no consultan la API al abrirse; `alertas.html`/`iot.html` consultan cada 10 s (no están en el menú).

### v1.5 — 28 oct 2026 — El backend puede dormir (Serverless) sin dañar nada
- **Sinric (AGROIA-ASISTENTE):** `USAR_API=0` por defecto: lee solo ThingSpeak (último valor, 40 lecturas recientes y 24 promedios por hora) y no llama a la API de Railway. `datos_agroia.py` gana `thingspeak_series()`, `USAR_API` y reintentos en `enviar_comando()` (el servidor puede estar despertando).
- **Backend:** parche de dos archivos sobre el código del equipo: `railway.toml` (`sleepApplication = true`) y `app/services/yolo_service.py` (carga perezosa de YOLO con cerrojo). Probado: la app arranca sin importar ultralytics/torch, `/docs` responde y las 63 rutas siguen. Archivo opcional aparte: motor de BD sin conexiones en reposo.
- **Hallazgo:** el log de Railway mostraba `/muestras/list` + `/menu/promedio-24h` cada minuto: era Sinric. El ESP32 no aparece (sigue sin enviar).
- **Incidente de Railway:** el panel mostró compilaciones fallando/atascadas el 28 oct; el despliegue activo siguió sirviendo. Ver pendiente de seguridad.

### v1.4 — 26 oct 2026 — Diagnóstico de datos, nombres oficiales y estado con antigüedad
- **Hallazgo (capturas del usuario):** el tablero marca «Sin datos recientes» y su última lectura es la de las 8:04 PM de hace días; ThingSpeak no recibe nada (ni temperatura ni humedades), por eso el TDS sigue vacío. La base tiene tipos de sensor 1 humedad del suelo, 2 temperatura, 3 humedad ambiental, 4 pH, 5 TDS; el pH queda retirado y los datos del TDS deben ir con el sensor de tipo 5.
- **Frontend:** nueva `diagnostico.html`; el estado del sistema indica cuánto hace del último dato (`js/layout.js`).
- **Backend:** `menu_routes.py`: «Humedad ambiental»/«ambiente» se abrevian **A**; `ultimo-registro` ya no muestra parámetros retirados (solo los que tienen datos dentro de las 24 h previas a la muestra más reciente, así el pH viejo no aparece). Probado contra PostgreSQL real (18 comprobaciones).
- **Bot y Sinric:** sin cambios de comportamiento; se verificó que reconocen los nombres de la base («Temperatura», «Humedad ambiental», «TDS», «Sólidos disueltos totales») e ignoran el pH.
- **Documento:** nueva tabla de «Modelo de datos y nombres oficiales» (§3).

### v1.3 — 23 oct 2026 — El cuarto sensor es TDS (ya no pH) en todo el proyecto
- **Frontend (código):** el campo 4 pasa de pH a **TDS (ppm)** en la configuración (`tds:4`), las 4 tarjetas, el iframe del campo 4 (título «TDS (ppm)», eje «ppm»), Historial (columna, filtro, CSV `tds_ppm`, buscador), Predicción (el formulario pide TDS; el contrato del clasificador lleva `tds`) y el chat (entiende TDS, «sólidos disueltos», «ppm»; si preguntan por el pH explica que ya no se mide). Icono de 3 letras «TDS».
- **Chat (web y bot):** mejoras del corrector: desempate por parecido de letras («pronedio» → promedio), «todas/todos», «por hoa» → hora, «necesito agua», «humeda del aire».
- **Backend (código):** `app/routes/menu_routes.py` — hora de Colombia + los arreglos del TDS descritos en §4.
- **Bot y Sinric:** `datos_agroia.py` (compartido, idéntico en ambos) pasa a TDS (`ORDEN`, rangos 0–1000 / 1500, reconoce «TDS» por nombre); el bot responde por TDS y avisa si preguntan por el pH.
- **Hallazgo:** en ThingSpeak el campo 4 sigue sin datos aunque el gráfico ya se llama «TDS»: el ESP32 no está enviando `field4`.

### v1.2 — 23 oct 2026 — El bot de Telegram entiende faltas de ortografía y las órdenes del LED
- **Bot (código):** nuevo `nlu.py` (corrector de faltas de ortografía, mismo método que el chat web); `respuestas.py` corrige el texto antes de aplicar las reglas y atiende las órdenes del LED; `datos_agroia.py` gana `enviar_comando()` (`POST /esp32/comando`); la ayuda y `PREGUNTAS_QUE_SIEMPRE_CONTESTA.txt` incluyen el LED. Las preguntas de contar («cuántas/cuántos lecturas») aceptan ambos géneros.
- **Frontend:** `js/chat-nlu.js` (ajustes menores: «todo» entra al vocabulario y «por haora» se corrige a «hora», no a «ahora»).
- **Sinric:** sin cambios de comportamiento; recibe la misma `datos_agroia.py` que el bot (las dos copias deben ser idénticas).
- **Backend:** sin cambios.

### v1.1 — 23 oct 2026 — Chat que entiende faltas de ortografía y LED, gráficas = iframes de ThingSpeak, login
- **Frontend (código):**
  - Nuevo `js/chat-nlu.js` y `js/chat-core.js` reescrito: el chat entiende mensajes mal escritos (también «encdre led», «encer der led») y **envía las órdenes del LED** a `POST /esp32/comando`; ambiguos, preguntas y otros aparatos no envían nada; sugerencias «¿quisiste decir…?» con botones. Botones rápidos nuevos en la página del chat.
  - **Gráficas:** los 4 iframes del Inicio y del Monitoreo son idénticos a los códigos Embed F1–F4 (antes tenían el título en blanco y un parámetro extra); la humedad del suelo del Inicio ya no es un anillo propio sino el iframe F3; el Historial reemplaza su gráfico propio y las mini-líneas por iframes del rango elegido.
  - Inicio: etiqueta «Campo N · ThingSpeak» (sin títulos duplicados), nivel en las 4 tarjetas, 2 columnas hasta 1599 px; aviso cuando el campo 4 no tiene datos; «pH» ya no se escribe «ph» dentro de las frases.
  - Archivos tocados: `js/chat-nlu.js` (nuevo), `js/chat-core.js`, `js/chat.js`, `js/ts.js`, `js/dashboard.js`, `js/monitoreo.js`, `js/historial.js`, `js/ui.js`, `dashboard.html`, `pages/chat.html`, `pages/historial.html`, `css/app.css`.
- **Backend:** sin cambios de código (el login con Google ya estaba completo y se configura con variables: ver §4). Solo se agrega este documento.
- **Bot y Sinric:** sin cambios; solo se agrega este documento.
- **Hallazgos:** el canal de ThingSpeak no recibe datos desde hace 2 días y su campo 4 está vacío; el sistema original medía también TDS (ver pendientes).

### v1.0 — 19 oct 2026 — Creación del documento maestro
- Se crea `CONTEXTO.md` con todo el contexto de los 4 componentes. Zips tocados: **frontend, backend, bot, Sinric** (solo se les agrega este documento y una línea en los README).

### Historial previo ampliado (sep–oct 2026, antes de este documento)
- **Sep 2026:** documentación en PDF (`AgroIA_Documentacion_Completa`, `Documentacion_Telegram_GoogleAssistant`), taller 2 (YOLO + Roboflow + IoT: guía y explicación simple, diagrama de arquitectura), `CONTEXTO_AgroIA_actualizado.md` (contexto antiguo, reemplazado por este documento), primeras versiones de la web (`agroia_web.zip`, `agroia_frontend.zip`).
- **16–18 oct:** `AgroIA_Tablero.zip` y capturas de demostración, guías del parcial del corte 2 (general y por integrante), «Punto 2: flujo paso a paso» (PDF), entregas locales con lanzador `.bat` y `.env` (`AgroIA_local_CON_ENV.zip`, sensible), `AgroIA_railway.zip`, cambio de cámara móvil, `Para_Jose_ThingSpeak_400.txt` (diagnóstico del error 400) y `AgroIA_Que_pasarle_al_equipo.txt`.
- **19 oct:** `AgroIA_Preguntas_Bot_y_Sinric.txt`, `AgroIA_endpoints_menu.zip` y `Para_Jose_endpoints_menu.txt` (endpoints `/menu` para el LCD; el zip quedó obsoleto), parche de hora de Colombia, creación de este documento maestro (v1.0).
- **Frontend original v10.x** (ThingSpeak, 9 pantallas) → rediseño de Inicio/Monitoreo/Historial con iframes de ThingSpeak, chat con corrector, login obligatorio.

### Historial previo (resumen, 18–19 oct 2026)
- **Bot de Telegram v2** y **puente Sinric v2** (filtrado por variable, 3 dispositivos, alertas push, capa de datos liviana con respaldo en ThingSpeak, `API_URL` corregida a Railway, interruptor `SOLO_DATOS_REALES`).
- **Parche de la hora de Colombia** para `/menu` teclas 4–7 (entregado; por confirmar si se aplicó).
- **Frontend:** botón «Análisis» (YOLO) en la barra móvil, cámara trasera por defecto y botón de cambio de cámara, pestañas de InfluxDB ocultas, `railway.json` con `sleepApplication`.
- **Backend:** desplegado en Railway con Dockerfile; `/menu/*` y `/esp32/comando` en producción.
- **ThingSpeak:** canal 3540815 público; corrección del diagnóstico del error 400.
- **Git:** lección del repositorio escondido en `C:\Users\vyepez` y flujo seguro en `C:\proyectos`.
