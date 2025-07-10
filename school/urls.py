from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns = [
    path("settings/setting", setting, name="settings/setting"),
    path("settings/setting_supuser", setting_supuser, name="settings/setting_supuser"),
    path("settings/setting_sup_admin", setting_sup_admin, name="settings/setting_sup_admin"),
    path("settings/maintenance", maintenance, name="settings/maintenance"),
    path("settings/authorization_etablissement/<str:id>", authorization_etablissement, name="settings/authorization_etablissement"),
    path("settings/authorization", authorization, name="settings/authorization"),
    path("settings/dashboard/<str:id>", dashboard, name="settings/dashboard"),
    path("session_annee/<int:etablissement_id>", session_annee, name="session_annee"),
    path("settings/db_cycle/<str:etablissement_id>", db_cycle, name="settings/db_cycle"),
    path("settings/db_classe/<str:id>", db_classe, name="settings/db_classe"),
    path("settings/db", db, name="settings/db"),
    path("settings/db_supuser", db_supuser, name="settings/db_supuser"),
    path("settings/home", home, name="settings/home"),
    path("settings/resources_admin", resources_admin, name="settings/resources_admin"),
    path("settings/resources_admin_parent", resources_admin_parent, name="settings/resources_admin_parent"),
    path("settings/resources_admin_user", resources_admin_user, name="settings/resources_admin_user"),
    path("settings/help", need_help, name="settings/help"),
    path("settings/help_sup_admin", need_help_sup_admin, name="settings/help_sup_admin"),
    path("settings/help_customer", need_help_customer, name="settings/help_customer"),
    path("ajaxyear/<int:id>", ajaxyear.as_view(), name="ajaxyear"),
    path("ajaxyear_index/<int:id>", ajaxyear_index.as_view(), name="ajaxyear_index"),
    path("settings/fetchgroup/<int:id>", fetchgroup.as_view(), name="fetchgroup"),
    path("settings/fetchgroupe_etablissement_user/<int:id>", fetchgroup_etablissement_user.as_view(), name="fetchgroupe_etablissement_user"),
    path("ajax_group_name/<str:group_name>", ajax_group_name.as_view(), name="ajax_group_name"),
    path("ajax_group_name_index/<str:group_name>", ajax_group_name_index.as_view(), name="ajax_group_name_index"),
    path("settings/ajax_content_salle_etablissement/<int:id>", ajax_content_salle_etablissement, name="ajax_content_salle_etablissement"),
    path("settings/ajax_content_student_etablissement/<int:id>", ajax_content_student_etablissement, name="ajax_content_student_etablissement"),
    path("settings/ajax_modal_block_student_etablissement/<int:id>", ajax_modal_block_student_etablissement, name="ajax_modal_block_student_etablissement"),
    path("settings/ajax_block_student_etablissement/<int:id>", ajax_block_student_etablissement, name="ajax_block_student_etablissement"),
    
    path("del_new_user/<str:id>", del_new_user, name="del_new_user"),
    path("settings/ajax_delete_new_user/<int:id>", ajax_delete_new_user, name="ajax_delete_new_user"),
    path("settings/ajax_group_new_user/<int:id>", ajax_group_new_user, name="ajax_group_new_user"),
    path("add_new_user_to_group", add_new_user_to_group, name="add_new_user_to_group"),
    path("send_message/<int:id>", send_message, name="send_message")
]