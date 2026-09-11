from django.contrib import admin

from .models import ChatSession, PushSubscription
from unfold.admin import ModelAdmin


@admin.register(PushSubscription)
class PushSubscriptionAdmin(ModelAdmin):
    list_display = ("get_username", "browser", "created_at")
    list_filter = ("user",)

    def get_username(self, obj):
        return obj.user.username

    get_username.short_description = "Пользователь"

    def browser(self, obj):
        if "fcm.googleapis.com" in obj.endpoint:
            return "🤖 Chrome/Android"
        elif "notify.windows.com" in obj.endpoint:
            return "🪟 Edge/Windows"
        elif "push.apple.com" in obj.endpoint:
            return "🍎 Safari/iPhone"
        elif "mozilla.com" in obj.endpoint:
            return "🦊 Firefox"
        return "❓ Неизвестно"

    browser.short_description = "Браузер"



@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ("id", "client", "created_at", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("client__username",)