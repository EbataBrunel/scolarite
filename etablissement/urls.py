from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("etabs", etablissements, name="etabs"),
    path("add_etablissement", add_etablissement, name="add_etablissement"),
    path("edit_etablissement/<str:id>", edit_etablissement, name="edit_etablissement"),
    path("edit_et", edit_et, name="edit_et"),
    path("del_etablissement/<str:id>", del_etablissement, name="del_etablissement"),
    path("delete_etablissement/<str:id>", delete_etablissement, name="delete_etablissement"),
]
