# Aplicación Cliente Web (SPA) - Consumidor de API REST con DRF y SimpleJWT

> **Evaluación Sumativa 3 (ES03) - Programación Backend**  
> **Institución:** INACAP  
> **Tecnologías:** HTML5, Tailwind CSS, JavaScript Moderno (ES6+), Three.js (3D), Chart.js, LocalStorage (Persistencia Offline).

---

## 1. ¿Qué problema resuelve esta aplicación?

En las unidades anteriores (ES01 y ES02), la gestión de inventario y ventas dependía exclusivamente de vistas Django renderizadas en el servidor (SSR).

Este **Cliente Web SPA** desacoplado resuelve las siguientes necesidades de negocio:
1. **Consumo Desacoplado y Móvil:** Permite a clientes web, móviles o terminales de punto de venta (POS) interactuar con el backend mediante servicios web estándar (RESTful API) en formato JSON.
2. **Seguridad y Acceso Basado en Tokens:** Utiliza el estándar de la industria **JWT (JSON Web Token)** con el esquema `Bearer Token` y `Authorization Headers`, garantizando que únicamente usuarios autenticados con roles válidos puedan modificar productos o emitir ventas.
3. **Experiencia de Usuario Interactiva y Rica (UI/UX):**
   - **Visualización 3D con Three.js:** Modela dinámicamente un rack/caja de producto en 3D en tiempo real con rotación 360°, iluminación y alertas de color según el estado del stock (verde = óptimo, naranja = crítico &le; 5 uds, rojo = agotado).
   - **Loaders y Skeletons:** Animaciones fluidas mientras los datos se sincronizan con la base de datos Supabase en la nube.
   - **Persistencia de Datos Offline:** Almacenamiento en caché con `localStorage` que permite consultar el catálogo de productos y estadísticas incluso cuando se interrumpe la conexión a internet.
   - **Terminal de Punto de Venta (POS):** Carrito de compras interactivo que emite ventas en tiempo real contra `POST /api/ventas/` con descuento y restauración atómica de stock en PostgreSQL Supabase.

---

## 2. ¿Cómo consume la API REST?

| Acción | Método HTTP | Endpoint de la API | Autenticación | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| **Obtener Token** | `POST` | `/api/token/` | Pública | Envía `username` y `password`, recibe `access` (60 min) y `refresh` (7 días). |
| **Refrescar Token** | `POST` | `/api/token/refresh/` | Pública | Envía `refresh` para renovar el `access` token automáticamente si expira. |
| **Perfil Usuario** | `GET` | `/api/perfil/` | `Bearer <token>` | Obtiene los datos del usuario autenticado actual. |
| **KPIs Dashboard** | `GET` | `/api/dashboard-stats/` | `Bearer <token>` | Métricas de ventas, stock crítico, valor de inventario y gráfico de 7 días. |
| **Listar Productos** | `GET` | `/api/productos/` | `Bearer <token>` | Catálogo completo con paginación, búsqueda (`?search=`) y filtros. |
| **Crear Producto** | `POST` | `/api/productos/` | `Bearer <token>` | Registra un nuevo producto con validación de precio y stock. |
| **Editar Producto** | `PUT` | `/api/productos/{id}/` | `Bearer <token>` | Actualiza la información técnica de un producto. |
| **Ajustar Stock** | `PATCH` | `/api/productos/{id}/ajustar-stock/` | `Bearer <token>` | Suma, resta o fija unidades en inventario en 1 clic. |
| **Eliminar Producto** | `DELETE` | `/api/productos/{id}/` | `Bearer <token>` | Elimina un producto no asociado a ventas históricas. |
| **Emitir Venta (POS)**| `POST` | `/api/ventas/` | `Bearer <token>` | Transacción atómica: crea la venta y descuenta el stock en Supabase. |
| **Listar Ventas** | `GET` | `/api/ventas/` | `Bearer <token>` | Historial con folios, clientes y totales facturados. |
| **Anular Venta** | `POST` | `/api/ventas/{id}/anular/` | `Bearer <token>` | Anula la venta y **restaura automáticamente las unidades al stock**. |

---

## 3. Instrucciones de Ejecución

Existen dos maneras muy sencillas de utilizar este cliente:

### Opción A: Directamente desde el Servidor Django (Recomendada)
El cliente web está integrado dentro del proyecto Django y se sirve en la URL:
```text
http://127.0.0.1:8000/cliente/
```
*(O en el despliegue público en la nube: `https://u2-backend.vercel.app/cliente/`)*

### Opción B: Ejecución Standalone (Servidor Web Desacoplado)
Dado que el Backend tiene configurado **CORS** con `django-cors-headers`, puedes servir los archivos de la carpeta `cliente/` en cualquier puerto local (ej: puerto 3000, 5500 o 5173):

1. **Con Python:**
   ```bash
   cd cliente
   python -m http.server 3000
   ```
2. **Con Node / NPX:**
   ```bash
   npx serve cliente -p 3000
   ```
3. Abre tu navegador en:
   ```text
   http://localhost:3000
   ```
4. Presiona el botón superior **"Iniciar Sesión JWT"**:
   - **Usuario:** `vicente` (o cualquier usuario registrado en Django)
   - **Contraseña:** *(la contraseña del usuario)*
5. ¡Listo! Verás la consola de tráfico HTTP en tiempo real, el modelo 3D en Three.js rotando y podrás realizar operaciones CRUD completas.

