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
    host = request.get_host().lower()
    if 'dev.' in host or 'staging' in host:
        response = HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /api/\nSitemap: https://spilbloo.com/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain")

def sitemap_xml(request):
    try:
        import os
        sitemap_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "spilbloo-site", "public", "sitemap.xml")
        if os.path.exists(sitemap_path):
            with open(sitemap_path, "r", encoding="utf-8") as f:
                return HttpResponse(f.read(), content_type="application/xml")
    except Exception:
        pass
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.spilbloo.com/</loc><lastmod>2026-08-08</lastmod><priority>1.0</priority></url>
  <url><loc>https://www.spilbloo.com/therapists</loc><lastmod>2026-08-08</lastmod><priority>0.95</priority></url>
  <url><loc>https://www.spilbloo.com/blog</loc><lastmod>2026-08-08</lastmod><priority>0.95</priority></url>
  <url><loc>https://www.spilbloo.com/resources</loc><lastmod>2026-08-08</lastmod><priority>0.8</priority></url>
  <url><loc>https://www.spilbloo.com/careers</loc><lastmod>2026-08-08</lastmod><priority>0.8</priority></url>
  <url><loc>https://www.spilbloo.com/privacy</loc><lastmod>2026-08-08</lastmod><priority>0.4</priority></url>
  <url><loc>https://www.spilbloo.com/terms</loc><lastmod>2026-08-08</lastmod><priority>0.4</priority></url>
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
    path("api/plans/", include("plans.urls")),
    path("api/doctor-request/", include("doctor_requests.urls")),
    path("api/call/", include("calls.urls")),
    path("api/discover/", include("discover.urls")),
    path("api/notification/", include("accounts.urls_notification")),
    path("node/", include("core.urls_node")),
    path("api/core/", include("core.urls")),
]
