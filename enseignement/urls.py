from django.urls import path
from .views import*

urlpatterns=[
    path("enseignements", enseignements, name="enseignements"),
    path("trim_enseignement/<str:salle_id>", trim_enseignement, name="trim_enseignement"),
    path("detail_enseignement/<str:salle_id>/<str:trimestre>", detail_enseignement, name="detail_enseignement"),
    path("add_enseignement", add_enseignement, name="add_enseignement"),
    path("edit_enseignement/<str:id>", edit_enseignement, name="edit_enseignement"),
    path("edit_en", edit_en, name="edit_en"),
    path("del_enseignement/<str:id>", del_enseignement, name="del_enseignement"),
    path("ajax_matiere/<int:id>", get_matiere_programmer_salle.as_view(), name="ajax_matiere"),
    path("edit_nseignement/ajax_matiere/<int:id>", get_matiere_programmer_salle.as_view(), name="ajax_matiere"),
    path("droit_eval/<str:id>", droit_eval, name="droit_eval"),
    path("droit_eval/droit_evaluation/<int:id>", droit_evaluation, name="droit_evaluation"),
    path("eval_enseignant", eval_enseignant, name="eval_enseignant"),
    path("add_eval", add_eval, name="add_eval")
]