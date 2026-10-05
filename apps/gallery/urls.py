from django.urls import path

from . import views

app_name = "gallery"

urlpatterns = [
    path("", views.gallery_view, name="index"),
    path("<str:slug>/", views.category_view, name="category"),
]
