from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Category, Product, ProductImage, SiteAssets, Cart, Favorite, CartItem,Review


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




class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('get_preview',)
    save_on_top = True

    def get_preview(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")
    get_preview.short_description = 'Превью'



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    exclude = ('group_slug',)
    inlines = [ProductImageInline]
    list_display = ('name','category', 'product_group','group_slug', 'article','color', 'price','discount_percentage','is_hit','discount_percentage')
    list_filter = ('is_available', 'name', 'group_slug', 'discount_percentage')
    search_fields = ('article', 'name')
    list_editable = ('price', 'discount_percentage', 'is_hit')
    save_on_top = True
    


#отзывы


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('title', 'text', 'user__username', 'product__name')
    list_editable = ('is_approved',)
    date_hierarchy = 'created_at'
    save_on_top = True




@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user',)
    save_on_top = True

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product')
    search_fields = ('user', 'product')
    save_on_top = True
    
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    search_fields = ('cart', 'product')
    save_on_top = True
    




admin.site.site_header = 'НР студия'
admin.site.site_title = 'НР студия'
