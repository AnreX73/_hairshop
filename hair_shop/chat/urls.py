from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("start/", views.start, name="start"),
    path("upload/", views.upload_image, name="upload"),
    path("operator/", views.inbox, name="inbox"),
    path("operator/<uuid:pk>/", views.conversation, name="conversation"),
    path(
        "operator/<uuid:pk>/upload/",
        views.upload_operator_image,
        name="operator_upload",
    ),
]
