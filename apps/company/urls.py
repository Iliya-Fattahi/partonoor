from django.urls import path

from . import views

app_name = "company"

urlpatterns = [
    path("about/", views.about_view, name="about"),
    path("workshop/", views.workshop_view, name="workshop"),
]
