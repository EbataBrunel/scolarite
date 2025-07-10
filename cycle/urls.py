from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns = [
    path("cycles", cycles, name="cycles"),
    path("cycles_admin", cycles_admin, name="cycles_admin"),
    path("add_cycle", add_cycle, name="add_cycle"),
    path("edit_cycle/<str:id>", edit_cycle, name="edit_cycle"),
    path("edit_cy", edit_cy, name="edit_cy"),
    path("del_cycle/<str:id>", del_cycle, name="del_cycle"),
    path("delete_cycle/<str:id>", delete_cycle, name="delete_cycle")
]
