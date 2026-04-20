from django.contrib import admin
from .models import Creator, Tag, Show, Comment, StaffFavorite, CreatorOfTheMonth, InfluentialShow, FeaturedShow

@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['genre']


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['tags', 'creators']


@admin.register(StaffFavorite)
class StaffFavoriteAdmin(admin.ModelAdmin):
    search_fields = ['show__title']


@admin.register(InfluentialShow)
class InfluentialShowAdmin(admin.ModelAdmin):
    search_fields = ['show__title']


@admin.register(CreatorOfTheMonth)
class CreatorOfTheMonthAdmin(admin.ModelAdmin):
    search_fields = ['creator__name']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    search_fields = ['name', 'email']
    list_display = ['name', 'email', 'created']
    readonly_fields = ['created', 'updated_at']

@admin.register(FeaturedShow)
class FeaturedShowAdmin(admin.ModelAdmin):
    list_display = ['show', 'featured_date', 'is_active']
    search_fields = ['show__title']