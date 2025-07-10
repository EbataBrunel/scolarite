from django.urls import path
from .views import *
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("series", series, name="series"),
    path("series_admin", series_admin, name="series_admin"),
    path("add_serie", add_serie, name="add_serie"),
    path("edit_serie/<str:id>", edit_serie, name="edit_serie"),
    path("edit_sr", edit_sr, name="edit_sr"),
    path("del_serie/<str:id>", del_serie, name="del_serie"),
    path("delete_serie/<str:id>", delete_serie, name="delete_serie")
]