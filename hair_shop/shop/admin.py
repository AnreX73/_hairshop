from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Category, Product, ProductImage, SiteAssets, Cart, Favorite


@admin.register(SiteAssets)
class SiteAssetsAdmin(admin.ModelAdmin):
    list_display = ('site_assets_name', 'is_active', 'note', 'getHtmlPhoto')
    search_fields = ('site_assets_name',)
    list_filter = ('is_active',)
    save_on_top = True

    def getHtmlPhoto(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")

    getHtmlPhoto.short_description = 'миниатюра'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'getHtmlPhoto')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True

    def getHtmlPhoto(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")

    getHtmlPhoto.short_description = 'миниатюра'






class ProductImageAdmin(admin.TabularInline):
    model = ProductImage
    list_display = ('product', 'getHtmlPhoto')
    search_fields = ('product__name',)
    save_on_top = True
    readonly_fields = ('getHtmlPhoto',)

    def getHtmlPhoto(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")

    getHtmlPhoto.short_description = 'миниатюра'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageAdmin]
    list_display = ('name','slug', 'getHtmlPhoto', 'is_hit', 'rating')
    search_fields = ('name',)
    save_on_top = True
    list_editable = ('is_hit', 'rating')
    prepopulated_fields = {'slug': ('name',)}

    def getHtmlPhoto(self, image):
        if image.main_image:
            return mark_safe(f"<img src='{image.main_image.url}' width=50>")

    getHtmlPhoto.short_description = 'миниатюра'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user',)

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product')
    search_fields = ('user', 'product')
    





admin.site.site_header = 'НР студия'
admin.site.site_title = 'НР студия'
