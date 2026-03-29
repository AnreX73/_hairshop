from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Category, Product, ProductImage, SiteAssets, Cart, Favorite, CartItem, ProductSeries, Review


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

    def get_preview(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")
    get_preview.short_description = 'Превью'


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1
    fields = ('article', 'color', 'hair_shade', 'main_image', 'price', 'discount_percentage', 'is_available')
    show_change_link = True  # ссылка на полную форму варианта


@admin.register(ProductSeries)
class ProductSeriesAdmin(admin.ModelAdmin):
    inlines = [ProductInline]
    list_display = ('name', 'get_variants_count','note_for_manager', 'created_at')
    list_filter = ('note_for_manager', 'category')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('category',)

    def get_variants_count(self, obj):
        return obj.products.count()
    get_variants_count.short_description = 'Вариантов'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('__str__', 'series', 'article', 'color', 'price', 'is_available')
    list_filter = ('is_available', 'hair_shade', 'series__category')
    search_fields = ('article', 'color', 'series__name')
    list_editable = ('price', 'is_available')
    raw_id_fields = ('series',)


#отзывы


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('title', 'text', 'user__username', 'product__name')
    list_editable = ('is_approved',)
    date_hierarchy = 'created_at'




@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user',)

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product')
    search_fields = ('user', 'product')
    
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    search_fields = ('cart', 'product')
    




admin.site.site_header = 'НР студия'
admin.site.site_title = 'НР студия'
