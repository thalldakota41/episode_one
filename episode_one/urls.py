from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from eo_app.sitemaps import ShowSitemap, CreatorSitemap, ArticleSitemap, StaticSitemap

sitemaps = {
    'shows': ShowSitemap,
    'creators': CreatorSitemap,
    'articles': ArticleSitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('eo_app.urls')),
]