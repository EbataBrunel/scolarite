from django.urls import path
from .views import*

urlpatterns=[
    path("absences", absences, name="absences"),
    path("detail_salle_absence/<str:enseignant_id>", detail_salle_absence, name="detail_salle_absence"),
    path("detail_absences/<str:enseignant_id>/<str:salle_id>", detail_absences, name="detail_absences"),
    path("save_absence/<str:emploi_id>", save_absence, name="save_absence"),
    path("save_ab", save_ab, name="save_ab"),
    path("edit_absence/<str:id>", edit_absence, name="edit_absence"),
    path("edit_ab/", edit_ab, name="edit_ab"),
    path("del_absence/<str:id>", del_absence, name="del_absence"),
    path("mes_absences", mes_absences, name="mes_absences"),
    path("detail_absences/<str:enseignant_id>/decision_absence_enseignant/<int:id>/<int:status>", decision_absence_enseignant, name="decision_absence_enseignant"),
    path("save_motif_absence", save_motif_absence, name="save_motif_absence"),
    path("mes_absences_admin", mes_absences_admin, name="mes_absences_admin"),
    
    path("presence_student/<str:id>", presence_student, name="presence_student"),
    path("abs_students", abs_students, name="abs_students"),
    path("abs_student_user", abs_student_user, name="abs_student_user"),
    path("abs_student_mat_user/<str:student_id>", abs_student_mat_user, name="abs_student_mat_user"),
    path("presence_student/save_absencestudent/<int:id>/<int:emargement_id>", save_absencestudent.as_view(), name="save_absencestudent"),
    path("abs_studentmatiere/<str:salle_id>/<str:matiere_month>", abs_studentmatiere, name="abs_studentmatiere"),
    path("save_motif_absence_student", save_motif_absence_student, name="save_motif_absence_student"),
    path("abs_student_mat_user/decision_absence_student/<int:id>/<int:status>", decision_absence_student, name="decision_absence_student"),
    
    
    path("absences_admin", absences_admin, name="absences_admin"),
    path("add_absence_admin", add_absence_admin, name="add_absence_admin"),
    path("edit_absence_admin/<str:id>", edit_absence_admin, name="edit_absence_admin"),
    path("edit_aa", edit_aa, name="edit_aa"),
    path("del_absence_admin/<str:id>", del_absence_admin, name="del_absence_admin"),
    path("ajax_delete_absence_admin/<int:id>", ajax_delete_absence_admin, name="ajax_delete_absence_admin"),
    path("modal_decision_absence/<int:id>", modal_decision_absence, name="modal_decision_absence"),
    path("decision_absence_admin/<int:id>/<int:status>", decision_absence_admin, name="decision_absence_admin")

]