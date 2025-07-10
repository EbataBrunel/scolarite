from django.urls import path
from .views import*

urlpatterns=[
    path("cours", cours, name="cours"),
    path("detail-cours/<str:salle_id>/<str:matiere_id>", detail_cours, name="detail_cours"),
    path("add-cours", add_cours, name="add_cours"),
    path("mat_enseignant/<int:salle_id>", mat_enseignant.as_view(), name="mat_enseignant"),
    path("edit-cours/mat_enseignant/<int:salle_id>", mat_enseignant.as_view(), name="mat_enseignant"),
    path("edit-cours/<str:id>", edit_cours, name="edit_cours"),
    path("edit-cours", edit_cour, name="edit_cour"),
    path("del-cours/<str:id>", del_cours, name="del_cours"),
    
    path("cours_ligne", cours_ligne, name="cours_ligne"),
    path("detail_coursligne/<str:salle_id>/<str:matiere_id>", detail_coursligne, name="detail_coursligne"),
    
    path("add-comment", add_commentcours, name="add_commentcours"),
    path("detail_coursligne/<int:salle_id>/delete_comment/<int:id>", delete_comment.as_view(), name="delete_comment")
]