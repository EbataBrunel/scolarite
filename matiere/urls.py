from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("matieres", matieres, name="matieres"),
    path("matieres_admin", matieres_admin, name="matieres_admin"),
    path("add_matiere", add_matiere, name="add_matiere"),
    path("edit_matiere/<str:id>", edit_matiere, name="edit_matiere"),
    path("edit_mt", edit_mt, name="edit_mt"),
    path("del_matiere/<str:id>", del_matiere, name="del_matiere"),
    path("delete_matiere/<str:id>", delete_matiere, name="delete_matiere")
]
