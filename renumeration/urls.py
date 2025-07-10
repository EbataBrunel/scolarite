from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("renumerations", renumerations, name="renumerations"),
    path("personnel_renum", personnel_renumeration, name="personnel_renum"),
    path("ajax_pers_renum/<str:month>", get_personnel_renumeration, name="ajax_pers_renum"),
    path("ajax_teacher_renum/<str:month>", get_teacher_renumeration, name="ajax_teacher_renum"),
    path("recap_emargement/<str:enseignant_id>/<str:month>", recap_emargement, name="recap_emargement"),
    path("add_renumeration/<str:enseignant_id>/<str:month>", add_renumeration, name="add_renumeration"),
    path("add_renum", add_renum, name="add_renum"),
    path("edit_renum/<str:id>", edit_renum, name="edit_renum"),
    path("edit_re", edit_re, name="edit_re"),
    path("del_renum/<str:id>", del_renum, name="del_renum"),
    path("ajax_delete_renum/<int:id>", ajax_delete_renum, name="ajax_delete_renum"),
    path("mes_renumerations", mes_renumerations, name="mes_renumerations"),
    
    
    path("contrat/contrats", contrats, name="contrat/contrats"),
    path("contrat/add_contrat", add_contrat, name="contrat/add_contrat"),
    path("contrat/edit_contrat/<str:id>", edit_contrat, name="contrat/edit_contrat"),
    path("edit_ct", edit_ct, name="edit_ct"),
    path("del_contrat/<str:id>", del_contrat, name="del_contrat"),
    path("contrat/contrats_user", contrats_user, name="contrat/contrats_user"),
    path("signer_contrat/<int:contrat_id>", signer_contrat, name="signer_contrat"),
    path("contrat/ajax_delete_contrat/<int:id>", ajax_delete_contrat, name="ajax_delete_contrat"),
    
    path("renum/renum_admin", renum_admin, name="renum/renum_admin"),
    path("renum/add_renum_admin", add_renum_admin, name="renum/add_renum_admin"),
    path("renum/add_renum_ad/<str:id>/<str:month>/<str:type_renumeration>", add_renum_ad, name="renum/add_renum_ad"),
    path("renum/edit_renum_admin/<str:id>", edit_renum_admin, name="renum/edit_renum_admin"),
    path("edit_ra", edit_ra, name="edit_ra"),
    path("del_renum_admin/<str:id>", del_renum_admin, name="del_renum_admin"),
    path("renum/mes_renum_admin", mes_renum_admin, name="renum/mes_renum_admin"),
    path("renum/ajax_delete_renum_admin/<int:id>", ajax_delete_renum_admin, name="ajax_delete_renum_admin"),
    
    path("recapitulatif", recapitulatif, name="recapitulatif"),
    path("contrat/ajax_type_contrat/<str:type_contrat>", ajax_type_contrat, name="ajax_type_contrat"),
    path("contrat/edit_contrat/ajax_type_contrat/<str:type_contrat>", ajax_type_contrat, name="ajax_type_contrat"),
    path("renum/ajax_user_month_contrat/<int:user_id>", ajax_user_month_contrat, name="ajax_user_month_contrat"),
    path("edit_renum_admin/ajax_user_month_contrat/<int:user_id>", ajax_user_month_contrat, name="ajax_user_month_contrat"),
    path("renum/ajax_user_amount/<int:user_id>/<str:month>", ajax_user_amount, name="ajax_user_amount"),
    path("edit_renum_admin/ajax_user_amount/<int:user_id>/<str:month>", ajax_user_amount, name="ajax_user_amount"),
    path("ajax_recapitulatif/<str:month>", ajax_recapitulatif, name="ajax_recapitulatif"),
    path("caisse", caisse, name="caisse"),
    path("apercu_global", apercu_global, name="apercu_global"),
    path("bulletin-paie-enseignant/<str:id>", bulletin_paie_enseignant, name="bulletin_paie_enseignant"),
    path("bulletin-paie-admin/<str:id>", bulletin_paie_admin, name="bulletin_paie_admin")
]