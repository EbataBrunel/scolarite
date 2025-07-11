from django.urls import path
from .views import*

urlpatterns=[
    path("compositions", compositions, name="compositions"),
    path("detail_cmp_salle/<str:id>", detail_cmp_salle, name="detail_cmp_salle"),
    path("detail_cmp_trimestre/<str:salle_id>/<str:trimestre>", detail_cmp_trimestre, name="detail_cmp_trimestre"),
    path("detail_comp_student/<str:salle_id>/<str:trimestre>/<str:student_id>", detail_comp_student, name="detail_comp_student"),
    path("detail_comp_matiere/<str:salle_id>/<str:trimestre>/<str:matiere_id>", detail_comp_matiere, name="detail_comp_matiere"),
    path("add_composition", add_composition, name="add_composition"),
    path("ajax_matiere_enseigner/<str:trimestre>/<int:salle_id>", get_matiere_enseigner_salle.as_view(), name="ajax_matiere_enseigner"),
    path("ajax_student_inscris/<int:id>", get_student_inscris_salle.as_view(), name="ajax_student_inscris"),
    path("ajax_trimestre_enseigner/<int:id>", get_trimestre_enseigner_salle.as_view(), name="ajax_trimestre_enseigner"),
    
    path("edit_composition/<str:id>/<str:param>", edit_composition, name="edit_composition"),
    path("edit_composition/<int:salle_id>/ajax_trim_enseigner/<int:id>", get_trim_matiere_enseigner_salle.as_view(), name="ajax_trim_enseigner"),
    path("edit_composition/<int:salle_id>/ajax_trim_student_inscris/<int:id>", get_trim_student_inscris_salle.as_view(), name="ajax_trim_student_inscris"),
    path("edit_composition/<int:salle_id>/ajax_trimestre_matiere_enseigner/<str:trimestre>/<int:id>", get_trimestre_matiere_enseigner_salle.as_view(), name="ajax_trimestre_matiere_enseigner"),
    path("edit_cp", edit_cp, name="edit_cp"),
    path("del_composition/<str:id>", del_composition, name="del_composition"),
    
    path("ajax_eval_controle/<str:evaluation>", get_ajax_eval_controle, name="ajax_eval_controle"),
    path("edit-composition/<int:id>/ajax_evaluation_controle/<str:evaluation>", get_ajax_evaluation_controle, name="ajax_evaluation_controle"),
    
    path("comp_deliberation", comp_deliberation, name="comp_deliberation"),
    path("trimestre_deliberation/<int:salle_id>", trimestre_deliberation.as_view(), name="trimestre_deliberation"),
    path("content_deliberation/<int:salle_id>/<str:trimestre>", content_deliberation.as_view(), name="content_deliberation"),
    path("tri_student_composer/<str:action>/<int:salle_id>/<str:trimestre>", tri_student_composer.as_view(), name="tri_student_composer/"),
    
    path("moyenne_validation", moyenne_validation, name="moyenne_validation"),
    
    path("comp_resultat", comp_resultat, name="comp_resultat"),
    path("trimestre_resultat/<int:salle_id>", trimestre_resultat.as_view(), name="trimestre_resultat"),
    path("content_resultat/<int:salle_id>/<str:trimestre>", content_resultat.as_view(), name="content_resultat"),
    path("publication_result", publication_result, name="publication_result"),

    path("gestion-etude", gestion_etude, name="gestion_etude"),
    path("gestion-etude-parent", gestion_etude_parent, name="gestion_etude_parent"),
    path("gestion-etude-parent-detail/<str:student_id>", gestion_etude_parent_detail, name="gestion_etude_parent_detail"),
    
    path("cmp_teacher", cmp_teacher, name="cmp_teacher"),
    path("detail_cmpteacher/<str:salle_id>/<str:matiere_id>/<str:trimestre>", detail_cmpteacher, name="detail_cmpteacher"),
    path("detail_cmpteacher/<int:s_id>/<int:m_id>/examen_teacher/<str:trimestre>/<str:evaluation>/<int:salle_id>/<int:matiere_id>", examen_teacher.as_view(), name="examen_teacher"),
    path("stat_composition", stat_composition, name="stat_composition"),
    path("content_stat_comp/<str:trimestre>", content_stat_comp, name="content_stat_comp"),
    path("content_stat_comp_trimestre/<int:salle_id>", content_stat_comp_trimestre, name="content_stat_comp_trimestre"),
    
    path("bulletin-etudiant/<str:student_id>/<str:trimestre>", bulletin_etudiant, name="bulletin_etudiant"),
    path("bulletin-etudiant-customer/<str:student_id>/<str:trimestre>", bulletin_etudiant_customer, name="bulletin_etudiant_customer"),
    path("proces_verbal_examen/<str:salle_id>/<str:trimestre>", proces_verbal_examen, name="proces_verbal_examen"),
    path("fetch_releve_controle/<int:student_id>/<int:matiere_id>/<str:num_controle>/<str:trimestre>", fetch_releve_controle, name="fetch_releve_controle"),
    path("fetch_releve_examen/<int:student_id>/<int:matiere_id>/<str:trimestre>", fetch_releve_examen, name="fetch_releve_examen"),
    path("gestion-etude-parent-detail/fetch_releve_controle/<int:student_id>/<int:matiere_id>/<str:num_controle>/<str:trimestre>", fetch_releve_controle, name="fetch_releve_controle"),
    path("gestion-etude-parent-detail/fetch_releve_examen/<int:student_id>/<int:matiere_id>/<str:trimestre>", fetch_releve_examen, name="fetch_releve_examen"),
    path("releve_note_controle/<str:salle_id>/<str:matiere_id>/<str:num_controle>/<str:trimestre>", releve_note_controle, name="releve_note_controle"),
    path("releve_note_controle_customer/<str:salle_id>/<str:matiere_id>/<str:num_controle>/<str:trimestre>", releve_note_controle_customer, name="releve_note_controle_customer"),
    path("releve_note_examen/<str:salle_id>/<str:matiere_id>/<str:trimestre>", releve_note_examen, name="releve_note_examen"),
    path("releve_note_examen_customer/<str:salle_id>/<str:matiere_id>/<str:trimestre>", releve_note_examen_customer, name="releve_note_examen_customer"),
    
    path("deliberation/deliberations", deliberations, name="deliberation/deliberations"),
    path("deliberation/detail_deliberation/<int:id>", detail_deliberation, name="deliberation/detail_deliberation"),
    path("cloture_deliberation", cloture_deliberation, name="cloture_deliberation")
]