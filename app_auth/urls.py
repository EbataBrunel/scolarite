from django.urls import path, reverse_lazy
from .views import*
from django.contrib.auth import views as auth_views
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("add_annee_setting", add_annee_setting, name="add_annee_setting" ),
    path("register_supuser", register_supuser, name="user/register_supuser"),
    path("register", register, name="user/register"),
    path("success-account/<str:id>", success_account, name="user/success-account"),
    path("success-account-etablissement/<str:user_id>/<str:etablissement_id>", success_account_etablissement, name="user/success-account-etablissement"),
    path("activate/<uidb64>/<token>", activate, name="activate"),
    path("login", login_user, name="connection/login"),
    path("logout", logout_user, name="logout"),
    path("account", account_user, name="connection/account"),
    path("connexion", login_customer, name="connection/connexion"),
    path("logout_customer", logout_customer, name="logout_customer"),
    
    path("user/detail_supuser/<str:id>", detail_supuser, name="user/detail_supuser"),
    path("del_supuser/<str:id>", del_supuser, name="del_supuser"), 
    path("user/promoteurs/", promoteurs, name="user/promoteurs"),
    path("user/detail_promoteur/<str:id>", detail_promoteur, name="user/detail_promoteur"),
    path("user/delete_promoteur/<str:id>", delete_promoteur, name="user/delete_promoteur"),
    path("del_promoteur/<str:id>", del_promoteur, name="del_promoteur"), 
    
    path("user/admin/", administrator, name="user/admin"),
    path("user/detail_admin/<str:id>", detail_admin, name="user/detail_admin"),
    path("del_admin/<str:id>", del_admin, name="del_admin"), 
    path("user/delete_admin/<str:id>", delete_admin, name="user/delete_admin"),    
    path("teacher/teachers/", teachers, name="teacher/teachers"),    
    path("teacher/detail_teacher/<str:id>", detail_teacher, name="teacher/detail_teacher"),
    path("teacher/delete-teacher/<str:id>", delete_teacher, name="teacher/delete_teacher"),
    path("del-teacher/<str:id>", del_teacher, name="del_teacher"),  
    path("user/profile/", profile, name="user/profile"),
    path("user/profile_supuser/", profile_supuser, name="user/profile_supuser"),
    path("user/profile_sup_admin/", profile_sup_admin, name="user/profile_sup_admin"),
    path("edit_profile_photo", edit_profile_photo, name="edit_profile_photo"),
    path("user/permission/<str:user_id>", permission, name="user/permission"),
    path("upadate_permission", update_permission, name="update_permission"),
    path("permission/ajax_active_permission/<str:actif>", ajax_active_permission, name="ajax_active_permission"),
    path("permission/ajax_staff_permission/<str:staff>", ajax_staff_permission, name="ajax_staff_permission"),
    path("permission/ajax_superuser_permission/<str:superuser>", ajax_superuser_permission, name="ajax_superuser_permission"),
    # Changer le mot de passe
    path("password_change", CustomPasswordChangeView.as_view(), name="password_change"),   
    path("password_change/done/", CustomPasswordChangeDoneView.as_view(), name="password_change_done"),
    # Réinitailisation du mot de passe
    path("reset_password", CustomPasswordResetView.as_view(), name="reset_password"),   
    path("reset_password_sent", CustomPasswordResetDoneView.as_view(), name="password_reset_done"),   
    path("reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),    
    path("reset_password_complet", CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    # Gestion des parents
    path("parent/parents", parents, name="parent/parents"),
    path("parent/detail_parent/<str:id>", detail_parent, name="parent/detail_parent"),
    path("parent/parent_parent/profil_parent", profile_parent, name="parent/profile_parent"),
    path("parent/add_parent", add_parent, name="parent/add_parent"),
    path("parent/edit_parent/<str:id>", edit_parent, name="parent/edit_parent"),
    path("edit_pa", edit_pa, name="edit_pa"),
    path("del_parent/<str:id>", del_parent, name="del_parent"),
    path("parent/delete_parent/<str:id>", delete_parent, name="parent/delete_parent"),
    path("update_password_parent", update_password_parent, name="update_password_parent"),
    # Gestion des étudiants
    path("student/students", students, name="student/students"),
    path("student/detail_student/<str:id>", detail_student, name="student/detail_student"),
    path("student/profil_student", profile_student, name="student/profile_student"),
    path("student/add_student", add_student, name="student/add_student"),
    path("student/edit_student/<str:id>", edit_student, name="student/edit_student"),
    path("edit_st", edit_st, name="edit_st"),
    path("del_student/<str:id>", del_student, name="del_student"),
    path("update_password", update_password, name="update_password"),
    
    path("group/groups", groupes, name="group/groups"),
    path("group/add_group", add_group, name="group/add_group"),
    path("group/edit_group/<str:id>", edit_group, name="group/edit_group"),
    path("edit_gr", edit_gr, name="edit_gr"),
    path("del_group/<str:id>", del_group, name="del_group"),
    
    path("group/group_users", group_users, name="group/group_users"),
    path("group/add_group_user", add_group_user, name="group/add_group_user"),
    path("group/edit_group_user/<str:id>", edit_group_user, name="group/edit_group_user"),
    path("del_group_user/<str:id>", del_group_user, name="del_group_user"),
    
    path("group/admin_group/<str:id>", admin_group, name="group/admin_group"),
    path("add_admin_to_group", add_admin_to_group, name="add_admin_to_group"),
    path("del_user_to_group/<str:id>/<str:name>", del_user_to_group, name="del_user_to_group"),
    
    path("role/roles", roles, name="role/roles"),
    path("role/add_role", add_role, name="role/add_role"),
    path("role/edit_role/<str:id>", edit_role, name="role/edit_role"),
    path("edit_ro", edit_ro, name="edit_ro"),
    path("role/ajax_delete_role/<int:id>", ajax_delete_role, name="ajax_delete_role"),
    path("del_role/<str:id>", del_role, name="del_role"),
    
    path("group/group_etablissement_user/<str:id>", group_etablissement_user, name="group/group_etablissement_user"),
    path("add_group_etablissement_to_user", add_group_etablissement_to_user, name="add_group_etablissement_to_user"),
    path("del_group_etablissement_to_user/<str:id>", del_group_etablissement_to_user, name="del_group_etablissement_to_user"),

    
]