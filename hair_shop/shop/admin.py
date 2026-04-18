from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import Category, Order, Product, ProductImage, SiteAssets, Cart, Favorite, CartItem,Review, OrderItem, Contact, ReviewMedia, Info


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
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
    exclude = ('group_slug',)
    inlines = [ProductImageInline]
    list_display = ('name','main_image_preview','category', 'product_group', 'article','color', 'price','discount_percentage')
    list_filter = ('is_available', 'name', 'group_slug', 'discount_percentage')
    search_fields = ('article', 'name')
    list_editable = ('price', 'discount_percentage', )
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
class ReviewMediaInline(admin.TabularInline):
    model = ReviewMedia
    extra = 0  # Чтобы не плодить пустые поля для новых фото
    readonly_fields = ('preview',)  # Поле только для чтения, где будет картинка

    def preview(self, obj):
        if obj.file: # Предположим, поле в ReviewMedia называется file
            return mark_safe(f'<img src="{obj.file.url}" style="max-height: 100px;">')
        return "Нет изображения"
    
    preview.short_description = 'Предпросмотр'

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    inlines = [ReviewMediaInline]
    list_display = ('product', 'user', 'rating', 'is_approved','get_media_count', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('title', 'text', 'user__username', 'product__name')
    list_editable = ('is_approved',)
    date_hierarchy = 'created_at'
    save_on_top = True

    def get_media_count(self, obj):
        return obj.media.count()
    
    get_media_count.short_description = 'Кол-во медиа'




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
    list_display = ('user','order_number', 'status','payment_status')
    list_editable = ('status', 'payment_status')
    search_fields = ('user',)
    save_on_top = True


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'product_price')
    search_fields = ('order', 'product_name')
    save_on_top = True


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ('label', 'value', 'contact_type', 'is_active')
    list_filter = ('contact_type', 'is_active')
    search_fields = ('label', 'value')
    list_editable = ('is_active',)
    save_on_top = True


@admin.register(Info)
class InfoAdmin(ModelAdmin):
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
    list_display = ('name', 'title', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'title', 'slug')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    save_on_top = True


admin.site.site_header = 'НР студия'
admin.site.site_title = 'НР студия'
