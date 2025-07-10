from django.urls import path
from .views import*

urlpatterns=[
    path("trimestre/trimestres", trimestres, name="trimestre/trimestres"),
    path("trimestre/add_trimestre", add_trimestre, name="trimestre/add_trimestre"),
    path("trimestre/edit_trimestre/<str:id>", edit_trimestre, name="trimestre/edit_trimestre"),
    path("edit_tr", edit_tr, name="edit_tr"),
    path("del-trimestre/<str:id>", del_trimestre, name="del_trimestre"),
    
    path("evenement/evenements", evenements, name="evenement/evenements"),
    path("evenement/add_evenement", add_evenement, name="evenement/add_evenement"),
    path("evenement/edit_evenement/<str:id>", edit_evenement, name="evenement/edit_evenement"),
    path("edit_ev", edit_ev, name="edit_ev"),
    path("del_evenement/<str:id>", del_evenement, name="del_evenement"),
    path("evenement/ajax_delete_evenement/<int:id>", ajax_delete_evenement, name="ajax_delete_evenement"),

]