"""
URL configuration for spilbloo_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from core.views import test_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/test/", test_api),
    path("api/accounts/", include("accounts.urls")),
    path("api/slot/", include("availability.urls")),
    path("api/plan/", include("plans.urls")),
    path("api/doctor-request/", include("doctor_requests.urls")),
    path("api/call/", include("calls.urls")),
    path("api/notification/", include("accounts.urls_notification")),
    path("api/core/", include("core.urls")),
]
