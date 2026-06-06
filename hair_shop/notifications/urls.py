from django.urls import path
from . import views

urlpatterns = [
    path("subscribe/", views.save_subscription, name="push-subscribe"),
    path("unsubscribe/", views.delete_subscription, name="push-unsubscribe"),
    path("chat/session/", views.get_or_create_session, name="chat_session"),
    path(
        "chat/<int:session_id>/poll/<int:last_id>/",
        views.poll_messages,
        name="chat_poll",
    ),
    path("chat/<int:session_id>/send/", views.send_message, name="chat_send"),
    path("chat/unread-count/", views.unread_chat_count, name="chat_unread_count"),
]
