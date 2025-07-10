from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("annee_academiques", anneeacademiques, name="annee_academiques"),
    path("anneeacademiques_promoteur", anneeacademiques_promoteur, name="anneeacademiques_promoteur"),
    path("add_anneeacademique", add_anneeacademique, name="add_anneeacademique"),
    path("edit_anneeacademique/<str:id>", edit_anneeacademique, name="edit_anneeacademique"),
    path("edit_anneeac", edit_anneeac, name="edit_anneeac"),
    path("delete_anneeacademique/<str:id>", delete_anneeacademique, name="delete_anneeacademique"),
    path("del_anneeacademique/<str:id>", del_anneeacademique, name="del_anneeacademique"),
    path("cloture_anneeacademique/<str:id>", cloture_anneeacademique, name="cloture_anneeacademique"),
    path("clot_sanneeacademique", clot_anneeacademique, name="clot_anneeacademique"),
    path("droit_acces_anneeacademique/<str:id>", droit_acces_anneeacademique, name="droit_acces_anneeacademique"),
    path("acces_sanneeacademique", acces_anneeacademique, name="acces_anneeacademique")
]