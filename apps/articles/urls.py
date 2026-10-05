from django.urls import path

from . import views

app_name = "articles"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("upload-image/", views.upload_inline_image, name="upload_image"),
    path("<str:slug>/", views.article_detail, name="detail"),
]
