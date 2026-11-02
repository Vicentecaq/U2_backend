from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from inventario.api import (
    DashboardStatsAPIView,
    UserProfileAPIView,
    router,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inventario.urls')),
    path("api-auth/", include("rest_framework.urls")),

    # Endpoints de Autenticación SimpleJWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Endpoints complementarios de la API
    path('api/dashboard-stats/', DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
    path('api/perfil/', UserProfileAPIView.as_view(), name='api_perfil'),

    # Endpoints RESTful administrados por el Router
    path("api/", include(router.urls)),
]