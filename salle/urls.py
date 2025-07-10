from django.urls import path
from .views import*

urlpatterns=[
    path("salles", salles, name="salles"),
    path("salles_admin", salles_admin, name="salles_admin"),
    path("detail_salle/<str:classe_id>", detail_salle, name="detail_salle"),
    path("add_salle", add_salle, name="add_salle"),
    path("edit_salle/<str:id>", edit_salle, name="edit_salle"),
    path("edit_sl", edit_sl, name="edit_sl"),
    path("del_salle/<str:id>", del_salle, name="del_salle"),
    path("delete_salle/<str:id>", delete_salle, name="delete_salle"),
    path("ajax_classe/<int:id>", ajax_classe, name="ajax_classe"),
    path("edit_salle/ajax_classe/<int:id>", ajax_classe, name="ajax_classe")
    
]