from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("user/", include("useraccount.urls")),
    path("", include("shifts.urls")),
    path("__reload__/", include("django_browser_reload.urls")),
]
