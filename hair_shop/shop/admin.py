from django.contrib import admin
from django.utils.safestring import mark_safe

from unfold.admin import ModelAdmin

from .models import Category, Order, Product, ProductImage, SiteAssets, Cart, Favorite, CartItem,Review, OrderItem


@admin.register(SiteAssets)
class SiteAssetsAdmin(ModelAdmin):
    list_display = ('site_assets_name', 'is_active', 'note', 'getHtmlPhoto')
    search_fields = ('site_assets_name',)
    list_filter = ('is_active',)
    save_on_top = True

    def getHtmlPhoto(self, image):
        if image.image:
            return mark_safe(f"<img src='{image.image.url}' width=50>")

    getHtmlPhoto.short_description = 'миниатюра'


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
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
class ProductAdmin(ModelAdmin):
    exclude = ('group_slug',)
    inlines = [ProductImageInline]
    list_display = ('name','main_image_preview','category', 'product_group', 'article','color', 'price','discount_percentage','is_hit')
    list_filter = ('is_available', 'name', 'group_slug', 'discount_percentage')
    search_fields = ('article', 'name')
    list_editable = ('price', 'discount_percentage','category', 'is_hit')
    save_on_top = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('images')

    def main_image_preview(self, obj):
        main_img = obj.main_image
        if main_img:
            return mark_safe(f'<img src="{main_img.url}" width="50" />')
        return "—"
    main_image_preview.short_description = 'Превью'

    
    


#отзывы


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('title', 'text', 'user__username', 'product__name')
    list_editable = ('is_approved',)
    date_hierarchy = 'created_at'
    save_on_top = True




@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ('user', 'total_price', 'total_items')
    search_fields = ('user',)
    save_on_top = True

@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ('user', 'product')
    search_fields = ('user', 'product')
    save_on_top = True
    
@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    search_fields = ('cart', 'product')
    save_on_top = True
    


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('user', 'status','payment_status')
    list_editable = ('status', 'payment_status')
    search_fields = ('user',)
    save_on_top = True


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'product_price')
    search_fields = ('order', 'product_name')
    save_on_top = True



admin.site.site_header = 'НР студия'
admin.site.site_title = 'НР студия'
