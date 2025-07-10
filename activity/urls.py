from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("activities", activities, name="activities"),
    path("detail_activity/<str:type>", detail_activity, name="detail_activity"),
    path("add_activity", add_activity, name="add_activity"),
    path("edit_activity/<str:id>", edit_activity, name="edit_activity"),
    path("edit_ac", edit_ac, name="edit_ac"),
    path("del_activity/<str:id>", del_activity, name="del_activity"),
    path("activity_student", activity_student, name="activity_student"),
]