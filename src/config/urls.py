"""URL configuration for ExamBoard API."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path(
        "api/auth/jwt/create/", TokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path("api/auth/jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/jwt/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/", include("apps.exams.urls")),
    path("api/", include("apps.health.urls")),
]
