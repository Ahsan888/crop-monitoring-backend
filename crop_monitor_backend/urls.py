from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

def health_check(request):
    return JsonResponse({"status": "ok", "message": "Django backend is running"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path('health/', health_check, name='health_check'),   # Add this line
    path("api/v1/", include("monitor.urls")),
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]