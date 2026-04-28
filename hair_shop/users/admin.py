from django.contrib import admin

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import  Group

from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin

from .models import User

admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'delivery_city', 'delivery_address', 'is_vip')}),
    )
    # Добавление полей в форму создания (add_fieldsets)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'delivery_city', 'delivery_address', 'is_vip')}),
    )
    
    list_display = ('username', 'email', 'phone_number', 'delivery_city', 'is_vip')
    search_fields = ('username', 'email', 'delivery_city')
    list_editable = ('is_vip',)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass