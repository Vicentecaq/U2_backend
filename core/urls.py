from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from inventario.api import router

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inventario.urls')),
    path("api-auth/", include("rest_framework.urls")),
    
    path("api/", include(router.urls)),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]