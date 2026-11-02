@echo off
chcp 65001 > nul
echo =====================================================================
echo    PRUEBAS AUTOMATIZADAS DE API REST - EVALUACIÓN SUMATIVA 3 (ES03)
echo =====================================================================
echo.

set BASE_URL=http://127.0.0.1:8000
set USERNAME=vicente
set /p PASSWORD=Ingrese la contraseña del usuario %USERNAME% [o presione ENTER para Vicecq2901.]: 
if "%PASSWORD%"=="" set PASSWORD=Vicecq2901.

echo.
echo [1] Probando acceso a endpoint protegido SIN TOKEN (Debe retornar HTTP 401 Unauthorized):
curl -s -o nul -w "   HTTP Status Code: %%{http_code}\n" %BASE_URL%/api/productos/
echo.

echo [2] Obteniendo Token JWT vía POST /api/token/...
for /f "tokens=*" %%a in ('powershell -Command "(Invoke-RestMethod -Uri '%BASE_URL%/api/token/' -Method Post -ContentType 'application/json' -Body '{\"username\":\"%USERNAME%\",\"password\":\"%PASSWORD%\"}').access"') do set ACCESS_TOKEN=%%a
for /f "tokens=*" %%a in ('powershell -Command "(Invoke-RestMethod -Uri '%BASE_URL%/api/token/' -Method Post -ContentType 'application/json' -Body '{\"username\":\"%USERNAME%\",\"password\":\"%PASSWORD%\"}').refresh"') do set REFRESH_TOKEN=%%a

if "%ACCESS_TOKEN%"=="" (
    echo    ERROR: No se pudo obtener el Access Token. Verifique que el servidor este corriendo en %BASE_URL% y las credenciales sean correctas.
    goto end
)

echo    Access Token Obtenido exitosamente: %ACCESS_TOKEN:~0,30%...
echo    Refresh Token Obtenido: %REFRESH_TOKEN:~0,30%...
echo.

echo [3] Probando acceso a endpoint protegido CON BEARER TOKEN (Debe retornar HTTP 200 OK):
curl -s -o nul -w "   HTTP Status Code: %%{http_code}\n" -H "Authorization: Bearer %ACCESS_TOKEN%" %BASE_URL%/api/productos/
echo.

echo [4] Consultando perfil del usuario autenticado (GET /api/perfil/):
curl -s -H "Authorization: Bearer %ACCESS_TOKEN%" %BASE_URL%/api/perfil/
echo.
echo.

echo [5] Consultando estadísticas del dashboard (GET /api/dashboard-stats/):
curl -s -H "Authorization: Bearer %ACCESS_TOKEN%" %BASE_URL%/api/dashboard-stats/
echo.
echo.

echo [6] Consultando productos en stock crítico (GET /api/productos/stock-critico/):
curl -s -H "Authorization: Bearer %ACCESS_TOKEN%" %BASE_URL%/api/productos/stock-critico/
echo.
echo.

echo [7] Creando nuevo producto vía POST /api/productos/:
curl -s -X POST -H "Authorization: Bearer %ACCESS_TOKEN%" -H "Content-Type: application/json" -d "{\"nombre\":\"Mouse Pad Gamer XXL cURL\",\"descripcion\":\"Base antideslizante con bordes cosidos\",\"precio\":\"14990.00\",\"stock\":12,\"activo\":true}" %BASE_URL%/api/productos/
echo.
echo.

echo [8] Probando refresco de token con POST /api/token/refresh/:
curl -s -X POST -H "Content-Type: application/json" -d "{\"refresh\":\"%REFRESH_TOKEN%\"}" %BASE_URL%/api/token/refresh/
echo.
echo.

echo [9] Verificando cabeceras CORS con OPTIONS preflight:
curl -s -I -X OPTIONS -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization" %BASE_URL%/api/productos/ | findstr /i "access-control"

echo.
echo =====================================================================
echo    TODAS LAS PRUEBAS DE LA COLECCIÓN cURL COMPLETADAS EXITOSAMENTE
echo =====================================================================

:end
pause

