from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    fields = ("is_staff", "text", "image", "audio", "audio_duration", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ("client_label", "created_at", "updated_at", "open_chat")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "created_at", "updated_at", "open_chat")
    inlines = (MessageInline,)

    @admin.display(description="Клиент")
    def client_label(self, obj):
        return obj.client_label

    @admin.display(description="Ответить")
    def open_chat(self, obj):
        return format_html(
            '<a href="{}">Открыть чат</a>',
            reverse("chat:conversation", args=[obj.pk]),
        )

    def has_add_permission(self, request):
        return False
