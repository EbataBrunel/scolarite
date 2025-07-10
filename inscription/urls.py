from django.urls import path
from .views import *

urlpatterns=[
    path("inscriptions", inscriptions, name="inscriptions"),
    path("detail_inscription/<str:id>", detail_inscription, name="detail_inscription"),
    path("add_inscription", add_inscription, name="add_inscription"),
    path("edit_inscription/<str:id>", edit_inscription, name="edit_inscription"),
    path("edit_in", edit_in, name="edit_in"),
    path("del_inscription/<str:id>", del_inscription, name="del_inscription"),
    path("inscription_parents", inscription_parents, name="inscription_parents"),
    path("access_parent/<int:id>", access_parent, name="access_parent"),
    path("detail_inscription/access_student/<int:id>", access_student, name="access_student"),
    path("detail_inscription/block_account_student/<int:id>", block_account_student, name="block_account_student"),
    
    path("ajax_amount_inscription/<int:salle_id>", ajax_amount_inscription, name="ajax_amount_inscription"),
    path("edit_inscription/ajax_amount_inscription/<int:salle_id>", ajax_amount_inscription, name="ajax_amount_inscription"),
    
    path("comptabilite_inscription", comptabilite_inscription, name="comptabilite_inscription"),
    path("inscriptions_enseignant", inscriptions_enseignant, name="inscriptions_enseignant"),
    path("inscriptions_admin", inscriptions_admin, name="inscriptions_admin"),
    path("attestation_inscription/<str:student_id>", attestation_inscription, name="attestation_inscription")
]