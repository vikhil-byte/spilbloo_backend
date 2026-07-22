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
from django.http import HttpResponse
from accounts.views import LogoutView, CardDeleteView, UserImageView

def robots_txt(request):
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /api/\nSitemap: https://spilbloo.com/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain")

def sitemap_xml(request):
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://spilbloo.com/</loc>
    <priority>1.00</priority>
  </url>
  <url>
    <loc>https://spilbloo.com/careers</loc>
    <priority>0.80</priority>
  </url>
  <url>
    <loc>https://spilbloo.com/resources</loc>
    <priority>0.80</priority>
  </url>
  <url>
    <loc>https://spilbloo.com/privacy-policy</loc>
    <priority>0.50</priority>
  </url>
  <url>
    <loc>https://spilbloo.com/terms-of-use</loc>
    <priority>0.50</priority>
  </url>
</urlset>"""
    return HttpResponse(content, content_type="application/xml")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap_xml),
    path("user/image/<int:pk>", UserImageView.as_view(), name="user_image"),

    # iOS legacy compatibility alias (historical typo in client path).
    path("api/users/logout/", LogoutView.as_view()),
    # iOS legacy compatibility alias.
    path("api/transactions/card-delete/", CardDeleteView.as_view()),
    path("api/user/", include("accounts.urls")),
    path("api/slot/", include("availability.urls")),
    path("api/plan/", include("plans.urls")),
    path("api/doctor-request/", include("doctor_requests.urls")),
    path("api/call/", include("calls.urls")),
    path("api/notification/", include("accounts.urls_notification")),
    path("node/", include("core.urls_node")),
    path("api/core/", include("core.urls")),
]
