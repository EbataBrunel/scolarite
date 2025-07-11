# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count
from django.db.models import Q
# Importation des modules locaux
from .models import Contact, Message
from school.views import get_setting
from app_auth.decorator import unauthenticated_customer, allowed_users
from app_auth.models import Student, Parent, EtablissementUser
from inscription.models import Inscription
from etablissement.models import Etablissement
from scolarite.utils.crypto import dechiffrer_param


permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']
permission_directeur_etudes = ['Promoteur', 'Directeur Général', 'Directeur des Etudes']
permission_enseignant = ['Enseignant']

@unauthenticated_customer
def contacts(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        student_id = request.session.get('student_id')
        parent_id = request.session.get('parent_id')
        if student_id:
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id, sending_status=True).order_by("-id")
            for contact in contacts:
                contact.reading_status = 1
                contact.save()
            
            all_contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).order_by("id")    
            # Liste des sujets
            subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre'] 
            context = {
                "customer": "student",
                "contacts": all_contacts,
                "subjects": subjects,
                "setting": setting
            }
            return render(request, "contacts.html", context)
        
        if parent_id:
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent_id, sending_status=True).order_by("-id")
            for contact in contacts:
                contact.reading_status = 1
                contact.save()
            
            all_contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent_id).order_by("-id")
            # Liste des sujets
            subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre'] 
            context = {
                "customer": "parent",
                "contacts": all_contacts,
                "subjects": subjects,
                "setting": setting
            }
            return render(request, "contacts.html", context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def contact_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    contacts_students = (Contact.objects.values("student_id")
                    .filter(anneeacademique_id=anneeacademique_id, user_id=user_id, sending_status=False, reading_status=0)
                    .annotate(nombre_messages=Count("student_id"))
    )
    nombre_contacts_students = 0
    for contact in contacts_students:
        nombre_contacts_students += contact["nombre_messages"]
        
    contacts_parents = (Contact.objects.values("parent_id")
                    .filter(anneeacademique_id=anneeacademique_id, user_id=user_id, sending_status=False, reading_status=0)
                    .annotate(nombre_messages=Count("parent_id"))
    )
    nombre_contacts_parents = 0
    for contact in contacts_parents:
        nombre_contacts_parents += contact["nombre_messages"]
        
    nombre_contacts = nombre_contacts_students + nombre_contacts_parents
    
    customer =  {"student": "student", "parent": "parent"}       
    context = {
        "nombre_contacts_students": nombre_contacts_students,
        "nombre_contacts_parents": nombre_contacts_parents,
        "nombre_contacts": nombre_contacts,
        "customer": customer,
        "setting": setting
    }
    return render(request, "contact_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def contact_sp_admin(request, customer):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cust = dechiffrer_param(customer)
    
    if cust not in ["student", "parent"]:
        return redirect("settings/authorization")
    
    user_id = request.user.id
    
    if cust == "student":
        
        # Mise à jour de reading_status pour marquer la lecture des messages
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=None, user_id=user_id, reading_status=0, sending_status=False)
        for cont in contacts:
            if cont.student.id: # Verifier s'il s'agit bien du contact de l'étudiant
                cont.reading_status = 1
                cont.save()
                        
        students_groupes = (Contact.objects.values("student_id")
                        .filter(anneeacademique_id=anneeacademique_id, user_id=user_id)
                        .annotate(nombre_messages=Count("student_id"))
        )
        contacts_students = []
        for contact in students_groupes:
            if contact["student_id"]: # Verifie si l'identifiant de l'étudiant existe 
                dernier_contact = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=contact["student_id"], user_id=user_id).order_by("-id")[0]
                if dernier_contact:
                    dic = {}
                    dic["dernier_contact"] = dernier_contact
                    dic["datecontact"] = dernier_contact.datecontact  # Ajout de la date pour le tri
                    # Compter le nombre de nouveaux contacts non lus 
                    dic["nombre_contacts"] = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=contact["student_id"], user_id=user_id, sending_status=False, reading_status=1).count()
                    contacts_students.append(dic)
                    
        # Tri de la liste par datecontact décroissante
        contacts_students_sorted = sorted(contacts_students, key=lambda x: x["datecontact"], reverse=True)
                    
        # Liste des inscriptionns
        inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id)   
        # Liste des sujets
        subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre']      
        context = {
            "contacts_students": contacts_students_sorted,
            "customer": cust,
            "inscriptions": inscriptions,
            "subjects": subjects,
            "setting": setting
        }
        return render(request, "contact_sp_admin.html", context)                          
    
    if cust == "parent":        
        # Mise à jour de reading_status pour marquer la lecture des messages
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=None, user_id=user_id, reading_status=0, sending_status=False)
        for cont in contacts:
            if cont.parent.id: # Verifier s'il s'agit bien du contact d'un parent
                cont.reading_status = 1
                cont.save()
            
        contacts_parents = []
        parents_groupes = (Contact.objects.values("parent_id")
                        .filter(anneeacademique_id=anneeacademique_id, user_id=user_id)
                        .annotate(nombre_messages=Count("parent_id"))
        )
         
        for contact in parents_groupes:
            if contact["parent_id"]:
                dernier_contact = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=contact["parent_id"], user_id=user_id).order_by("-id")[0]
                if dernier_contact:
                    dic = {}
                    dic["dernier_contact"] = dernier_contact
                    dic["datecontact"] = dernier_contact.datecontact
                    # Compter le nombre de nouveaux contacts non lus 
                    dic["nombre_contacts"] =  Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=contact["parent_id"], user_id=user_id, sending_status=False, reading_status=1).count()
                    contacts_parents.append(dic)
        
        # Tri de la liste par datecontact décroissante
        contacts_parents_sorted = sorted(contacts_parents, key=lambda x: x["datecontact"], reverse=True)
        # Liste des parents des étudiants inscris cette année
        tabParents = []
        inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id) 
        for inscription in inscriptions:
            if inscription.student.parent not in tabParents:
                tabParents.append(inscription.student.parent)
        # Liste des sujets
        subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre']        
        context = {
            "contacts_parents": contacts_parents_sorted,
            "customer": cust,
            "parents": tabParents,
            "subjects": subjects,
            "setting": setting
        }
        return render(request, "contact_sp_admin.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def contact_admin_detail(request, customer, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = int(dechiffrer_param(str(id)))
    cust = dechiffrer_param(customer)
    if cust not in ["student", "parent"]:
        return redirect("settings/authorization")
    
    user_id = request.user.id
    
    if cust == "student":
        student = Student.objects.get(id=student_id)
        # Mise à jour de reading_status pour marquer la lecture des messages
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id, user_id=user_id, sending_status=False, reading_status__in=[0,1])
        for cont in contacts:
            if cont.student.id: # Verifier s'il s'agit bien du contact de l'étudiant
                cont.reading_status = 2
                cont.save()
                
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id, user_id=user_id).order_by("id")
        # Liste des sujets
        subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre'] 
        context = {
            "customer": cust,
            "contacts": contacts,
            "student": student,
            "subjects": subjects,
            "setting": setting
        }
        return render(request, "contact_admin_detail.html", context)
    
    if cust == "parent":
        parent = Parent.objects.get(id=id)
        # Mise à jour de reading_status pour marquer la lecture des messages
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=id, user_id=user_id, sending_status=False, reading_status__in=[0,1])
        for cont in contacts:
            if cont.parent.id: # Verifier s'il s'agit bien du contact d'un parent
                cont.reading_status = 2
                cont.save()
                
                
        contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=id, user_id=user_id).order_by("id")
        # Liste des sujets
        subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre']  
        context = {
            "customer": cust,
            "contacts": contacts,
            "parent": parent,
            "setting": setting,
            "subjects": subjects
        }
        return render(request, "contact_admin_detail.html", context)

@unauthenticated_customer
def add_contact(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    if request.method == "POST":
        user_id = 0
        subject = bleach.clean(request.POST["subject"].strip())
        message = bleach.clean(request.POST["message"].strip())
        
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        
        users = User.objects.all()
        if subject in ["Harcèlement", "Réclamation de notes"]:
            for user in users:
                for role in EtablissementUser.objects.filter(etablissement=etablissement, user=user):
                    if role.group.name  in ["Directeur des Etudes"]:                       
                        user_id = user.id
                            
        if subject in ["Frais de scolarité", 'Autre']:
            for user in users:
                for role in EtablissementUser.objects.filter(etablissement=etablissement, user=user):
                    if role.group.name  in ["Gestionnaire"]:                       
                        user_id = user.id
                                
        type = request.POST["type"]
        if type == "student":
            student_id = request.session.get('student_id')     
            contact = Contact(
                anneeacademique_id=anneeacademique_id,
                subject=subject, 
                message=message, 
                student_id=student_id, 
                reading_status=0,
                sending_status=False,
                user_id=user_id)
            # Nombre de classes avant l'ajout
            count0 = Contact.objects.all().count()
            contact.save()
            # Nombre de classes après l'ajout
            count1 = Contact.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Message envoyé avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Le message n'a pas été envoyé."})
        if type == "parent":
            parent_id = request.session.get('parent_id')     
            contact = Contact(
                anneeacademique_id=anneeacademique_id,
                subject=subject, 
                message=message, 
                parent_id=parent_id,
                reading_status=0,
                sending_status=False,
                user_id=user_id)
            # Nombre de classes avant l'ajout
            count0 = Contact.objects.all().count()
            contact.save()
            # Nombre de classes après l'ajout
            count1 = Contact.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Message envoyé avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Le message n'a pas été envoyé."})


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def del_contact(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        try:
            contact_id = int(dechiffrer_param(str(id)))
            contact = Contact.objects.get(id=contact_id)
        except:
            contact = None
            
        if contact:
            contact.delete()
        return redirect("contacts")

@login_required(login_url='connection/account')    
@allowed_users(allowed_roles=permission_admin)    
def add_contact_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        user_id = request.user.id
        subject = bleach.clean(request.POST["subject"].strip())
        message = bleach.clean(request.POST["message"].strip())
        type = request.POST["type"]
        if type == "student": 
            student_id = request.POST["student_id"]           
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    student_id=student_id, 
                    sending_status=True,
                    user_id=user_id)
            
            contact.save()
            
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id, user_id=user_id).order_by("id")            
            # Liste des sujets
            subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre'] 
            context = {
                "contacts": contacts,
                "subjects": subjects
            }            
            return render(request, "content_contact.html", context)  
        else:
            parent_id = request.POST["parent_id"]
            
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    parent_id=parent_id, 
                    sending_status=True,
                    user_id=user_id)
            
            contact.save()
            
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent_id, user_id=user_id).order_by("id")
            # Liste des sujets
            subjects = ['Réclamation de notes', 'Harcèlement', 'Frais de scolarité', 'Autre'] 
            context = {
                "contacts": contacts,
                "subjects": subjects
            }            
            return render(request, "content_contact.html", context)  

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)       
def add_contact_admin_customer(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        user_id = request.user.id
        subject = bleach.clean(request.POST["subject"].strip())
        message = bleach.clean(request.POST["message"].strip())
        type = request.POST["type"]
        if type == "student": 
            student_id = request.POST["student"]           
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    student_id=student_id, 
                    sending_status=True,
                    user_id=user_id)
            
            contact.save()
                            
            students_groupes = (Contact.objects.values("student_id")
                            .filter(anneeacademique_id=anneeacademique_id, user_id=user_id)
                            .annotate(nombre_messages=Count("student_id"))
            )
            contacts_students = []
            for contact in students_groupes:
                if contact["student_id"]:
                    dic = {}
                    student = Student.objects.get(id=contact["student_id"])
                    dernier_contact = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id, user_id=user_id).order_by("-id")[0]
                    dic["dernier_contact"] = dernier_contact
                    # Compter le nombre de nouveaux contacts non lus 
                    dic["nombre_contacts"] = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id, user_id=user_id, sending_status=False, reading_status=1).count()
                    contacts_students.append(dic)
                
            context = {
                "contacts_students": contacts_students,
                "customer": "student"
            }            
            return render(request, "content_contact_customer.html", context)  
        else:
            parent_id = request.POST["parent"]
            
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    parent_id=parent_id, 
                    sending_status=True,
                    user_id=user_id)
            
            contact.save()
                
            contacts_parents = []
            parents_groupes = (Contact.objects.values("parent_id")
                            .filter(anneeacademique_id=anneeacademique_id, user_id=user_id)
                            .annotate(nombre_messages=Count("parent_id"))
            )
            
            for contact in parents_groupes:
                if contact["parent_id"]:
                    dic = {}
                    parent = Parent.objects.get(id=contact["parent_id"])
                    dernier_contact = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent.id, user_id=user_id).order_by("-id")[0]
                    dic["dernier_contact"] = dernier_contact
                    # Compter le nombre de nouveaux contacts non lus 
                    dic["nombre_contacts"] = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent.id, user_id=user_id, sending_status=False, reading_status=1).count()
                    contacts_parents.append(dic)
            
            context = {
                "contacts_parents": contacts_parents,
                "customer": "parent"
            }            
            return render(request, "content_contact_customer.html", context) 

@unauthenticated_customer
def add_contact_customer(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    if request.method == "POST":
        user_id = 0
        subject = bleach.clean(request.POST["subject"].strip())
        message = bleach.clean(request.POST["message"].strip())
        
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
    
        users = User.objects.all()
        if subject in ["Harcèlement", "Réclamation de notes"]:
            for user in users:
                for role in EtablissementUser.objects.filter(etablissement=etablissement, user=user):
                    if role.group.name in ["Directeur des Etudes"]:                       
                        user_id = user.id
                            
        if subject in ["Frais de scolarité", "Autre"]:
            for user in users:
                for role in EtablissementUser.objects.filter(etablissement=etablissement, user=user):
                    if role.group.name in ["Gestionnaire"]:                       
                        user_id = user.id                            
                            
        if request.session.get('student_id'): 
            student_id = request.session.get('student_id')          
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    student_id=student_id, 
                    sending_status=False,
                    user_id=user_id)
            
            contact.save()
                            
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id, sending_status=True).order_by("id")
            for contact in contacts:
                contact.reading_status = 1
                contact.save()
            
            all_contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).order_by("id")    
            context = {
                "contacts": all_contacts,
            }            
            return render(request, "content_customer.html", context)  
        if request.session.get('parent_id'):
            parent_id = request.session.get('parent_id')
            
            contact = Contact(
                    anneeacademique_id=anneeacademique_id,
                    subject=subject, 
                    message=message, 
                    parent_id=parent_id, 
                    sending_status=False,
                    user_id=user_id)
            
            contact.save()
                
            contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent_id, sending_status=True).order_by("id")
            for contact in contacts:
                contact.reading_status = 1
                contact.save()
                
            all_contacts = Contact.objects.filter(anneeacademique_id=anneeacademique_id, parent_id=parent_id).order_by("id")
            
            context = {
                "contacts": all_contacts
            }            
            return render(request, "content_customer.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)          
def messages(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    
    # Mise à jour de reading_status pour marquer la lecture des messages
    messages = Message.objects.filter(anneeacademique_id=anneeacademique_id, beneficiaire_id=user_id, reading_status=0)
    for message in messages:
            message.reading_status = 1
            message.save()
    
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)                   
    users = User.objects.all().exclude(id=user_id)
    tabUsers = []
    for user in users:
        if etablissement.groups.filter(user=user).exists():
            tabUsers.append(user)
    list_messages = []
    for user in tabUsers:  
        messages = Message.objects.filter(
            Q(expediteur=user_id, beneficiaire=user.id) |
            Q(expediteur=user.id, beneficiaire=user_id)
        ).order_by('-datemessage')
        if messages:
            dic = {}
            dernier_message = messages[0] # Dernier message
            dic["message"] = dernier_message
            dic["datemessage"] = dernier_message.datemessage
            dic["nombre_messages"] = Message.objects.filter(anneeacademique_id=anneeacademique_id, beneficiaire_id=user_id, reading_status=1).count()
            list_messages.append(dic) 
            
    # Tri de la liste des date de message par ordre décroissante
    messages_sorted = sorted(list_messages, key=lambda x: x["datemessage"], reverse=True)  
            
    context = {
        "setting": setting,
        "messages": messages_sorted,
        "users": tabUsers
    }            
    return render(request, "messages.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)   
def detail_message(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Mise à jour de reading_status pour marquer la lecture des messages
    messages = Message.objects.filter(anneeacademique_id=anneeacademique_id, beneficiaire_id=user_id, reading_status__in=[0,1])
    for message in messages:
            message.reading_status = 2
            message.save()
    
    beneficiaire_id = int(dechiffrer_param(str(id)))
    messages = Message.objects.filter(
            Q(expediteur=user_id, beneficiaire=beneficiaire_id) |
            Q(expediteur=beneficiaire_id, beneficiaire=user_id)
        ).order_by('datemessage')
    
    user = User.objects.get(id=beneficiaire_id)
    context = {
        "setting": setting,
        "messages": messages,
        "user": user
    }
    return render(request, "detail_message.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)    
def add_message(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        user_id = request.user.id
        content = bleach.clean(request.POST["content"].strip())
        beneficiaire = request.POST["user"]           
        message = Message(
                    anneeacademique_id=anneeacademique_id,
                    content=content, 
                    expediteur_id=user_id, 
                    beneficiaire_id=beneficiaire,
        )
            
        message.save()
        
        users = User.objects.all().exclude(id=user_id)
        list_messages = []
        for user in users:  
            messages = Message.objects.filter(
                Q(expediteur=user_id, beneficiaire=user.id) |
                Q(expediteur=user.id, beneficiaire=user_id)
            ).order_by('-datemessage')
            if messages:
                list_messages.append(messages[0])
               
        context = {
            "messages": list_messages
        }            
        return render(request, "content_message.html", context)  

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)      
def add_message_user(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        user_id = request.user.id
        content = bleach.clean(request.POST["content"].strip())
        beneficiaire = request.POST["user"]           
        message = Message(
                    anneeacademique_id=anneeacademique_id,
                    content=content, 
                    expediteur_id=user_id, 
                    beneficiaire_id=beneficiaire,
        )
            
        message.save()
                            
        messages = Message.objects.filter(
            Q(expediteur=user_id, beneficiaire=beneficiaire) |
            Q(expediteur=beneficiaire, beneficiaire=user_id)
        ).order_by('datemessage')
    
        context = {
            "messages": messages
        }           
        return render(request, "content_message_user.html", context)  