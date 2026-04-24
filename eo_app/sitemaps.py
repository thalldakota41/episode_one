from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Show, Creator, Article

class ShowSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Show.objects.all()

    def location(self, obj):
        return reverse('show_page', args=[obj.id])


class CreatorSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Creator.objects.all()

    def location(self, obj):
        return reverse('creator', args=[obj.id])


class ArticleSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Article.objects.filter(status='published')

    def location(self, obj):
        return reverse('article_detail', args=[obj.slug])


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return ['index', 'browse', 'news', 'reviews', 'about', 'comment']

    def location(self, item):
        return reverse(item)