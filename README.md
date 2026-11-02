# 📦 Sistema de Control de Ventas e Inventario - API REST & Cliente 3D

> **Evaluación Sumativa 3 (ES03) - Programación Backend**  
> **Carrera:** Ingeniería en Informática / Analista Programador  
> **Institución:** INACAP  
> **Tecnologías:** Django 6.1.1, Django REST Framework (DRF), SimpleJWT, PostgreSQL (Supabase), Vercel Serverless, Three.js 3D, Tailwind CSS, Chart.js.

---

## 🌐 1. Enlaces del Despliegue en Producción (Cloud Vercel + Supabase)

| Recurso | URL Pública en Producción | Descripción |
| :--- | :--- | :--- |
| **🚀 Cliente Web SPA (3D + JWT)** | [https://u2-backend.vercel.app/cliente/](https://u2-backend.vercel.app/cliente/) | Cliente interactivo con Three.js 3D, Login JWT, terminal POS y persistencia offline |
| **📊 Dashboard Web Tradicional** | [https://u2-backend.vercel.app/](https://u2-backend.vercel.app/) | Panel Django tradicional (ES01 / ES02) con reportes y gráficos |
| **⚡ API REST Root (DRF)** | [https://u2-backend.vercel.app/api/](https://u2-backend.vercel.app/api/) | Navegador Browsable API de Django REST Framework |
| **🔑 Endpoint JWT (Token)** | [https://u2-backend.vercel.app/api/token/](https://u2-backend.vercel.app/api/token/) | Obtención de Bearer Access Token y Refresh Token |
| **🔄 Endpoint JWT (Refresh)** | [https://u2-backend.vercel.app/api/token/refresh/](https://u2-backend.vercel.app/api/token/refresh/) | Renovación de token de acceso sin reingresar credenciales |

---

## 🎯 2. Objetivos de la Evaluación Cumplidos (Rúbrica al 100%)

- **Configuración Oficial de DRF (3.1.1):** Integración de `djangorestframework`, configuración global en `settings.py` con paginación, filtros avanzados (`django-filter`) y routers automáticos (`DefaultRouter`).
- **Serializers y ViewSets con Lógica de Negocio (3.1.3):** Serializadores robustos para `Producto`, `Venta` y `DetalleVenta`. Validación estricta de precios y stock. Transacciones atómicas (`transaction.atomic()`) que descuentan stock al vender y lo restauran automáticamente al anular o eliminar una venta.
- **Endpoints y Rutas RESTful Claras (3.1.4):** Rutas consistentes bajo `/api/` con códigos HTTP estándar (200, 201, 204, 400, 401, 403, 404).
- **Autenticación SimpleJWT (3.1.2):** Acceso seguro mediante encabezados `Authorization: Bearer <token>`, ciclo de vida configurado (Access Token de 60 min, Refresh Token de 7 días).
- **Seguridad CORS (django-cors-headers):** `CorsMiddleware` posicionado al inicio del pipeline. Orígenes explícitamente autorizados en `CORS_ALLOWED_ORIGINS` (evitando configuraciones abiertas `CORS_ALLOW_ALL_ORIGINS = False`).
- **Cliente Web Consumidor Completo:** Aplicación SPA responsive con **Three.js** (modelado 3D interactivo según nivel de stock), **Skeletons/Loaders**, consola de tráfico HTTP en vivo, terminal POS y **Persistencia Offline** con `localStorage`.
- **Suite de Pruebas Automatizadas:** 19 tests unitarios aprobados (`python manage.py test`), scripts de cURL automatizados y colección lista para importar en Postman.

---

## 🛡️ 3. Arquitectura y Decisiones de Seguridad

```
   [ CLIENTE WEB SPA (Three.js 3D) ]  <--->  [ NATIVO / cURL / POSTMAN ]
                  │                                     │
                  └─── [ CORS: Solo Orígenes Autorizados ] ───┘
                                      │
                         [ SimpleJWT: Bearer Token ]
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
             [ /api/token/ ]                  [ /api/productos/ ]
           (Público: Login)                  [ /api/ventas/ ]
                                           (IsAuthenticated)
                                                       │
                                          [ Transacciones Atómicas ]
                                         (Descuento & Restauración)
                                                       │
                                                       ▼
                                         [ PostgreSQL (Supabase) ]
```

1. **Tokens Bearer Seguros:** Cada solicitud hacia endpoints protegidos requiere la cabecera:
   ```http
   Authorization: Bearer <access_token>
   ```
2. **Políticas de CORS Seguras:** Se especifica la lista blanca en `CORS_ALLOWED_ORIGINS` (puertos locales `3000`, `5173`, `5500`, `8000` y el dominio público de producción `u2-backend.vercel.app`), protegiendo el backend de peticiones cross-site no autorizadas.
3. **Variables de Entorno:** Credenciales de base de datos (`host`, `database`, `user`, `password`), claves de firma criptográfica (`DJANGO_SECRET_KEY`) y orígenes confiables cargados vía `python-dotenv`.
4. **Integridad de Inventario:** El inventario se actualiza mediante bloqueos de fila (`select_for_update()`) en transacciones atómicas para prevenir condiciones de carrera (Race Conditions) y ventas sin stock.

---

## 📡 4. Catálogo de Endpoints de la API REST

### A. Autenticación & Usuarios
| Método | Endpoint | Permiso | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/token/` | `AllowAny` | Envía `username` y `password`, retorna `access` y `refresh` tokens. |
| `POST` | `/api/token/refresh/` | `AllowAny` | Envía `refresh`, retorna un nuevo `access` token. |
| `POST` | `/api/token/verify/` | `AllowAny` | Valida la firma y vigencia de un token. |
| `GET` | `/api/perfil/` | `IsAuthenticated` | Devuelve información del usuario conectado (id, username, email). |

### B. Productos e Inventario
| Método | Endpoint | Permiso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/productos/` | `IsAuthenticated` | Lista de productos paginada. Admite `?search=` y filtros de stock. |
| `POST` | `/api/productos/` | `IsAuthenticated` | Crea un producto en el catálogo. |
| `GET` | `/api/productos/{id}/` | `IsAuthenticated` | Consulta el detalle de un producto específico. |
| `PUT` | `/api/productos/{id}/` | `IsAuthenticated` | Actualiza todos los campos de un producto. |
| `PATCH`| `/api/productos/{id}/` | `IsAuthenticated` | Actualización parcial de un producto. |
| `DELETE`| `/api/productos/{id}/` | `IsAuthenticated` | Elimina un producto (bloqueado si tiene ventas registradas). |
| `GET` | `/api/productos/stock-critico/` | `IsAuthenticated` | Devuelve únicamente productos con stock &le; 5 unidades. |
| `GET` | `/api/productos/activos/` | `IsAuthenticated` | Devuelve productos activos con stock disponible (> 0). |
| `PATCH`| `/api/productos/{id}/ajustar-stock/` | `IsAuthenticated` | Ajusta existencias en 1 clic: `{"cantidad": 5, "operacion": "sumar"}`. |

### C. Ventas y Transacciones
| Método | Endpoint | Permiso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/ventas/` | `IsAuthenticated` | Lista de ventas con folios, clientes y totales. |
| `POST` | `/api/ventas/` | `IsAuthenticated` | Emite una nueva venta y **descuenta stock automáticamente**. |
| `GET` | `/api/ventas/{id}/` | `IsAuthenticated` | Detalle de una venta con sus líneas de productos. |
| `DELETE`| `/api/ventas/{id}/` | `IsAuthenticated` | Elimina la venta y **restaura el stock al inventario**. |
| `POST` | `/api/ventas/{id}/anular/` | `IsAuthenticated` | Anula la venta y **restaura el stock al inventario**. |
| `GET` | `/api/ventas/resumen/` | `IsAuthenticated` | Total recaudado, ventas de hoy y transacciones por estado. |
| `GET` | `/api/dashboard-stats/` | `IsAuthenticated` | Métricas generales y serie de datos de los últimos 7 días. |

---

## 💻 5. Ejemplos de Peticiones y Respuestas JSON

### 1. Obtener Token JWT (`POST /api/token/`)
**Request Payload:**
```json
{
  "username": "vicente",
  "password": "tu_password"
}
```
**Response (200 OK):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Crear Venta vía API (`POST /api/ventas/`)
**Headers:** `Authorization: Bearer <access_token>`  
**Request Payload:**
```json
{
  "cliente": "Empresa Distribuidora SpA",
  "estado": "pagada",
  "observaciones": "Entrega por encomienda rápida",
  "detalles": [
    {
      "producto": 1,
      "cantidad": 3
    }
  ]
}
```
**Response (201 Created):**
```json
{
  "id": 5,
  "folio": "VNT-00005",
  "cliente": "Empresa Distribuidora SpA",
  "fecha": "2026-11-02 18:45:10",
  "estado": "pagada",
  "estado_display": "Pagada",
  "observaciones": "Entrega por encomienda rápida",
  "total": "135000.00",
  "total_formateado": "$135.000",
  "detalles": [
    {
      "id": 8,
      "venta": 5,
      "producto": 1,
      "producto_nombre": "Teclado Mecánico RGB",
      "cantidad": 3,
      "precio_unitario": "45000.00",
      "subtotal": "135000.00"
    }
  ]
}
```

---

## 🎨 6. Cliente Web SPA (Librerías y Capacidades UI/UX)

La aplicación cliente se encuentra en la carpeta `cliente/` (y también disponible en `/cliente/` en Django):
1. **Three.js 3D:** Renderiza un contenedor 3D interactivo donde los productos se visualizan tridimensionalmente. Al hacer clic en un producto, el modelo rota 360°, se puede manipular con el cursor y cambia de color según el nivel de stock (verde = óptimo, naranja = crítico, rojo = agotado).
2. **Chart.js:** Gráfico dinámico de las ventas de los últimos 7 días obtenido de la API.
3. **Persistencia Offline:** Almacena el catálogo y las métricas en `localStorage`. Si se pierde la conectividad a internet, la aplicación pasa a modo offline mostrando los datos en caché con un indicador visual.
4. **Terminal de Facturación POS:** Permite armar un carrito de ventas en vivo, validando el stock antes del envío y ejecutando la compra con un solo clic.
5. **Consola de Tráfico en Tiempo Real:** Registra cada solicitud HTTP, mostrando la cabecera `Authorization: Bearer eyJ...` y los códigos de respuesta del servidor.

---

## 🚀 7. Instrucciones para Ejecución Local

### Paso 1: Clonar el repositorio y crear entorno virtual
```bash
git clone https://github.com/Vicentecaq/U2_backend.git
cd U2_backend
python -m venv .venv

# Activar en Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# O en CMD:
.\.venv\Scripts\activate.bat
```

### Paso 2: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 3: Configurar variables de entorno
Crea tu archivo `.env` tomando como base `.env.example`:
```env
DJANGO_SECRET_KEY=clave-secreta-de-desarrollo
DJANGO_DEBUG=True
host=aws-0-us-east-1.pooler.supabase.com
port=5432
database=postgres
user=postgres.tu-usuario
password=tu-contraseña
```

### Paso 4: Ejecutar el servidor Django
```bash
python manage.py runserver
```

Abre en tu navegador:
- Dashboard Tradicional: `http://127.0.0.1:8000/`
- Cliente SPA Web: `http://127.0.0.1:8000/cliente/`

---

## 🧪 8. Colección de Pruebas Automatizadas

### A. Tests Unitarios Django (19 tests)
Para correr la suite completa de pruebas automatizadas:
```bash
python manage.py test
```
*Salida esperada:*
```text
Ran 19 tests in 83.753s
OK
```

### B. Scripts de Prueba cURL
- En Windows: ejecuta `scripts\probar_api.bat`
- En Linux / Mac / Git Bash: ejecuta `bash scripts/probar_api.sh`

### C. Importar en Postman
Importa el archivo `scripts/postman_collection.json` en Postman o Thunder Client para probar de manera gráfica todos los endpoints protegidos con JWT.

---

## ☁️ 9. Despliegue en la Nube (Vercel + Supabase)

El proyecto cuenta con `vercel.json` y `api/index.py` listos para despliegue serverless:
1. Conectar el repositorio de GitHub con **Vercel**.
2. En la configuración del proyecto en Vercel (*Settings -> Environment Variables*), configurar las variables:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG` = `False`
   - `host`, `port`, `database`, `user`, `password` (credenciales de Supabase)
   - `DJANGO_ALLOWED_HOSTS` = `.vercel.app,localhost,127.0.0.1`
   - `CSRF_TRUSTED_ORIGINS` = `https://u2-backend.vercel.app,https://*.vercel.app`
3. Al hacer `git push origin main`, Vercel despliega automáticamente la versión actualizada.

