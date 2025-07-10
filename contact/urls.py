from django.urls import path
from .views import*
#from django.contrib.auth import views as auth_views

urlpatterns=[
    path("contacts", contacts, name="contacts"),
    path("contact-admin", contact_admin, name="contact_admin"),
    path("contact-sp-admin/<str:customer>", contact_sp_admin, name="contact_sp_admin"),
    path("contact_admin_detail/<str:customer>/<str:id>", contact_admin_detail, name="contact_admin_detail"),
    path("add-contact", add_contact, name="add_contact"),
    path("del-contact/<str:id>", del_contact, name="del_contact"),
    
    path("add-contact-admin", add_contact_admin, name="add_contact_admin"),
    path("add_contact-admin-customer", add_contact_admin_customer, name="add_contact_admin_customer"),
    path("add-contact-customer", add_contact_customer, name="add_contact_customer"),
    
    path("messages", messages, name="messages"),
    path("detail-message/<str:id>", detail_message, name="detail_message"),
    path("add_message", add_message, name="add_message"),
    path("add_message_user", add_message_user, name="add_message_user")
]