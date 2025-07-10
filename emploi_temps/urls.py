from django.urls import path
from .views import*

urlpatterns=[
    path("emploitemps", emploitemps, name="emploitemps"),
    path("emploitemps_student", emploitemps_student, name="emploitemps_student"),
    path("emploitemps_parent", emploitemps_parent, name="emploitemps_parent"),
    path("add_emploitemps", add_emploitemps, name="add_emploitemps"),
    path("edit_emploitemps/<str:id>", edit_emploitemps, name="edit_emploitemps"),
    path("edit_emp", edit_emp, name="edit_emp"),
    path("del_emploitemps/<str:id>", del_emploitemps, name="del_emploitemps"),
    path("ajax_enseignant/<int:id>", get_enseignant_salle_emploi.as_view(), name="ajax_enseignant"),
    path("edit_emploitemps/ajax_enseignant/<int:id>", get_enseignant_salle_emploi.as_view(), name="ajax_enseignant"),
    path("ajax_matiere_enseignant/<int:salle_id>/<int:enseignant_id>", get_matiere_enseignant_salle_emploi.as_view(), name="ajax_matiere_enseignant"),
    path("edit_emploitemps/ajax_matiere_enseignant/<int:salle_id>/<int:enseignant_id>", get_matiere_enseignant_salle_emploi.as_view(), name="ajax_matiere_enseignant"),
    path("content_emploitemps/<int:id>", content_emploitemps.as_view(), name="content_emploitemps"),
    path("content_emploitemps_parent/<int:id>", content_emploitemps_parent.as_view(), name="content_emploitemps_parent")
]