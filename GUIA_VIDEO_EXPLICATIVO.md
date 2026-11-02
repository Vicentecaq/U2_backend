# 🎬 Guion Paso a Paso para el Video Explicativo (Evaluación Sumativa 3)

> **Criterio Rúbrica:** *Presenta un video explicativo claro, que demuestra el flujo end-to-end y las decisiones de diseño/seguridad* (6 puntos).  
> **Duración sugerida:** Entre 5 y 8 minutos.  
> **Objetivo:** Demostrar ante el docente evaluador el 100% de los requisitos técnicos, de seguridad y funcionales solicitados.

---

## 📋 Checklist Previo a la Grabación

Antes de iniciar la grabación con OBS Studio, Loom o software similar, asegúrate de tener abiertas las siguientes pestañas en tu navegador:
1. **Pestaña 1:** `http://127.0.0.1:8000/` (Dashboard tradicional Django).
2. **Pestaña 2:** `http://127.0.0.1:8000/cliente/` (Cliente Web SPA 3D con Three.js).
3. **Pestaña 3:** `https://u2-backend.vercel.app/` y `https://u2-backend.vercel.app/cliente/` (Demostración en la nube operativa).
4. **Editor de Código (VS Code):** Archivos `settings.py`, `serializers.py`, `api.py` y `urls.py`.
5. **Terminal / Consola:** Lista para ejecutar `python manage.py test` o el script de pruebas cURL.

---

## ⏱️ Estructura del Video Minuto a Minuto

### 🕒 Minuto 0:00 - 0:45 | Introducción y Presentación del Proyecto
- **Qué mostrar:** Pantalla inicial con el `README.md` y el Dashboard del sistema.
- **Qué decir:**
  > "Buenas tardes profesor/a. En esta presentación de la Evaluación Sumativa 3 de Programación Backend, demostraremos la evolución de nuestro sistema comercial e inventario hacia una arquitectura moderna basada en API RESTful utilizando Django REST Framework, autenticación con SimpleJWT, configuración estricta de CORS y un cliente web interactivo con visualización 3D en Three.js y persistencia offline. Mi nombre es [Tu Nombre] y [Nombre de tu compañero/a]."

---

### 🕒 Minuto 0:45 - 2:00 | Arquitectura Backend y Decisiones de Seguridad
- **Qué mostrar en VS Code:**
  1. `core/settings.py` (mostrar `REST_FRAMEWORK`, `SIMPLE_JWT` y `CORS_ALLOWED_ORIGINS`).
  2. `inventario/serializers.py` (mostrar validaciones y transacciones).
  3. `inventario/api.py` (mostrar `ProductoViewSet` y `VentaViewSet`).
- **Qué decir:**
  > "En el backend, configuramos Django REST Framework siguiendo las mejores prácticas:
  > 1. **Autenticación SimpleJWT:** Definimos `JWTAuthentication` como clase por defecto y protegemos globalmente los endpoints con `IsAuthenticated`.
  > 2. **CORS Seguro:** Instalamos `django-cors-headers` y colocamos `CorsMiddleware` en la parte superior del pipeline. Cumpliendo estrictamente la rúbrica, no utilizamos `CORS_ALLOW_ALL_ORIGINS = True`, sino que restringimos explícitamente los orígenes del cliente en `CORS_ALLOWED_ORIGINS`.
  > 3. **Lógica de Dominio:** En `serializers.py` y `api.py`, implementamos transacciones atómicas (`transaction.atomic()`). Al registrar una venta vía API REST, se valida la existencia, el estado activo y que haya stock disponible; si se cumplen, el stock se descuenta en la base de datos PostgreSQL en Supabase. Si una venta se anula o elimina, las unidades se restauran automáticamente al inventario."

---

### 🕒 Minuto 2:00 - 3:30 | Demostración de Endpoints y Seguridad (Postman o cURL)
- **Qué mostrar:** Terminal o Postman ejecutando peticiones contra la API.
- **Qué hacer:**
  1. Ejecuta una petición GET a `http://127.0.0.1:8000/api/productos/` **SIN TOKEN**.
     - *Muestra que el servidor responde con `HTTP 401 Unauthorized`*.
     - *Explica:* "Como se aprecia, sin el token Bearer, el acceso es denegado conforme a nuestras políticas de seguridad."
  2. Ejecuta `POST /api/token/` con tus credenciales (`vicente` / tu contraseña).
     - *Muestra que la API retorna `access` y `refresh`*.
  3. Ejecuta la misma petición GET a `/api/productos/` agregando el encabezado:
     - `Authorization: Bearer <access_token>`
     - *Muestra que ahora responde `HTTP 200 OK` con la lista en formato JSON*.
  4. Ejecuta el script automatizado en la terminal:
     ```bash
     .\scripts\probar_api.bat
     ```
     o
     ```bash
     python manage.py test
     ```
     - *Muestra que los 19 tests pasan en `OK`*.

---

### 🕒 Minuto 3:30 - 5:30 | Demostración del Cliente Web SPA (Three.js 3D & POS)
- **Qué mostrar:** La página `http://127.0.0.1:8000/cliente/` (o standalone).
- **Qué hacer en pantalla:**
  1. **Inicio de Sesión JWT:**
     - Haz clic en **"Iniciar Sesión JWT"**, ingresa tu usuario y contraseña.
     - Muestra cómo cambia el estado a **"Bearer Activo"** y cómo la consola en vivo ("Live API Traffic Inspector") registra la llamada `POST /api/token/ -> 200`.
     - Haz clic en **"Ver JWT"** para mostrar el Access Token y el botón de refresco.
  2. **Visualizador 3D interactivo con Three.js:**
     - Muestra el visor 3D en pantalla. Arrastra con el ratón para rotar el producto 360° y usa la rueda para hacer zoom.
     - Haz clic en **"👁 Ver en 3D"** en un producto con stock óptimo (se verá verde).
     - Luego haz clic en un producto con stock crítico (se verá ámbar/rojo con alerta).
     - Explica: *"Incorporamos Three.js para modelar los productos en 3D y dar retroalimentación visual al encargado de bodega según el stock en tiempo real."*
  3. **Terminal de Venta Rápida (POS):**
     - Ve a la pestaña **"Terminal de Venta Rápida (POS)"**.
     - Selecciona un producto, añade cantidad al carrito y presiona **"Emitir Venta vía API"**.
     - Muestra el toast de confirmación y cómo la consola registra `POST /api/ventas/ -> 201 Created`.
     - Vuelve a la tabla de productos: ¡el stock disminuyó automáticamente!
  4. **Persistencia Offline:**
     - En las DevTools de tu navegador (F12 -> Network), cambia a **"Offline"** o desconecta el WiFi un segundo.
     - Recarga o navega: muestra el aviso amarillo *"Modo Offline (Caché local en localStorage)"*. Explica que los datos se persisten localmente para asegurar continuidad operativa.

---

### 🕒 Minuto 5:30 - 6:30 | Demostración en la Nube (Vercel + Supabase)
- **Qué mostrar:** La URL pública `https://u2-backend.vercel.app/` y `https://u2-backend.vercel.app/cliente/`.
- **Qué decir:**
  > "Para finalizar, demostramos que el despliegue en la nube sigue operativo al 100%:
  > La aplicación backend está desplegada en Vercel Serverless conectada a la base de datos PostgreSQL alojada en Supabase AWS.
  > Tanto la vista Django tradicional como la API REST y el nuevo cliente SPA funcionan perfectamente en la URL pública mostrada en nuestro README."

---

### 🕒 Minuto 6:30 - 7:00 | Conclusiones y Cierre
- **Qué decir:**
  > "En resumen, hemos cumplido con todos y cada uno de los indicadores de la rúbrica: configuración de DRF, autenticación JWT con SimpleJWT, protección de endpoints, CORS seguro, cliente web enriquecido con Three.js y persistencia offline, suite de pruebas automatizadas y despliegue público en la nube. Muchas gracias por su atención."

---

## 🏆 Consejos Clave para Obtener los 6 Puntos Completos

- **Audio claro:** Graba en un ambiente silencioso con micrófono nítido.
- **Resolución:** Graba a 1080p (Full HD) para que el código y los estados HTTP de la consola se lean con total claridad.
- **Seguridad primero:** Resalta explícitamente que la API responde **401 Unauthorized** cuando no hay token, y **200 OK** cuando se envía la cabecera `Authorization: Bearer <token>`. Este punto es verificado minuciosamente en la rúbrica.

