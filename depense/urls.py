from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("depenses", depenses, name="depenses"),
    path("add_depense", add_depense, name="add_depense"),
    path("edit_depense/<str:id>", edit_depense, name="edit_depense"),
    path("edit_dp", edit_dp, name="edit_dp"),
    path("ajax_delete_depense/<int:id>", ajax_delete_depense, name="ajax_delete_depense"),
    path("del_depense/<str:id>", del_depense, name="del_depense"),
    path("edit_depense/type_depense/<str:type_depense>", type_depense, name="type_depense")
]
