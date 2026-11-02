/**
 * Cliente Web Pro - Consumidor de API REST con Django REST Framework y SimpleJWT
 * Evaluación Sumativa 3 (ES03) - Programación Backend
 */

// Configuración de la API REST
const API_CONFIG = {
  // Si se abre directo desde el servidor Django usa ruta relativa '', si es standalone usa localhost:8000
  getBaseUrl() {
    if (window.location.origin.includes(":8000") || window.location.origin.includes("vercel.app")) {
      return window.location.origin;
    }
    return localStorage.getItem("custom_api_base") || "http://127.0.0.1:8000";
  },
  TOKEN_KEY: "es03_access_token",
  REFRESH_KEY: "es03_refresh_token",
  OFFLINE_PRODUCTS_KEY: "es03_cache_productos",
  OFFLINE_STATS_KEY: "es03_cache_stats",
};

// Estado Global de la Aplicación
const state = {
  user: null,
  productos: [],
  ventas: [],
  stats: null,
  cart: [],
  selectedProduct3D: null,
  isOffline: !navigator.onLine,
  autoRotate3D: true,
};

// -------------------------------------------------------------
// 1. UTILIDADES Y LOGGER DE TRÁFICO HTTP (DEV INSPECTOR)
// -------------------------------------------------------------
function logHttp(method, endpoint, status, extra = "") {
  const consoleEl = document.getElementById("devLogConsole");
  if (!consoleEl) return;
  const time = new Date().toLocaleTimeString();
  const token = localStorage.getItem(API_CONFIG.TOKEN_KEY);
  const bearerSnippet = token ? `Bearer ${token.substring(0, 16)}...` : "Sin Token";
  const row = document.createElement("div");

  let colorClass = "text-emerald-400";
  if (status >= 400) colorClass = "text-rose-400 font-bold";
  else if (status >= 300) colorClass = "text-amber-400";

  row.className = colorClass;
  row.textContent = `[${time}] ${method} ${endpoint} -> ${status} | Auth: [${bearerSnippet}] ${extra}`;
  consoleEl.prepend(row);
}

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  const bg = type === "success" 
    ? "border-emerald-500/40 bg-emerald-950/90 text-emerald-300"
    : "border-rose-500/40 bg-rose-950/90 text-rose-300";

  toast.className = `glass-panel pointer-events-auto rounded-xl border p-3 text-xs shadow-xl flex items-center justify-between gap-3 transform transition duration-300 translate-y-2 opacity-0 ${bg}`;
  toast.innerHTML = `
    <div class="flex items-center gap-2">
      <span>${type === "success" ? "✓" : "⚠"}</span>
      <span>${message}</span>
    </div>
    <button class="text-slate-400 hover:text-white" onclick="this.parentElement.remove()">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  }, 10);

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatoClp(monto) {
  try {
    const val = Math.round(Number(monto || 0));
    return "$" + val.toLocaleString("es-CL");
  } catch (e) {
    return "$0";
  }
}

// -------------------------------------------------------------
// 2. CLIENTE HTTP CON INTERCEPTOR JWT (BEARER TOKEN & REFRESH)
// -------------------------------------------------------------
async function apiFetch(endpoint, options = {}) {
  const baseUrl = API_CONFIG.getBaseUrl();
  const fullUrl = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;

  options.headers = options.headers || {};
  if (!options.headers["Content-Type"] && !(options.body instanceof FormData)) {
    options.headers["Content-Type"] = "application/json";
  }

  // Inyectar cabecera Authorization: Bearer <token>
  let token = localStorage.getItem(API_CONFIG.TOKEN_KEY);
  if (token) {
    options.headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    let response = await fetch(fullUrl, options);
    logHttp(options.method || "GET", endpoint, response.status);

    // Si recibimos 401 Unauthorized y tenemos un Refresh Token, intentamos renovar
    if (response.status === 401 && localStorage.getItem(API_CONFIG.REFRESH_KEY)) {
      logHttp("POST", "/api/token/refresh/", 0, "[Auto-Refreshing Expired Token...]");
      const refreshed = await renovarToken();
      if (refreshed) {
        token = localStorage.getItem(API_CONFIG.TOKEN_KEY);
        options.headers["Authorization"] = `Bearer ${token}`;
        response = await fetch(fullUrl, options);
        logHttp(options.method || "GET", endpoint, response.status, "[Reintento con nuevo Token]");
      } else {
        cerrarSesion();
        throw new Error("Su sesión ha expirado. Inicie sesión nuevamente.");
      }
    }

    return response;
  } catch (err) {
    logHttp(options.method || "GET", endpoint, 0, `[Network Fail: ${err.message}]`);
    throw err;
  }
}

async function renovarToken() {
  const refreshToken = localStorage.getItem(API_CONFIG.REFRESH_KEY);
  if (!refreshToken) return false;

  try {
    const resp = await fetch(`${API_CONFIG.getBaseUrl()}/api/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (resp.ok) {
      const data = await resp.json();
      localStorage.setItem(API_CONFIG.TOKEN_KEY, data.access);
      actualizarEstadoAutenticacion();
      showToast("Token JWT renovado automáticamente con éxito.", "success");
      return true;
    }
  } catch (e) {
    console.error("Error al refrescar token:", e);
  }
  return false;
}

// -------------------------------------------------------------
// 3. GESTIÓN DE SESIÓN Y LOGIN JWT (POST /api/token/)
// -------------------------------------------------------------
async function iniciarSesion(username, password) {
  try {
    const resp = await fetch(`${API_CONFIG.getBaseUrl()}/api/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    logHttp("POST", "/api/token/", resp.status);

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || "Credenciales inválidas. Verifique usuario y contraseña.");
    }

    const data = await resp.json();
    localStorage.setItem(API_CONFIG.TOKEN_KEY, data.access);
    localStorage.setItem(API_CONFIG.REFRESH_KEY, data.refresh);

    showToast(`¡Bienvenido! Sesión iniciada con JWT.`, "success");
    cerrarModal("modalLogin");

    // Cargar perfil y datos protegidos
    await obtenerPerfilUsuario();
    actualizarEstadoAutenticacion();
    await cargarTodo();
  } catch (error) {
    const errBox = document.getElementById("loginErrorMsg");
    if (errBox) {
      errBox.textContent = error.message;
      errBox.classList.remove("hidden");
    }
  }
}

async function obtenerPerfilUsuario() {
  try {
    const resp = await apiFetch("/api/perfil/");
    if (resp.ok) {
      state.user = await resp.json();
      const el = document.getElementById("userProfileName");
      if (el) el.textContent = state.user.username;
    }
  } catch (e) {
    console.warn("No se pudo obtener el perfil del usuario:", e);
  }
}

function cerrarSesion() {
  localStorage.removeItem(API_CONFIG.TOKEN_KEY);
  localStorage.removeItem(API_CONFIG.REFRESH_KEY);
  state.user = null;
  actualizarEstadoAutenticacion();
  showToast("Sesión cerrada correctamente.", "success");
}

function actualizarEstadoAutenticacion() {
  const token = localStorage.getItem(API_CONFIG.TOKEN_KEY);
  const isAuth = Boolean(token);

  const banner = document.getElementById("authNoticeBanner");
  const userBar = document.getElementById("userProfileBar");
  const loginBtn = document.getElementById("btnLoginOpen");
  const kpiJwtStatus = document.getElementById("kpiJwtStatus");
  const kpiTokenPreview = document.getElementById("kpiTokenPreview");

  if (isAuth) {
    if (banner) banner.classList.add("hidden");
    if (userBar) userBar.classList.remove("hidden");
    if (loginBtn) loginBtn.classList.add("hidden");
    if (kpiJwtStatus) {
      kpiJwtStatus.textContent = "Bearer Activo";
      kpiJwtStatus.className = "text-lg font-bold font-display text-emerald-400 mt-2";
    }
    if (kpiTokenPreview) {
      kpiTokenPreview.textContent = `${token.substring(0, 24)}...`;
    }
  } else {
    if (banner) banner.classList.remove("hidden");
    if (userBar) userBar.classList.add("hidden");
    if (loginBtn) loginBtn.classList.remove("hidden");
    if (kpiJwtStatus) {
      kpiJwtStatus.textContent = "No Autenticado";
      kpiJwtStatus.className = "text-lg font-bold font-display text-rose-400 mt-2";
    }
    if (kpiTokenPreview) {
      kpiTokenPreview.textContent = "Inicie sesión con JWT";
    }
  }
}

// -------------------------------------------------------------
// 4. LIBRERÍA 3D INTERACTIVA CON THREE.JS (PRODUCT VAULT)
// -------------------------------------------------------------
let threeScene, threeCamera, threeRenderer, threeMesh;
let isDragging3D = false;
let previousMousePosition = { x: 0, y: 0 };

function initThreeJs() {
  const container = document.getElementById("threeCanvasContainer");
  if (!container) return;

  const width = container.clientWidth || 300;
  const height = container.clientHeight || 220;

  threeScene = new THREE.Scene();
  threeScene.background = new THREE.Color(0x080d1a);

  threeCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  threeCamera.position.set(0, 1.8, 4.2);
  threeCamera.lookAt(0, 0, 0);

  threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  threeRenderer.setSize(width, height);
  threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.innerHTML = "";
  container.appendChild(threeRenderer.domElement);

  // Iluminación
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  threeScene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0x6366f1, 1.5);
  dirLight.position.set(3, 5, 4);
  threeScene.add(dirLight);

  const pointLight = new THREE.PointLight(0x10b981, 1.2, 10);
  pointLight.position.set(-2, 2, 2);
  threeScene.add(pointLight);

  // Geometría Inicial (Caja de Almacén)
  crearMesh3D("cube", 0x10b981);

  // Controles de Ratón para Rotación 360° Interactiva
  const canvas = threeRenderer.domElement;
  canvas.addEventListener("mousedown", (e) => {
    isDragging3D = true;
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener("mouseup", () => {
    isDragging3D = false;
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDragging3D || !threeMesh) return;
    const deltaX = e.clientX - previousMousePosition.x;
    const deltaY = e.clientY - previousMousePosition.y;

    threeMesh.rotation.y += deltaX * 0.01;
    threeMesh.rotation.x += deltaY * 0.01;

    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  // Zoom con rueda de ratón
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    threeCamera.position.z = Math.max(2, Math.min(8, threeCamera.position.z + e.deltaY * 0.005));
  });

  // Animación Loop
  function animate() {
    requestAnimationFrame(animate);
    if (threeMesh && state.autoRotate3D && !isDragging3D) {
      threeMesh.rotation.y += 0.008;
    }
    threeRenderer.render(threeScene, threeCamera);
  }
  animate();

  // Resize listener
  window.addEventListener("resize", () => {
    if (!container || !threeCamera || !threeRenderer) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    threeCamera.aspect = w / h;
    threeCamera.updateProjectionMatrix();
    threeRenderer.setSize(w, h);
  });
}

function crearMesh3D(tipo = "cube", colorHex = 0x10b981) {
  if (threeMesh) threeScene.remove(threeMesh);

  let geom;
  if (tipo === "cylinder") {
    geom = new THREE.CylinderGeometry(0.8, 0.8, 1.6, 32);
  } else {
    geom = new THREE.BoxGeometry(1.4, 1.4, 1.4);
  }

  const mat = new THREE.MeshStandardMaterial({
    color: colorHex,
    roughness: 0.3,
    metalness: 0.6,
    wireframe: false,
  });

  threeMesh = new THREE.Mesh(geom, mat);
  threeMesh.position.y = 0.2;
  threeScene.add(threeMesh);
}

function actualizarVisor3D(producto) {
  state.selectedProduct3D = producto;
  const nameEl = document.getElementById("threeProductName");
  const stockEl = document.getElementById("threeProductStock");
  const badgeEl = document.getElementById("three3dBadge");

  if (!producto) {
    if (nameEl) nameEl.textContent = "Ninguno";
    if (stockEl) stockEl.textContent = "0 uds";
    return;
  }

  if (nameEl) nameEl.textContent = producto.nombre;
  if (stockEl) stockEl.textContent = `${producto.stock} uds`;

  let color = 0x10b981; // Verde (Óptimo)
  let badgeClass = "badge badge-optimo";
  let badgeText = "Stock Óptimo";

  if (producto.stock <= 0) {
    color = 0xf43f5e; // Rojo (Agotado)
    badgeClass = "badge badge-agotado";
    badgeText = "Agotado";
  } else if (producto.stock <= 5) {
    color = 0xf59e0b; // Ámbar (Crítico)
    badgeClass = "badge badge-critico";
    badgeText = "Stock Crítico";
  }

  if (badgeEl) {
    badgeEl.className = badgeClass;
    badgeEl.textContent = badgeText;
  }

  if (threeMesh && threeMesh.material) {
    threeMesh.material.color.setHex(color);
  }
}

// -------------------------------------------------------------
// 5. GRÁFICO INTERACTIVO CHART.JS
// -------------------------------------------------------------
let salesChartInstance = null;

function renderChart(labels = [], data = []) {
  const ctx = document.getElementById("salesChart");
  if (!ctx) return;

  if (salesChartInstance) salesChartInstance.destroy();

  salesChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.length ? labels : ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
      datasets: [
        {
          label: "Ventas Diarias ($ CLP)",
          data: data.length ? data : [0, 0, 0, 0, 0, 0, 0],
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.15)",
          borderWidth: 3,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: "#10b981",
          pointRadius: 4,
          pointHoverRadius: 7,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f172a",
          titleColor: "#94a3b8",
          bodyColor: "#f8fafc",
          borderColor: "#334155",
          borderWidth: 1,
          callbacks: {
            label: (item) => ` Facturado: ${formatoClp(item.raw)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#94a3b8", font: { size: 10 } },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#94a3b8",
            font: { size: 10 },
            callback: (val) => formatoClp(val),
          },
        },
      },
    },
  });
}

// -------------------------------------------------------------
// 6. CARGA DE DATOS: PRODUCTOS, STATS, OFFLINE PERSISTENCE
// -------------------------------------------------------------
async function cargarDashboardStats() {
  try {
    const resp = await apiFetch("/api/dashboard-stats/");
    if (!resp.ok) throw new Error("No autenticado para métricas");
    const stats = await resp.json();
    state.stats = stats;

    // Persistir offline
    localStorage.setItem(API_CONFIG.OFFLINE_STATS_KEY, JSON.stringify(stats));

    actualizarKpis(stats);
    renderChart(stats.chart_labels, stats.chart_data);
  } catch (err) {
    console.warn("Fallo al consultar stats:", err.message);
    // Recuperar caché offline
    const cached = localStorage.getItem(API_CONFIG.OFFLINE_STATS_KEY);
    if (cached) {
      const stats = JSON.parse(cached);
      actualizarKpis(stats);
      renderChart(stats.chart_labels, stats.chart_data);
      mostrarAvisoOffline();
    }
  }
}

function actualizarKpis(stats) {
  const elTotal = document.getElementById("kpiVentasTotales");
  const elHoy = document.getElementById("kpiVentasHoy");
  const elValor = document.getElementById("kpiValorInventario");
  const elCantProd = document.getElementById("kpiTotalProductos");
  const elCritico = document.getElementById("kpiStockCritico");
  const elActivos = document.getElementById("kpiProductosActivos");

  if (elTotal) elTotal.textContent = formatoClp(stats.ventas_totales_monto);
  if (elHoy) elHoy.textContent = formatoClp(stats.ventas_hoy_monto);
  if (elValor) elValor.textContent = formatoClp(stats.valor_inventario);
  if (elCantProd) elCantProd.textContent = `${stats.total_productos} ítems`;
  if (elCritico) elCritico.textContent = stats.stock_critico_count;
  if (elActivos) elActivos.textContent = stats.productos_activos;
}

async function cargarProductos() {
  const tbody = document.getElementById("tablaProductosBody");
  const posSelect = document.getElementById("posSelectProducto");

  try {
    const resp = await apiFetch("/api/productos/");
    if (!resp.ok) throw new Error("Acceso no autorizado a catálogo");
    const data = await resp.json();
    const productos = data.results ? data.results : data;

    state.productos = productos;
    // Persistir en LocalStorage para modo offline
    localStorage.setItem(API_CONFIG.OFFLINE_PRODUCTS_KEY, JSON.stringify(productos));

    renderTablaProductos(productos);
    poblarSelectPos(productos);

    if (productos.length > 0 && !state.selectedProduct3D) {
      actualizarVisor3D(productos[0]);
    }
  } catch (err) {
    console.warn("Fallo al obtener productos:", err.message);
    // Fallback Offline
    const cached = localStorage.getItem(API_CONFIG.OFFLINE_PRODUCTS_KEY);
    if (cached) {
      const productos = JSON.parse(cached);
      state.productos = productos;
      renderTablaProductos(productos);
      poblarSelectPos(productos);
      mostrarAvisoOffline();
    } else {
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="p-6 text-center text-slate-400">
              Inicia sesión con tu token JWT para visualizar y gestionar el catálogo de productos.
            </td>
          </tr>
        `;
      }
    }
  }
}

function renderTablaProductos(productos) {
  const tbody = document.getElementById("tablaProductosBody");
  if (!tbody) return;

  if (productos.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="p-6 text-center text-slate-400">
          No hay productos registrados aún. Presiona "+ Nuevo Producto" para crear uno.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = productos.map((p) => {
    let badgeClass = "badge-optimo";
    let badgeText = "Óptimo";
    if (p.stock <= 0) {
      badgeClass = "badge-agotado";
      badgeText = "Agotado";
    } else if (p.stock <= 5) {
      badgeClass = "badge-critico";
      badgeText = "Crítico";
    }

    return `
      <tr class="hover:bg-slate-800/40 transition group">
        <td class="px-5 py-3 font-mono text-slate-400">#${p.id}</td>
        <td class="px-5 py-3">
          <div class="font-bold text-white">${p.nombre}</div>
          <div class="text-[11px] text-slate-400 truncate max-w-xs">${p.descripcion || "Sin descripción"}</div>
        </td>
        <td class="px-5 py-3 text-right font-mono font-bold text-white">${formatoClp(p.precio)}</td>
        <td class="px-5 py-3 text-center">
          <span class="font-mono font-bold ${p.stock <= 5 ? "text-amber-400" : "text-emerald-400"}">${p.stock}</span>
        </td>
        <td class="px-5 py-3 text-center">
          <span class="badge ${badgeClass}">${badgeText}</span>
        </td>
        <td class="px-5 py-3 text-center">
          <button onclick="seleccionarProductoPara3D(${p.id})" class="rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 px-2 py-1 text-[11px] font-semibold transition">
            👁 Ver en 3D
          </button>
        </td>
        <td class="px-5 py-3 text-right whitespace-nowrap space-x-1">
          <button onclick="abrirAjusteStock(${p.id}, 1)" title="Sumar 1 unidad" class="rounded bg-slate-800 hover:bg-slate-700 px-2 py-1 text-emerald-400 font-mono font-bold">+</button>
          <button onclick="abrirAjusteStock(${p.id}, -1)" title="Restar 1 unidad" class="rounded bg-slate-800 hover:bg-slate-700 px-2 py-1 text-amber-400 font-mono font-bold">-</button>
          <button onclick="editarProducto(${p.id})" class="rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 px-2 py-1 text-[11px] font-semibold transition">Editar</button>
          <button onclick="eliminarProducto(${p.id})" class="rounded bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 px-2 py-1 text-[11px] font-semibold transition">Eliminar</button>
        </td>
      </tr>
    `;
  }).join("");
}

function seleccionarProductoPara3D(id) {
  const prod = state.productos.find((p) => p.id === id);
  if (prod) {
    actualizarVisor3D(prod);
    showToast(`Mostrando "${prod.nombre}" en el Visor 3D`, "success");
  }
}

// -------------------------------------------------------------
// 7. OPERACIONES CRUD DE PRODUCTOS (POST, PUT, DELETE, PATCH)
// -------------------------------------------------------------
async function guardarProducto(e) {
  e.preventDefault();
  const id = document.getElementById("prodId").value;
  const nombre = document.getElementById("prodNombre").value.trim();
  const descripcion = document.getElementById("prodDescripcion").value.trim();
  const precio = document.getElementById("prodPrecio").value;
  const stock = document.getElementById("prodStock").value;
  const activo = document.getElementById("prodActivo").checked;

  const payload = { nombre, descripcion, precio, stock: parseInt(stock, 10), activo };

  try {
    let resp;
    if (id) {
      // PUT /api/productos/{id}/
      resp = await apiFetch(`/api/productos/${id}/`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      // POST /api/productos/
      resp = await apiFetch("/api/productos/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const msg = Object.values(err).flat().join(" ") || "Error al procesar la solicitud.";
      throw new Error(msg);
    }

    showToast(id ? "Producto actualizado correctamente." : "Producto creado con éxito.", "success");
    cerrarModal("modalProducto");
    await cargarProductos();
    await cargarDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function editarProducto(id) {
  const p = state.productos.find((item) => item.id === id);
  if (!p) return;

  document.getElementById("modalProductoTitle").textContent = `Editar: ${p.nombre}`;
  document.getElementById("prodId").value = p.id;
  document.getElementById("prodNombre").value = p.nombre;
  document.getElementById("prodDescripcion").value = p.descripcion || "";
  document.getElementById("prodPrecio").value = p.precio;
  document.getElementById("prodStock").value = p.stock;
  document.getElementById("prodActivo").checked = p.activo;

  abrirModal("modalProducto");
}

async function eliminarProducto(id) {
  const p = state.productos.find((item) => item.id === id);
  if (!confirm(`¿Está seguro de eliminar "${p ? p.nombre : 'este producto'}" del inventario?`)) {
    return;
  }

  try {
    const resp = await apiFetch(`/api/productos/${id}/`, { method: "DELETE" });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "No se puede eliminar el producto porque tiene ventas asociadas.");
    }
    showToast("Producto eliminado del inventario.", "success");
    await cargarProductos();
    await cargarDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function abrirAjusteStock(id, delta) {
  try {
    const resp = await apiFetch(`/api/productos/${id}/ajustar-stock/`, {
      method: "PATCH",
      body: JSON.stringify({
        cantidad: Math.abs(delta),
        operacion: delta > 0 ? "sumar" : "restar",
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || "No se pudo ajustar el stock.");
    }

    const updated = await resp.json();
    showToast(`Stock de "${updated.nombre}" actualizado a ${updated.stock} uds.`, "success");
    await cargarProductos();
    await cargarDashboardStats();
    if (state.selectedProduct3D && state.selectedProduct3D.id === id) {
      actualizarVisor3D(updated);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -------------------------------------------------------------
// 8. TERMINAL POS - EMISIÓN DE VENTAS VÍA API (POST /api/ventas/)
// -------------------------------------------------------------
function poblarSelectPos(productos) {
  const select = document.getElementById("posSelectProducto");
  if (!select) return;

  const disponibles = productos.filter((p) => p.activo && p.stock > 0);
  if (disponibles.length === 0) {
    select.innerHTML = '<option value="">Sin productos con stock disponible</option>';
    return;
  }

  select.innerHTML = disponibles
    .map((p) => `<option value="${p.id}">${p.nombre} - ${formatoClp(p.precio)} (Disp: ${p.stock})</option>`)
    .join("");
}

function agregarItemCarrito() {
  const select = document.getElementById("posSelectProducto");
  const cantInput = document.getElementById("posInputCantidad");
  if (!select || !cantInput) return;

  const prodId = parseInt(select.value, 10);
  const cant = parseInt(cantInput.value, 10);

  if (!prodId || cant < 1) {
    showToast("Seleccione un producto y una cantidad válida.", "error");
    return;
  }

  const prod = state.productos.find((p) => p.id === prodId);
  if (!prod) return;

  if (cant > prod.stock) {
    showToast(`Stock insuficiente. Solo hay ${prod.stock} unidades de "${prod.nombre}".`, "error");
    return;
  }

  const existing = state.cart.find((item) => item.productoId === prodId);
  if (existing) {
    if (existing.cantidad + cant > prod.stock) {
      showToast(`No puedes superar el stock disponible (${prod.stock} uds).`, "error");
      return;
    }
    existing.cantidad += cant;
  } else {
    state.cart.push({
      productoId: prod.id,
      nombre: prod.nombre,
      precio: parseFloat(prod.precio),
      cantidad: cant,
    });
  }

  cantInput.value = 1;
  renderCarrito();
  showToast(`Añadido "${prod.nombre}" al carrito.`, "success");
}

function quitarItemCarrito(index) {
  state.cart.splice(index, 1);
  renderCarrito();
}

function renderCarrito() {
  const tbody = document.getElementById("posCartBody");
  const elNeto = document.getElementById("posSummaryNeto");
  const elIva = document.getElementById("posSummaryIva");
  const elTotal = document.getElementById("posSummaryTotal");

  if (!tbody) return;

  if (state.cart.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-8 text-center text-slate-500">
          El carrito está vacío. Agrega productos arriba para iniciar la venta.
        </td>
      </tr>
    `;
    if (elNeto) elNeto.textContent = "$0";
    if (elIva) elIva.textContent = "$0";
    if (elTotal) elTotal.textContent = "$0";
    return;
  }

  let total = 0;
  tbody.innerHTML = state.cart
    .map((item, idx) => {
      const sub = item.cantidad * item.precio;
      total += sub;
      return `
        <tr class="hover:bg-slate-800/30 transition">
          <td class="py-2.5 px-3 font-semibold text-white">${item.nombre}</td>
          <td class="py-2.5 px-3 text-center font-mono">${item.cantidad}</td>
          <td class="py-2.5 px-3 text-right font-mono">${formatoClp(item.precio)}</td>
          <td class="py-2.5 px-3 text-right font-mono font-bold text-emerald-400">${formatoClp(sub)}</td>
          <td class="py-2.5 px-3 text-center">
            <button onclick="quitarItemCarrito(${idx})" class="text-rose-400 hover:text-rose-300 font-bold">✕</button>
          </td>
        </tr>
      `;
    })
    .join("");

  const neto = total / 1.19;
  const iva = total - neto;

  if (elNeto) elNeto.textContent = formatoClp(neto);
  if (elIva) elIva.textContent = formatoClp(iva);
  if (elTotal) elTotal.textContent = formatoClp(total);
}

async function emitirVentaPos() {
  if (state.cart.length === 0) {
    showToast("Debe agregar al menos un ítem al carrito.", "error");
    return;
  }

  const cliente = document.getElementById("posInputCliente").value.trim() || "Consumidor Final";
  const observaciones = document.getElementById("posInputObservaciones").value.trim();

  const payload = {
    cliente,
    estado: "pagada",
    observaciones,
    detalles: state.cart.map((i) => ({
      producto: i.productoId,
      cantidad: i.cantidad,
      precio_unitario: i.precio,
    })),
  };

  try {
    const btn = document.getElementById("posBtnEmitirVenta");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>Procesando Venta...</span>`;
    }

    // POST /api/ventas/
    const resp = await apiFetch("/api/ventas/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const msg = err.detalles || err.detail || "Error al emitir la venta.";
      throw new Error(msg);
    }

    const data = await resp.json();
    showToast(`¡Venta #${data.id} (${data.folio}) emitida exitosamente!`, "success");

    // Limpiar carrito
    state.cart = [];
    document.getElementById("posInputCliente").value = "";
    document.getElementById("posInputObservaciones").value = "";
    renderCarrito();

    // Actualizar productos y stats (el stock se descontó en Supabase)
    await cargarProductos();
    await cargarDashboardStats();
    await cargarVentas();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    const btn = document.getElementById("posBtnEmitirVenta");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span>Emitir Venta vía API</span>
      `;
    }
  }
}

// -------------------------------------------------------------
// 9. HISTORIAL DE VENTAS Y ANULACIÓN (POST /api/ventas/{id}/anular/)
// -------------------------------------------------------------
async function cargarVentas() {
  const tbody = document.getElementById("tablaVentasBody");
  if (!tbody) return;

  try {
    const resp = await apiFetch("/api/ventas/");
    if (!resp.ok) throw new Error("Acceso no autorizado a ventas");
    const data = await resp.json();
    const ventas = data.results ? data.results : data;
    state.ventas = ventas;

    if (ventas.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="6" class="p-6 text-center text-slate-400">No hay ventas registradas aún.</td></tr>
      `;
      return;
    }

    tbody.innerHTML = ventas
      .map((v) => {
        let badge = "badge-pagada";
        if (v.estado === "anulada") badge = "badge-anulada";
        else if (v.estado === "pendiente") badge = "badge-pendiente";

        return `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="px-5 py-3 font-mono font-bold text-indigo-400">${v.folio}</td>
            <td class="px-5 py-3 text-slate-300">${new Date(v.fecha).toLocaleString("es-CL")}</td>
            <td class="px-5 py-3 font-medium text-white">${v.cliente || "Consumidor Final"}</td>
            <td class="px-5 py-3 text-center"><span class="badge ${badge}">${v.estado_display || v.estado}</span></td>
            <td class="px-5 py-3 text-right font-mono font-bold text-white">${formatoClp(v.total)}</td>
            <td class="px-5 py-3 text-center space-x-1">
              ${
                v.estado !== "anulada"
                  ? `<button onclick="anularVenta(${v.id})" class="rounded bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 px-2 py-1 text-[11px] font-semibold transition" title="Restaura stock a los productos">Anular Venta</button>`
                  : `<span class="text-[11px] text-slate-500">Anulada</span>`
              }
            </td>
          </tr>
        `;
      })
      .join("");
  } catch (err) {
    tbody.innerHTML = `
      <tr><td colspan="6" class="p-6 text-center text-slate-400">Inicia sesión con JWT para ver las transacciones.</td></tr>
    `;
  }
}

async function anularVenta(id) {
  if (!confirm(`¿Desea anular la venta #${id}? El stock de los productos vendidos será restaurado al inventario.`)) {
    return;
  }

  try {
    const resp = await apiFetch(`/api/ventas/${id}/anular/`, { method: "POST" });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.mensaje || "Error al anular la venta.");
    }
    const data = await resp.json();
    showToast(data.mensaje || "Venta anulada con éxito.", "success");
    await cargarVentas();
    await cargarProductos();
    await cargarDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -------------------------------------------------------------
// 10. MODO OFFLINE Y PERSISTENCIA
// -------------------------------------------------------------
function mostrarAvisoOffline() {
  const notice = document.getElementById("offlineCacheNotice");
  if (notice) notice.classList.remove("hidden");
  const badge = document.getElementById("netStatusBadge");
  const txt = document.getElementById("netStatusText");
  if (badge) {
    badge.className = "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold border border-amber-500/30 bg-amber-500/10 text-amber-400";
  }
  if (txt) txt.textContent = "Modo Offline (Caché)";
}

window.addEventListener("online", () => {
  showToast("Conexión restablecida con el servidor.", "success");
  const notice = document.getElementById("offlineCacheNotice");
  if (notice) notice.classList.add("hidden");
  const badge = document.getElementById("netStatusBadge");
  const txt = document.getElementById("netStatusText");
  if (badge) {
    badge.className = "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
  }
  if (txt) txt.textContent = "En línea";
  cargarTodo();
});

window.addEventListener("offline", () => {
  showToast("Conexión perdida. Activando modo offline.", "error");
  mostrarAvisoOffline();
});

// -------------------------------------------------------------
// 11. MODALES Y EVENT LISTENERS DE NAVEGACIÓN
// -------------------------------------------------------------
function abrirModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("hidden");
}

function cerrarModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("hidden");
}

function cambiarTab(tab) {
  const secProd = document.getElementById("sectionProductos");
  const secPos = document.getElementById("sectionPos");
  const secVentas = document.getElementById("sectionVentas");

  const btnProd = document.getElementById("tabBtnProductos");
  const btnPos = document.getElementById("tabBtnPos");
  const btnVentas = document.getElementById("tabBtnVentas");
  const actionContainer = document.getElementById("tabActionContainer");

  const activeClasses = "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20";
  const inactiveClasses = "bg-slate-800 text-slate-300 hover:bg-slate-700";

  if (tab === "productos") {
    secProd.classList.remove("hidden");
    secPos.classList.add("hidden");
    secVentas.classList.add("hidden");

    btnProd.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${activeClasses}`;
    btnPos.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    btnVentas.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    if (actionContainer) actionContainer.classList.remove("hidden");
  } else if (tab === "pos") {
    secProd.classList.add("hidden");
    secPos.classList.remove("hidden");
    secVentas.classList.add("hidden");

    btnProd.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    btnPos.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${activeClasses}`;
    btnVentas.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    if (actionContainer) actionContainer.classList.add("hidden");
  } else if (tab === "ventas") {
    secProd.classList.add("hidden");
    secPos.classList.add("hidden");
    secVentas.classList.remove("hidden");

    btnProd.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    btnPos.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${inactiveClasses}`;
    btnVentas.className = `px-4 py-2 rounded-xl text-xs font-bold transition ${activeClasses}`;
    if (actionContainer) actionContainer.classList.add("hidden");
    cargarVentas();
  }
}

// -------------------------------------------------------------
// 12. INICIALIZACIÓN
// -------------------------------------------------------------
async function cargarTodo() {
  await Promise.all([cargarProductos(), cargarDashboardStats()]);
}

document.addEventListener("DOMContentLoaded", async () => {
  initThreeJs();
  actualizarEstadoAutenticacion();

  // Tabs
  document.getElementById("tabBtnProductos")?.addEventListener("click", () => cambiarTab("productos"));
  document.getElementById("tabBtnPos")?.addEventListener("click", () => cambiarTab("pos"));
  document.getElementById("tabBtnVentas")?.addEventListener("click", () => cambiarTab("ventas"));

  // Modales
  document.getElementById("btnLoginOpen")?.addEventListener("click", () => abrirModal("modalLogin"));
  document.getElementById("btnBannerLogin")?.addEventListener("click", () => abrirModal("modalLogin"));
  document.getElementById("modalLoginClose")?.addEventListener("click", () => cerrarModal("modalLogin"));
  document.getElementById("btnLogout")?.addEventListener("click", cerrarSesion);

  document.getElementById("btnNuevoProducto")?.addEventListener("click", () => {
    document.getElementById("formProducto").reset();
    document.getElementById("prodId").value = "";
    document.getElementById("modalProductoTitle").textContent = "Nuevo Producto";
    abrirModal("modalProducto");
  });
  document.getElementById("modalProductoClose")?.addEventListener("click", () => cerrarModal("modalProducto"));
  document.getElementById("formProducto")?.addEventListener("submit", guardarProducto);

  // Formulario Login
  document.getElementById("formLogin")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const user = document.getElementById("loginUsername").value.trim();
    const pass = document.getElementById("loginPassword").value;
    await iniciarSesion(user, pass);
  });

  // Modal Ver JWT
  document.getElementById("btnVerToken")?.addEventListener("click", () => {
    const acc = localStorage.getItem(API_CONFIG.TOKEN_KEY) || "No hay Access Token";
    const ref = localStorage.getItem(API_CONFIG.REFRESH_KEY) || "No hay Refresh Token";
    document.getElementById("jwtAccessVal").value = acc;
    document.getElementById("jwtRefreshVal").value = ref;
    abrirModal("modalJwtDetails");
  });
  document.getElementById("modalJwtClose")?.addEventListener("click", () => cerrarModal("modalJwtDetails"));
  document.getElementById("btnForceRefresh")?.addEventListener("click", async () => {
    await renovarToken();
    const acc = localStorage.getItem(API_CONFIG.TOKEN_KEY) || "";
    document.getElementById("jwtAccessVal").value = acc;
  });

  // 3D Controls
  document.getElementById("btn3dCube")?.addEventListener("click", () => {
    crearMesh3D("cube", 0x10b981);
    if (state.selectedProduct3D) actualizarVisor3D(state.selectedProduct3D);
  });
  document.getElementById("btn3dCylinder")?.addEventListener("click", () => {
    crearMesh3D("cylinder", 0x6366f1);
    if (state.selectedProduct3D) actualizarVisor3D(state.selectedProduct3D);
  });
  document.getElementById("btn3dAutoRotate")?.addEventListener("click", (e) => {
    state.autoRotate3D = !state.autoRotate3D;
    e.target.textContent = state.autoRotate3D ? "Auto Rotar: ON" : "Auto Rotar: OFF";
  });

  // POS Buttons
  document.getElementById("posBtnAgregarItem")?.addEventListener("click", agregarItemCarrito);
  document.getElementById("posBtnEmitirVenta")?.addEventListener("click", emitirVentaPos);

  // Filtros de búsqueda
  document.getElementById("inputBuscarProducto")?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtrados = state.productos.filter(
      (p) => p.nombre.toLowerCase().includes(q) || (p.descripcion && p.descripcion.toLowerCase().includes(q))
    );
    renderTablaProductos(filtrados);
  });

  document.getElementById("selectFiltroStock")?.addEventListener("change", (e) => {
    const f = e.target.value;
    let res = state.productos;
    if (f === "critico") res = state.productos.filter((p) => p.stock <= 5);
    else if (f === "activos") res = state.productos.filter((p) => p.activo && p.stock > 0);
    renderTablaProductos(res);
  });

  document.getElementById("btnReloadProductos")?.addEventListener("click", cargarProductos);
  document.getElementById("btnRefreshStats")?.addEventListener("click", cargarDashboardStats);
  document.getElementById("btnReloadVentas")?.addEventListener("click", cargarVentas);
  document.getElementById("btnClearConsole")?.addEventListener("click", () => {
    const c = document.getElementById("devLogConsole");
    if (c) c.innerHTML = "<div>[System] Log reiniciado.</div>";
  });

  document.getElementById("btnClearOfflineCache")?.addEventListener("click", () => {
    localStorage.removeItem(API_CONFIG.OFFLINE_PRODUCTS_KEY);
    localStorage.removeItem(API_CONFIG.OFFLINE_STATS_KEY);
    showToast("Caché offline limpiado.", "success");
    cargarTodo();
  });

  // Config host manual si se desea
  document.getElementById("btnConfigApi")?.addEventListener("click", () => {
    const actual = API_CONFIG.getBaseUrl();
    const nuevo = prompt("Ingrese la URL base del Backend Django:", actual);
    if (nuevo !== null && nuevo.trim()) {
      localStorage.setItem("custom_api_base", nuevo.trim());
      showToast(`URL configurada a: ${nuevo.trim()}`, "success");
      location.reload();
    }
  });

  // Intento de carga inicial
  if (localStorage.getItem(API_CONFIG.TOKEN_KEY)) {
    await obtenerPerfilUsuario();
    actualizarEstadoAutenticacion();
  }
  await cargarTodo();
});

