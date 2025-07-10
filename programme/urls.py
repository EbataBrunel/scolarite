from django.urls import path
from .views import*

urlpatterns=[
    path("programmes", programmes, name="programmes"),
    path("detail_programme/<str:id>", detail_programme, name="detail_programme"),
    path("add_programme", add_programme, name="add_programme"),
    path("edit_programme/<str:id>", edit_programme, name="edit_programme"),
    path("edit_pg", edit_pg, name="edit_pg"),
    path("del_programme/<str:id>", del_programme, name="del_programme"),
]