from django.urls import path
from .views import*

urlpatterns=[
    path("publications", publications, name="publications"),
    path("detail_publication/<str:salle_id>", detail_publication, name="detail_publication"),
    path("add_publication", add_publication, name="add_publication"),
    path("edit_publication/<str:id>", edit_publication, name="edit_publication"),
    path("edit_pb", edit_pub, name="edit_pub"),
    path("del_publication/<str:id>", del_publication, name="del_publication"),
    
    path("pub_student", pub_student, name="pub_student"),
]