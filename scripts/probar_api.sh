#!/usr/bin/env bash
# =====================================================================
#    PRUEBAS AUTOMATIZADAS DE API REST - EVALUACIÓN SUMATIVA 3 (ES03)
# =====================================================================

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
USERNAME="${USERNAME:-vicente}"
PASSWORD="${PASSWORD:-Vicecq2901.}"

echo "====================================================================="
echo "   Colección de Pruebas de Endpoints cURL (Con y Sin Autenticación)"
echo "   URL Base: $BASE_URL"
echo "====================================================================="
echo ""

echo "[1] Probando acceso a endpoint protegido SIN TOKEN (Esperado: 401 Unauthorized)..."
STATUS_SIN_TOKEN=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/productos/")
echo "    -> HTTP Status: $STATUS_SIN_TOKEN"

echo ""
echo "[2] Obteniendo Token JWT vía POST /api/token/..."
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/token/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access":"[^"]*' | cut -d'"' -f4)
REFRESH_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"refresh":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "    ERROR: No se pudo obtener el token. Respuesta del servidor:"
  echo "$AUTH_RESPONSE"
  exit 1
fi

echo "    -> Access Token: ${ACCESS_TOKEN:0:32}..."
echo "    -> Refresh Token: ${REFRESH_TOKEN:0:32}..."

echo ""
echo "[3] Probando acceso a endpoint protegido CON BEARER TOKEN (Esperado: 200 OK)..."
STATUS_CON_TOKEN=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE_URL/api/productos/")
echo "    -> HTTP Status: $STATUS_CON_TOKEN"

echo ""
echo "[4] Consultando perfil de usuario (GET /api/perfil/)..."
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/api/perfil/"
echo ""

echo ""
echo "[5] Consultando métricas del dashboard (GET /api/dashboard-stats/)..."
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/api/dashboard-stats/"
echo ""

echo ""
echo "[6] Creando producto de prueba (POST /api/productos/)..."
NUEVO_PROD=$(curl -s -X POST "$BASE_URL/api/productos/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Teclado Mecánico cURL Test","descripcion":"Switch Brown","precio":"59990.00","stock":15,"activo":true}')
echo "$NUEVO_PROD"
PROD_ID=$(echo "$NUEVO_PROD" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -n "$PROD_ID" ]; then
  echo ""
  echo "[7] Emitiendo venta de prueba vía API REST (POST /api/ventas/)..."
  curl -s -X POST "$BASE_URL/api/ventas/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"cliente\":\"Cliente cURL\",\"estado\":\"pagada\",\"detalles\":[{\"producto\":$PROD_ID,\"cantidad\":2}]}"
  echo ""
fi

echo ""
echo "[8] Probando refresco de token (POST /api/token/refresh/)..."
curl -s -X POST "$BASE_URL/api/token/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}"
echo ""

echo ""
echo "[9] Verificando cabeceras CORS con OPTIONS preflight..."
curl -s -I -X OPTIONS "$BASE_URL/api/productos/" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" | grep -i "access-control"

echo ""
echo "====================================================================="
echo "   Colección de pruebas cURL finalizada con éxito."
echo "====================================================================="

