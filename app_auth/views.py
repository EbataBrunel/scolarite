# Importation des modules standards
import re
import bleach
import os

from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import views as auth_views
from django.db.models import Count
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy

# Importation des modules locaux
from .tokens import account_activation_token
from school.views import get_setting_sup_user, get_setting 
from .utils import send_email_with_html_body
from .decorator import*
from .models import *
from .forms import *
from etablissement.models import Etablissement
from anneeacademique.models import AnneeCademique
from inscription.models import Inscription
from enseignement.models import Enseigner
from renumeration.models import Contrat, Renumeration
from absence.models import Absence, AbsenceAdmin
from emargement.models import Emargement
from paiement.models import Payment, AutorisationPayment, AutorisationPaymentSalle, ContratEtablissement 
from depense.models import Depense
from composition.models import Composer
from school.models import Setting, SettingSupUser
from scolarite.utils.crypto import chiffrer_param, dechiffrer_param

permission_user = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Surveillant Général", "Enseignant"]
permission_admin = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Surveillant Général"]
permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_sup_user_promoteur = ['Promoteur', 'Directeur Général', 'Super user', 'Super admin']
permission_sup_user = ["Super user", "Super admin"]
permission_gestionnaire = ['Promoteur', 'Directeur Général', 'Gestionnaire']

# Trier les noms des groups par ordre de chef
def trier_group_name(tab_names_groups):
    group_name = ""
    if "Super user" in tab_names_groups:
        group_name = "Super user"
    elif "Super admin" in tab_names_groups:
        group_name = "Super admin"
    elif "Promoteur" in tab_names_groups:
        group_name = "Promoteur"
    elif "Directeur Général" in tab_names_groups:
        group_name = "Directeur Général"
    elif "Directeur des Etudes" in tab_names_groups:
        group_name = "Directeur des Etudes"
    elif "Gestionnaire" in tab_names_groups:
        group_name = "Gestionnaire"
    elif "Surveillant Général" in tab_names_groups:
        group_name = "Surveillant Général"
    else:
        group_name = "Enseignant"
        
    return group_name

@transaction.atomic
def add_annee_setting(request):   

    if request.method == "POST":
        #==================== Information de l'année académique ==========================
        annee_debut = bleach.clean(request.POST["annee_debut"].strip())
        annee_fin = bleach.clean(request.POST["annee_fin"].strip())
        separateur = request.POST["separateur"]
        start_date = bleach.clean(request.POST["start_date"].strip())
        end_date = bleach.clean(request.POST["end_date"].strip())
        
        # Information du paramètre
        appname = bleach.clean(request.POST["appname"].strip())
        appeditor = bleach.clean(request.POST["appeditor"].strip())
        version = bleach.clean(request.POST["version"].strip())
        theme = request.POST["theme"].strip()
        text_color = request.POST["text_color"]
        address = bleach.clean(request.POST["address"].strip())
        devise = bleach.clean(request.POST["devise"].strip())
        email = request.POST["email"]
        phone = bleach.clean(request.POST["phone"].strip())
        width = request.POST["width"].strip()
        height = request.POST["height"].strip()
        
        
        logo = None
        # Difference entre les deux années
        diff_annee = int(annee_debut) - int(annee_fin)
        query = AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin)
        regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
        
        if request.POST.get('logo', True):
            logo = request.FILES["logo"]       
        
        if not re.search(regexp, email): #On verifie si l'adresse e-mail correspond bien
            return JsonResponse({
                "status": "error",
                "message": "Le format de l'adresse e-mail ne correspond pas."})
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette année scolaire existe déjà."})
        if diff_annee >= 0:
            return JsonResponse({
                    "status": "error",
                    "message": "L'année du début doit être supérieure à l'année de fin."})
        if  diff_annee != -1:
            return JsonResponse({
                    "status": "error",
                    "message": "L'année de fin doit être supérieure à l'année de début de 1 an."})
        else:
            anneeacademique = AnneeCademique(
                    annee_debut=annee_debut, 
                    annee_fin=annee_fin, 
                    separateur=separateur,
                    start_date=start_date,
                    end_date=end_date)
            # Nombre d'années académiques avant l'ajout
            count0 = AnneeCademique.objects.all().count()
            anneeacademique.save()
            # Nombre d'années académiques après l'ajout
            count1 = AnneeCademique.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:                     
                    
                sett = SettingSupUser(
                        appname=appname,
                        appeditor=appeditor,
                        version=version,
                        theme=theme,
                        text_color=text_color,
                        devise=devise,
                        address=address,
                        email=email,
                        phone=phone,
                        logo=logo,
                        width_logo=width,
                        height_logo=height
                )
                # Nombre de paramètre avant l'ajout
                count2 = SettingSupUser.objects.all().count()
                sett.save()  
                # Nombre de paramètre après l'ajout
                count3 = SettingSupUser.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas. 
                if count2 < count3:              
                    return JsonResponse({
                        "status": "success",
                        "message": "Année scolaire et paramètre enregistrées avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."}) 
                
    return render(request, "add_annee_setting.html")

@transaction.atomic
def register_supuser(request):
    setting = get_setting_sup_user()
    form = UserForm()
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            #On verifie si l'adresse e-mail correspond bien
            regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
            if not re.search(regexp, email):
                messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
            else:
                query = User.objects.filter(email=email)
                if query.exists():
                    messages.error(request, "L'adresse e-mail renseignée existe déjà.") 
                else:
                    count0 = User.objects.all().count()
                    user = form.save() 
                    #On desactive l'accès du membre
                    user.is_active = False
                    user.save()
                    #On recupere nombre total des membres après la création du compte
                    count1 = User.objects.all().count()
                    #On envoie l'e-mail au membre pour activer son compte
                    subject = "Activation de compte"
                    template = "email/emailactivation.html"
                    receivers = [email]
                    
                    context = {
                        "domain":get_current_site(request).domain,
                        "uid":urlsafe_base64_encode(force_bytes(user.pk)),
                        "token":account_activation_token.make_token(user),
                        "protocol": 'https' if request.is_secure() else 'http',
                        "user":user,
                        "setting":setting,
                    }
                    has_send = send_email_with_html_body(
                        subject = subject,
                        receivers = receivers,
                        template = template,
                        context = context
                    )
                    
                    if count0 < count1 and has_send == True:
                        return redirect("user/success-account", chiffrer_param(str(user.id)))
                    else:
                        messages.error(request, "Inscription a échouée.")
                        context = {
                            "form": form,
                            "setting": setting
                        }
                        return render(request, "user/register_supuser.html", context) 
        else:
            # Personnalisation des erreurs
            for field, errors in form.errors.items():
                for error in errors:
                    # Si l'erreur concerne les mots de passe, afficher un message générique
                    if "Les deux mots de passe ne correspondent pas" in error:
                        messages.error(request, "Les deux mots de passe ne correspondent pas.")
                    else:
                        messages.error(request, error)
            context = {
                "form": form,
                "setting": setting
            }
            return render(request, "user/register_supuser.html", context)

    context = {
        "form": form,
        "setting": setting
    }
    return render(request, "user/register_supuser.html", context)

def success_account(request, id):
    setting = get_setting_sup_user()
    if setting is None:
        redirect("settings/maintenance")
    else:
        try:
            user_id = int(dechiffrer_param(str(id)))
            user = User.objects.get(id=user_id)
        except:
            user = None
            
        if user:
            context = {
                "user": user,
                "setting": setting
            }
            return render(request, "user/success-account.html", context)
        else:
            return redirect("user/register_supuser")

@transaction.atomic
def register(request):
    setting = get_setting_sup_user()
    # Récuperer la dernière académique du groupe
    anneeacademique_group = AnneeCademique.objects.filter(etablissement=None).order_by("-annee_debut").first()  
    # Récuperer des années académiques
    anneeacademiques = AnneeCademique.objects.filter(annee_debut=anneeacademique_group.annee_debut, annee_fin=anneeacademique_group.annee_fin).exclude(etablissement=None).order_by("etablissement")
    # Récuperer les établissements aux quels on a signé le contrat
    etablissements = []
    for anneeacademique in anneeacademiques:
        if ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique.etablissement).exists():
            etablissements.append(anneeacademique.etablissement)
    group = Group.objects.get(name="Enseignant")
    if anneeacademique_group is None or group is None: 
        return redirect("settings/maintenance")
    form = UserForm()
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            etablissement_id = bleach.clean(request.POST["etablissement"].strip())
            email = form.cleaned_data.get("email")
            #On verifie si l'adresse e-mail correspond bien
            regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
            if not re.search(regexp, email):
                messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
            else:
                query = User.objects.filter(email=email)
                if query.exists():
                    messages.error(request, "L'adresse e-mail renseignée existe déjà.") 
                else:
                    count0 = User.objects.all().count()
                    user = form.save() 
                    # Récuperer l'établissement
                    etablissement = Etablissement.objects.get(id=etablissement_id)
                    # Associer l'utilisateur à l'établissement
                    EtablissementUser.objects.create(
                        group=group,
                        etablissement=etablissement,
                        user=user
                    )
                    #On desactive l'accès du membre
                    user.is_active = False
                    user.save()
                    #On recupere nombre total des membres après la création du compte
                    count1 = User.objects.all().count()
                    #On recupere nombre total des membres après la création du compte
                    count1 = User.objects.all().count()
                    #On envoie l'e-mail au membre pour activer son compte
                    subject = "Activation de compte"
                    template = "email/emailactivation.html"
                    receivers = [email]
                    
                    context = {
                        "domain":get_current_site(request).domain,
                        "uid":urlsafe_base64_encode(force_bytes(user.pk)),
                        "token":account_activation_token.make_token(user),
                        "protocol": 'https' if request.is_secure() else 'http',
                        "user":user,
                        "setting":setting,
                    }
                    has_send = send_email_with_html_body(
                        subject = subject,
                        receivers = receivers,
                        template = template,
                        context = context
                    )
                    
                    if count0 < count1 and has_send == True:
                        return redirect("user/success-account-etablissement", chiffrer_param(str(user.id)), chiffrer_param(str(etablissement.id)))
                    else:
                        messages.error(request, "Inscription a échouée.")
                        context = {
                            "form": form,
                            "setting": setting,
                            "etablissements": etablissements
                        }
                        return render(request, "user/register.html", context) 
        else:
            # Personnalisation des erreurs
            for field, errors in form.errors.items():
                for error in errors:
                    # Si l'erreur concerne les mots de passe, afficher un message générique
                    if "Les deux mots de passe ne correspondent pas" in error:
                        messages.error(request, "Les deux mots de passe ne correspondent pas.")
                    else:
                        messages.error(request, error)
            context = {
                "form": form,
                "setting": setting,
                "etablissements": etablissements
            }
            return render(request, "user/register.html", context)

    context = {
        "form": form,
        "setting": setting,
        "etablissements": etablissements
    }
    return render(request, "user/register.html", context)

def success_account_etablissement(request, user_id, etablissement_id):
    etab_id = int(dechiffrer_param(str(etablissement_id)))   
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etab_id)
    anneeacademique = AnneeCademique.objects.filter(etablissement_id=etablissement.id).order_by("-annee_debut").first()
    setting = get_setting(anneeacademique.id)
    if setting is None:
        redirect("settings/maintenance")
    else:
        try:
            id = int(dechiffrer_param(str(user_id)))
            user = User.objects.get(id=id)
        except:
            user = None
            
        if user:
            context = {
                "user": user,
                "etablissement": etablissement,
                "setting": setting
            }
            return render(request, "user/success-account-etablissement.html", context)
        else:
            return redirect("user/register")
    
#Activation du compte
def activate(request, uidb64, token):
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(id=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        # Vérifier si l'utilisateur a un établissement 
        if EtablissementUser.objects.filter(user=user).exists():
            messages.success(request, "Activation effectuée avec succès. Vous pouvez alors vous connecter.")
            return redirect("connection/account")
        else:
            messages.success(request, "Activation effectuée avec succès. Vous pouvez alors vous connecter.")
            return redirect("connection/login")
    else:
         messages.error(request, "Le lien d'activation est invalide")

    return redirect("connection/login")

def login_user(request):
    #Destruction de toutes les sessions
    logout(request)
    request.session.clear()
                
    nb_anneeacademiques = AnneeCademique.objects.filter(etablissement=None).count()
    if nb_anneeacademiques == 0: 
        return redirect("add_annee_setting")
    
    request.session.clear()
    setting = get_setting_sup_user()
    anneeacademique = AnneeCademique.objects.filter(etablissement=None).order_by("-id").first()
    if request.method == "POST":
        form = LoginForm(request.POST)
        # Verifier la validité du formulaire
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user is not None:
                #Création des sessions
                login(request, user)
                request.session["annee_id"] = anneeacademique.id
                request.session["annee_d"] = anneeacademique.annee_debut
                request.session["annee_f"] = anneeacademique.annee_fin
                request.session["sep"] = anneeacademique.separateur
                
                if user.groups.exists():
                    groups = user.groups.all()
                    # Récupérer le group principal
                    tab_names_groups = [] 
                    for group in groups:
                        if group.name in ["Super user", "Super admin"]:
                            tab_names_groups.append(group.name)
                            
                    if len(tab_names_groups) == 0:
                        context = {
                            "form": form,
                            "setting": setting
                        }
                        messages.error(request, "Vous n'avez pas de permission")
                        return render(request, "connection/login.html", context)     
                    group_name = trier_group_name(tab_names_groups)
                    request.session["group_name"] = group_name
                    if user.is_active:
                        query = SettingSupUser.objects.all()
                        if query.exists():
                            return redirect("index")
                        else:
                            redirect("add_annee_setting")
                    else:
                        context = {
                                    "form": form,
                                    "setting": setting
                        }
                        messages.error(request, "Vous n'avez pas de permission")
                        return render(request, "connection/login.html", context)
                else:
                    context = {
                                "form": form,
                                "setting": setting
                    }
                    messages.error(request, "Vous n'êtes pas associés à un groupe")
                    return render(request, "connection/login.html", context)                       
                
            context = {
                "form": form,
                "setting": setting
            }
            messages.error(request, "Erreur d'authentification")
            return render(request, "connection/login.html", context)
        else:
            for field in form.errors:
                form[field].field.widget.attrs['class']+='is-invalid'
            
            context = {
                "form": form,
                "setting": setting
            }
            return render(request, "connection/login.html", context)
    else:
        form = LoginForm()
        context = {
            "form": form,
            "setting": setting
        }
        return render(request, "connection/login.html", context)
    
def logout_user(request):

    group_name = request.session.get('group_name') 
    
    if group_name in ["Super user", "Super admin"]:
        logout(request)
        for key in request.session.keys():
                del request.session[key]
        return redirect("connection/login")
    else:
        logout(request)
        for key in request.session.keys():
            del request.session[key]
        return redirect("connection/account")
            
            
def account_user(request):
    #Destruction de toutes les sessions
    logout(request)
    request.session.clear()
    # Récuperer la dernière académique du groupe
    anneeacademique_group = AnneeCademique.objects.filter(etablissement=None).order_by("-annee_debut").first()
    if anneeacademique_group is None: 
        return redirect("settings/maintenance")
      
    setting = get_setting_sup_user()   
    # Récuperer des années académiques
    anneeacademiques = AnneeCademique.objects.filter(annee_debut=anneeacademique_group.annee_debut, annee_fin=anneeacademique_group.annee_fin).exclude(etablissement=None).order_by("etablissement")
    # Récuperer les établissements aux quels on a signé le contrat
    etablissements = []
    for anneeacademique in anneeacademiques:
        if ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique.etablissement).exists():
            etablissements.append(anneeacademique.etablissement)
    request.session["form"] = True
    if request.method == "POST":
        form = LoginForm(request.POST)
        # Verifier la validité du formulaire
        if form.is_valid():
            etablissement_id = bleach.clean(request.POST["etablissement"].strip())
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            # Récuperer l'établissement
            etablissement = Etablissement.objects.get(id=etablissement_id)
            if AnneeCademique.objects.filter(etablissement=etablissement, status_access=False).order_by("-annee_debut").first():
                request.session["interdiction"] = True
                return redirect("settings/authorization_etablissement", chiffrer_param(str(etablissement_id)))
            if user is not None:
                roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
                if roles.exists():
                    #Création des sessions
                    login(request, user)
                    # Récuperer l'année académique de l'établissement
                    anneeacademique = AnneeCademique.objects.filter(
                        annee_debut=anneeacademique_group.annee_debut, 
                        annee_fin=anneeacademique_group.annee_fin, 
                        etablissement=etablissement).first()
                    
                    request.session["anneeacademique_id"] = anneeacademique.id
                    request.session["annee_debut"] = anneeacademique.annee_debut
                    request.session["annee_fin"] = anneeacademique.annee_fin
                    request.session["separateur"] = anneeacademique.separateur
                    
                    request.session["etablissement_id"] = etablissement.id
                    # Récupérer le group principal
                    tab_names_groups = [] 
                    for role in roles:
                        tab_names_groups.append(role.group.name)
                    
                    group_name = trier_group_name(tab_names_groups)
                    request.session["group_name"] = group_name
                    if user.is_active:
                        if roles.first()  or etablissement.promoteur == user:
                            return redirect("settings/db_cycle", chiffrer_param(str(etablissement.id)))
                        else:
                            return redirect("settings/authorization")
                    else:
                        context = {
                            "form": form,
                            "etablissements": etablissements,
                            "setting": setting
                        }
                        messages.error(request, "Vous n'avez pas de permission")
                        return render(request, "connection/account.html", context) 
                else:
                    context = {
                            "form": form,
                            "etablissements": etablissements,
                            "setting": setting
                    }
                    messages.error(request, "Vous n'êtres pas membre de cet établissement, selectionnez correctement votre établissement")
                    return render(request, "connection/account.html", context)                      

            context = {
                "form": form,
                "etablissements": etablissements,
                "setting": setting
            }
            messages.error(request, "Erreur d'authentification")
            return render(request, "connection/account.html", context)
        else:
            for field in form.errors:
                form[field].field.widget.attrs['class']+='is-invalid'
            
            context = {
                "form": form,
                "etablissements": etablissements,
                "setting": setting
            }
            return render(request, "connection/account.html", context)       

    form = LoginForm()
    context = {
        "form": form,
        "etablissements": etablissements,
        "setting": setting
    }
    return render(request, "connection/account.html", context)
            
def login_customer(request):
    # Récuperer la dernière académique du groupe
    anneeacademique_group = AnneeCademique.objects.filter(etablissement=None).order_by("-annee_debut").first()
    if anneeacademique_group is None: 
        return redirect("settings/maintenance")
      
    setting = get_setting_sup_user()   
    # Récuperer des années académiques
    anneeacademiques = AnneeCademique.objects.filter(annee_debut=anneeacademique_group.annee_debut, annee_fin=anneeacademique_group.annee_fin).exclude(etablissement=None).order_by("etablissement")
    # Récuperer les établissements aux quels on a signé le contrat
    etablissements = []
    for anneeacademique in anneeacademiques:
        if ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique.etablissement).exists():
            etablissements.append(anneeacademique.etablissement)   
    if request.method == "POST":
        etablissement_id = bleach.clean(request.POST["etablissement"].strip())
        username = request.POST["username"]
        password = request.POST["password"]
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        query_parent = Parent.objects.filter(username=username, password=password, etablissement_id=etablissement.id)
        query_student = Student.objects.filter(username=username, password=password, etablissement_id=etablissement.id)
        
        # Récuperer l'année académique de l'établissement
        anneeacademique = AnneeCademique.objects.filter(
                        annee_debut=anneeacademique_group.annee_debut, 
                        annee_fin=anneeacademique_group.annee_fin, 
                        etablissement=etablissement).first()
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        if AnneeCademique.objects.filter(etablissement=etablissement, status_access=False).order_by("-annee_debut").first():
            request.session["interdiction"] = False
            return redirect("settings/authorization_etablissement", chiffrer_param(str(etablissement_id)))
        if query_student.exists() or query_parent.exists():
            if query_student.exists():
                student = query_student.first()
                #Verifier l'inscription de l'étudiant
                query_inscription = Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique.id)
                if query_inscription.exists():
                    inscription = query_inscription.first()
                    if inscription.status_access:
                        if inscription.status_block:
                            request.session["anneeacademique_id"] = anneeacademique.id
                            request.session["annee_debut"] = anneeacademique.annee_debut
                            request.session["annee_fin"] = anneeacademique.annee_fin
                            request.session["separateur"] = anneeacademique.separateur
                            request.session["start_date"] = str(anneeacademique.start_date)
                            request.session["end_date"] = str(anneeacademique.end_date)
                            
                            request.session["student_id"] = student.id
                            request.session["lastname"] = student.lastname
                            request.session["firstname"] = student.firstname
                            request.session["photo"] = inscription.photo.url
                            request.session["username"] = student.username
                            
                            return redirect("settings/home")
                        else:
                            context = {
                                "setting": setting,
                                "etablissements": etablissements
                            }
                            messages.error(request, "Votre compte a été définitivement bloqué. Vous pouvez donc contacter la direction de l'école pour plus d'informations.")
                            return render(request, "connection/connexion.html", context)
                    else:
                        context = {
                            "setting": setting,
                            "etablissements": etablissements
                        }
                        messages.error(request, "Votre compte a été provisoirement bloqué. Vous pouvez donc contacter la direction de l'école pour plus d'informations.")
                        return render(request, "connection/connexion.html", context)
                else:
                    context = {
                        "setting": setting,
                        "etablissements": etablissements
                    }
                    messages.error(request, f"Vous n'êtes pas inscris pour l'année scolaire {anneeacademique.annee_debut}{anneeacademique.separateur}{anneeacademique.annee_fin}")
                    return render(request, "connection/connexion.html", context)
            else:
                parent = query_parent.first()
                if parent.status_access:
                    students = Student.objects.filter(parent_id=parent.id)
                    nombre_inscris = 0 # Deteterminer si au moins un enfant du parent estb inscris cette année
                    nombre_compte_bloque = 0 # Determiner le nombre des enfants qui ont été bloqués
                    for student in students:
                        #Verifier l'inscription de l'étudiant
                        query = Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique.id)
                        if query.exists():
                            nombre_inscris += 1
                            inscription = query.first()
                            if inscription.status_block == False: # Verifier si le compte de l'étudiant a été bloqué.
                                nombre_compte_bloque += 1                           
                        
                    if nombre_inscris > 0:
                        if nombre_inscris != nombre_compte_bloque:
                            request.session["anneeacademique_id"] = anneeacademique.id
                            request.session["annee_debut"] = anneeacademique.annee_debut
                            request.session["annee_fin"] = anneeacademique.annee_fin
                            request.session["separateur"] = anneeacademique.separateur
                            request.session["start_date"] = str(anneeacademique.start_date)
                            request.session["end_date"] = str(anneeacademique.end_date)
                            
                            request.session["parent_id"] = parent.id
                            request.session["lastname"] =  parent.lastname
                            request.session["firstname"] =  parent.firstname
                            request.session["username"] =  parent.username
                            
                            return redirect("settings/home")
                        else:
                            context = {
                                "setting": setting,
                                "etablissements": etablissements
                            }
                            messages.error(request, "Votre compte a été définitivement bloqué. Vous pouvez donc contacter la direction de l'école pour plus d'informations.")
                            return render(request, "connection/connexion.html", context)
                    else:
                        context = {
                            "setting": setting,
                            "etablissements": etablissements
                        }
                        messages.error(request, f"Aucun de vos enfants est inscris pour l'année scolaire {anneeacademique.annee_debut}{anneeacademique.separateur}{anneeacademique.annee_fin}")
                        return render(request, "connection/connexion.html", context)
                else:
                    context = {
                        "setting": setting,
                        "etablissements": etablissements
                    }
                    messages.error(request, "Votre compte a été provisoirement bloqué. Vous pouvez donc contacter la direction de l'école pour plus d'informations.")
                    return render(request, "connection/connexion.html", context)
        else:
            context = {
                "setting": setting,
                "etablissements": etablissements
            }
            messages.error(request, "Erreur d'authentification")
            return render(request, "connection/connexion.html", context)
    
    else:
        context = {
            "setting": setting,
            "etablissements": etablissements
        }
        return render(request, "connection/connexion.html", context)
    

def logout_customer(request):    
    for key in list(request.session.keys()):  # Utiliser une copie des clés
        del request.session[key]
    return redirect("connection/connexion")

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def detail_supuser(request, id):
    setting = get_setting_sup_user()
    user_id = int(dechiffrer_param(str(id)))
    user = User.objects.get(id=user_id)
    context = {
        "setting": setting,
        "user": user
    }
    return render(request, "user/detail_supuser.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def del_supuser(request, id):
    try:
        user_id = int(dechiffrer_param(str(id)))
        user = User.objects.get(id=user_id)
    except:
        user = None
    
    if user:
        # Nombre d'utilisateurs avant la suppression
        count0 = User.objects.all().count()
        user.delete()
        # Nombre d'utilisateurs après la suppression
        count1 = User.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("user/super_users")
    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def promoteurs(request):
    setting = get_setting_sup_user()
    # Récuperer les administrateurs
    promoteurs = []
    users = []
    for role in EtablissementUser.objects.all():
        if role.group.name == "Promoteur":
            if role.user not in users:
                dic = {}
                dic["promoteur"] = role.user 
                etablissements = role.user.etablissements.all()  
                dic["etablissements"] = etablissements
                dic["nombre_etablissements"] = etablissements.count() # Nombre d'établissements   
                promoteurs.append(dic)
                users.append(role.user)
        
    context = {
            "setting": setting,
            "promoteurs": promoteurs,
            "permission": permission_promoteur_DG
    }
    return render(request, "user/promoteurs.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def detail_promoteur(request, id):
    setting = get_setting_sup_user()
    user_id = int(dechiffrer_param(str(id)))
    promoteur = User.objects.get(id=user_id)
    
    etablissements = Etablissement.objects.filter(promoteur=promoteur)
    context = {
        "setting": setting,
        "promoteur": promoteur,
        "etablissements": etablissements
    }
    return render(request, "user/detail_promoteur.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def delete_promoteur(request, id):
    setting = get_setting_sup_user()
    if setting is None:
        return redirect("settings/maintenance")
    
    user = User.objects.get(id=id)
    nombre = {}
    nombre["nombre_etablissements"] = Etablissement.objects.filter(promoteur=user).count()
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
   
    context = {
        "setting": setting,
        "admin": user,
        "nombre_total": nombre_total,
        "nombre": nombre,
    }
    return render(request, "user/delete_promoteur.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def del_promoteur(request, id):
    try:
        user_id = int(dechiffrer_param(str(id)))
        user = User.objects.get(id=user_id)
    except:
        user = None
    
    if user:
        # Nombre d'utilisateurs avant la suppression
        count0 = User.objects.all().count()
        user.delete()
        # Nombre d'utilisateurs après la suppression
        count1 = User.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("user/promoteurs")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def administrator(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        # Récuperer les administrateurs
        administrateurs = []
        users = []
        roles = EtablissementUser.objects.filter(etablissement=etablissement)                       
        for role in roles:
            if role.group.name in permission_admin:      
                dic = {}
                dic["user"] = role.user
                dic["roles"] = EtablissementUser.objects.filter(etablissement=etablissement, user=role.user)
                dic["nombre_groupes"] = EtablissementUser.objects.filter(etablissement=etablissement, user=role.user).count() # Nombre de groupes de l'utilisateur
                if role.user not in users:
                    users.append(role.user)
                    administrateurs.append(dic)
        
        context = {
                "setting": setting,
                "administrateurs": administrateurs,
                "permission": permission_promoteur_DG
        }
        return render(request, "user/admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def detail_admin(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        
        user_id = int(dechiffrer_param(str(id)))
        user = User.objects.get(id=user_id)
        roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
        context = {
            "setting": setting,
            "user": user,
            "roles": roles
        }
        return render(request, "user/detail_admin.html", context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_admin(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    user = User.objects.get(id=user_id)
    nombre = {}
    nombre["nombre_contrats"] = Contrat.objects.filter(user_id=user.id).count()
    nombre["nombre_enseignements"] = Enseigner.objects.filter(enseignant_id=user.id).count()
    nombre["nombre_renumerations"] = Renumeration.objects.filter(user_id=user.id).count()
    nombre["nombre_absences_enseignants"] = Absence.objects.filter(enseignant_id=user.id).count()
    nombre["nombre_emargements"] = Emargement.objects.filter(enseignant_id=user.id).count()
    
    nombre["nombre_contrats_admin"] = Contrat.objects.filter(admin_id=user.id).count()
    nombre["nombre_renumerations_admin"] = Renumeration.objects.filter(type_renumeration="Administrateur scolaire", user_id=user.id).count()
    nombre["nombre_paiements"] = Payment.objects.filter(user_id=user.id).count()
    nombre["nombre_autorisation_payements_students"] = AutorisationPayment.objects.filter(user_id=user.id).count()
    nombre["nombre_autorisation_payements_salles"] = AutorisationPaymentSalle.objects.filter(user_id=user.id).count()
    nombre["nombre_absences_admin"] = AbsenceAdmin.objects.filter(user_id=user.id).count()
    nombre["nombre_compositions"] = Composer.objects.filter(user_id=user.id).count()
    nombre["nombre_emargements_admin"] = Emargement.objects.filter(user_id=user.id).count()
    nombre["nombre_depenses"] = Depense.objects.filter(user_id=user.id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
    
    groups = user.groups.all()    
    context = {
        "setting": setting,
        "admin": user,
        "nombre_total": nombre_total,
        "nombre": nombre,
        "groups": groups
    }
    return render(request, "user/delete_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_admin(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        user_id = int(dechiffrer_param(str(id)))
        admin = User.objects.get(id=user_id)
    except:
        admin = None
    
    if admin:
        # Nombre d'utilisateurs avant la suppression
        count0 = User.objects.all().count()
        admin.delete()
        # Nombre d'utilisateurs après la suppression
        count1 = User.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("user/admin")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def teachers(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        roles = EtablissementUser.objects.filter(etablissement=etablissement)
        enseignants = []
        users = []            
        for role in roles:
            dic = {}
            dic["user"] = role.user
            dic["roles"] = EtablissementUser.objects.filter(user=role.user, etablissement=etablissement) 
            dic["nombre_groupes"] = EtablissementUser.objects.filter(user=role.user, etablissement=etablissement).count() # Nombre de groupes de l'utilisateur
            if role.group.name == "Enseignant":   
                if role.user not in users:
                    users.append(role.user)
                    enseignants.append(dic)
        context = {
            "setting": setting,
            "enseignants": enseignants,
            "permission": permission_promoteur_DG
        }
        return render(request, "teacher/teachers.html", context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def detail_teacher(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        user_id = int(dechiffrer_param(str(id)))
        user = User.objects.get(id=user_id)
        
        #Récuperer l'établissement 
        etablissement = Etablissement.objects.get(id=etablissement_id)
        roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
        context = {
            "setting": setting,
            "user": user,
            "roles": roles
        }
        return render(request, "teacher/detail_teacher.html", context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_teacher(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    user = User.objects.get(id=user_id)
    nombre = {}
    nombre["nombre_contrats"] = Contrat.objects.filter(user_id=user.id).count()
    nombre["nombre_enseignements"] = Enseigner.objects.filter(enseignant_id=user.id).count()
    nombre["nombre_renumerations"] = Renumeration.objects.filter(user_id=user.id).count()
    nombre["nombre_absences_enseignants"] = Absence.objects.filter(enseignant_id=user.id).count()
    nombre["nombre_emargements"] = Emargement.objects.filter(enseignant_id=user.id).count()
    
    nombre["nombre_contrats_admin"] = Contrat.objects.filter(admin_id=user.id).count()
    nombre["nombre_renumerations_admin"] = Renumeration.objects.filter(user_id=user.id).count()
    nombre["nombre_paiements"] = Payment.objects.filter(user_id=user.id).count()
    nombre["nombre_autorisation_payements_students"] = AutorisationPayment.objects.filter(user_id=user.id).count()
    nombre["nombre_autorisation_payements_salles"] = AutorisationPaymentSalle.objects.filter(user_id=user.id).count()
    nombre["nombre_absences_admin"] = AbsenceAdmin.objects.filter(user_id=user.id).count()
    nombre["nombre_compositions"] = Composer.objects.filter(user_id=user.id).count()
    nombre["nombre_emargements_admin"] = Emargement.objects.filter(user_id=user.id).count()
    nombre["nombre_depenses"] = Depense.objects.filter(user_id=user.id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
    
    groups = user.groups.all()    
    context = {
        "setting": setting,
        "enseignant": user,
        "nombre_total": nombre_total,
        "nombre": nombre,
        "groups": groups
    }
    return render(request, "teacher/delete_teacher.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_teacher(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        user_id = int(dechiffrer_param(str(id)))
        user = User.objects.get(id=user_id)
    except:
        user = None
    
    if user:
        # Nombre d'utilisateurs avant la suppression
        count0 = User.objects.all().count()
        user.delete()
        # Nombre d'utilisateurs après la suppression
        count1 = User.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
            return redirect("user/admin")
        else:
            messages.error(request, "La suppression a échouée.")
            return redirect("user/admin")
    return redirect("user/admin")
    

@login_required(login_url='connection/login')
def edit_photo(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        user = user=request.user
        profile = Profile.objects.get(user = user)
    except Exception as e:
        profile = None

    if request.method == "POST":
        photo = None
        if request.POST.get('photo', True):
            photo = request.FILES["photo"]
            
        if photo is not None :
            profile.photo = photo
            profile.save()
                    
        return redirect("user/profile")
    
    context={
        "user" : user,
        "profile":profile,
        "setting": setting
    }
    return render(request,"user/profile.html",context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_user)
@transaction.atomic
def profile(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    try:
        profile = Profile.objects.get(user=user)
    except Exception as e:
        profile = None
     
    if request.method == "POST":
        #On verifie si le profile n'existe pour le créer sinon on le modifie.
        if profile is None:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            country = request.POST["country"]

            request.user.last_name = last_name
            request.user.first_name = first_name
            request.user.email = email

            
            request.user.save()
            
            profil = Profile(
                datenais = datenais,
                phone = phone, 
                address = address, 
                user = request.user, 
                gender = gender,
                profession = profession, 
                diplome = diplome, 
                country = country
            )
            profil.save()
            return redirect("user/profile")
        else:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            country = bleach.clean(request.POST["country"].strip())

            user = profile.user
            user.last_name = last_name
            user.first_name = first_name
            user.email = email

            user.save()
            profile.datenais = datenais
            profile.gender = gender
            profile.phone = phone
            profile.address = address
            profile.profession = profession
            profile.diplome = diplome
            profile.country = country
            
            profile.save()
            return redirect("user/profile")
            
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]

    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
    context={
        "countries": countries,
        "user": user,
        "profile": profile,
        "roles": roles,
        "setting": setting
    }
    return render(request, "user/profile.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
@transaction.atomic
def profile_supuser(request):
    setting = get_setting_sup_user()
    
    user_id = request.user.id
    user = User.objects.get(id = user_id)
    try:
        profile = Profile.objects.get(user=user)
    except Exception as e:
        profile = None
     
    if request.method == "POST":
        #On verifie si le profile n'existe pour le créer sinon on le modifie.
        if profile == None:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            country = request.POST["country"]

            request.user.last_name = last_name
            request.user.first_name = first_name
            request.user.email = email

            
            request.user.save()
            
            profil = Profile(
                datenais = datenais,
                phone = phone, 
                address = address, 
                user = request.user, 
                gender = gender,
                profession = profession, 
                diplome = diplome, 
                country = country
            )
            profil.save()
            return redirect("user/profile_supuser")
        else:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            country = bleach.clean(request.POST["country"].strip())

            user = profile.user
            user.last_name = last_name
            user.first_name = first_name
            user.email = email

            user.save()
            profile.datenais = datenais
            profile.gender = gender
            profile.phone = phone
            profile.address = address
            profile.profession = profession
            profile.diplome = diplome
            profile.country = country
            
            profile.save()
            return redirect("user/profile_supuser")
            
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]

    groups = Group.objects.filter(name__in=["Super user", "Super admin"])
    context={
        "countries": countries,
        "user": user,
        "profile": profile,
        "groups": groups,
        "setting": setting
    }
    return render(request, "user/profile_supuser.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
@transaction.atomic
def profile_sup_admin(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    try:
        profile = Profile.objects.get(user=user)
    except Exception as e:
        profile = None
     
    if request.method == "POST":
        #On verifie si le profile n'existe pour le créer sinon on le modifie.
        if profile == None:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            country = request.POST["country"]

            request.user.last_name = last_name
            request.user.first_name = first_name
            request.user.email = email

            
            request.user.save()
            
            profil = Profile(
                datenais = datenais,
                phone = phone, 
                address = address, 
                user = request.user, 
                gender = gender,
                profession = profession, 
                diplome = diplome, 
                country = country
            )
            profil.save()
            return redirect("user/profile_sup_admin")
        else:
            last_name = bleach.clean(request.POST["last_name"].strip())
            first_name = bleach.clean(request.POST["first_name"].strip())
            datenais = request.POST["datenais"]
            gender = request.POST["gender"]
            email = request.POST["email"]
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            diplome = bleach.clean(request.POST["diplome"].strip())
            country = bleach.clean(request.POST["country"].strip())

            user = profile.user
            user.last_name = last_name
            user.first_name = first_name
            user.email = email

            user.save()
            profile.datenais = datenais
            profile.gender = gender
            profile.phone = phone
            profile.address = address
            profile.profession = profession
            profile.diplome = diplome
            profile.country = country
            
            profile.save()
            return redirect("user/profile_sup_admin")
            
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]

    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
    context = {
        "countries": countries,
        "user": user,
        "profile": profile,
        "roles": roles,
        "setting": setting
    }
    return render(request, "user/profile_sup_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_user)
def edit_profile_photo(request):
    if request.method == "POST":
        try:
            profile = Profile.objects.get(user=request.user)
        except Exception as e:
            profile = None
        
        if profile:
            photo = None
            if request.POST.get('photo', True):
                photo = request.FILES["photo"]
            if photo is not None :
                # Vérifier si l'utilisateur a une photo associée et que le fichier existe réellement
                if profile.photo and hasattr(profile.photo, 'path'):
                    photo_path = profile.photo.path  # Récupérer le chemin de la photo

                    if os.path.exists(photo_path):  # Vérifier si le fichier existe
                        os.remove(photo_path)  # Supprimer le fichier  
                    profile.photo = photo
                    profile.save() 
                else:
                    profile.photo = photo
                    profile.save()           
            return redirect("user/profile")
        else:
            messages.error(request, "Commencez par mettre à jour votre profil, et après vous pourrez ajouter une photo.")
            return redirect("user/profile")
        
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_sup_user_promoteur)            
def permission(request, user_id):
    group_name = request.session.get('group_name')
    id = int(dechiffrer_param(str(user_id)))
    if group_name in ["Super user", "Super admin"]:
        anneeacademique_id = request.session.get('annee_id')
        setting = get_setting_sup_user()
        user = User.objects.get(id=id)
        request.session["is_active"] = user.is_active
        request.session["is_staff"] = user.is_staff
        request.session["is_superuser"] = user.is_superuser
        
        template = 'global/base_supuser.html'
        context = {
            "setting": setting,
            "user": user,
            "template": template
        }
        return render(request, "user/permission.html", context)
    else:
        anneeacademique_id = request.session.get('anneeacademique_id')
        setting = get_setting(anneeacademique_id)
        if setting is None:
            redirect("settings/maintenance")
        
        user = User.objects.get(id=id)
        request.session["is_active"] = user.is_active
        request.session["is_staff"] = user.is_staff
        
        template = 'global/base_sup_admin.html'
        context = {
            "setting": setting,
            "user": user,
            "template": template
        }
        return render(request, "user/permission.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_sup_user_promoteur)    
def update_permission(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            user = User.objects.get(id=id)
        except:
            user = None

        if user == None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else:            
            actif = request.POST.get('actif')
            staff = request.POST.get('staff')
            group_name = request.session.get('group_name')
            if group_name in ["Super user", "Super admin"]:
                superuser = request.POST.get('superuser')
                if actif == "on":
                    user.is_active = True
                else:
                    user.is_active = False
                    
                if staff == "on":
                    user.is_staff = True
                else:
                    user.is_staff = False
                    
                if superuser == "on":
                    user.is_superuser = True
                else:
                    user.is_superuser = False
                    
                user.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Permission mise à jour avec succès."}) 
            else:  
                if actif == "on":
                    user.is_active = True
                else:
                    user.is_active = False
                    
                if staff == "on":
                    user.is_staff = True
                else:
                    user.is_staff = False
                    
                user.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Permission mise à jour avec succès."})
            
def ajax_active_permission(request, actif):
    if actif == "on":
        request.session["is_active"] = True
    else:
        request.session["is_active"] = False
    context = {}
    return render(request, "ajax_active_permission.html", context)

def ajax_staff_permission(request, staff):
    if staff == "on":
        request.session["is_staff"] = True
    else:
        request.session["is_staff"] = False
    context = {}
    return render(request, "ajax_staff_permission.html", context)

def ajax_superuser_permission(request, superuser):
    if superuser == "on":
        request.session["is_superuser"] = True
    else:
        request.session["is_superuser"] = False
    context = {}
    return render(request, "ajax_superuser_permission.html", context)
            
class CustomPasswordChangeView(auth_views.PasswordChangeView):
    template_name = "password/password_change.html"
    success_url = reverse_lazy("password_change_done")
    form_class = PasswordChangingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(self.request.session.get('group_name'))
        if self.request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
            anneeacademique_id = self.request.session.get('anneeacademique_id')
            setting = get_setting(anneeacademique_id)
            context["setting"] = setting 
            context["template"] = 'global/base_sup_admin.html'
        elif self.request.session.get('group_name') in ["Super user", "Super admin"]:
            setting = get_setting_sup_user()
            context["setting"] = setting 
            context["template"] = 'global/base_supuser.html'     
        else:
            anneeacademique_id = self.request.session.get('anneeacademique_id')
            setting = get_setting(anneeacademique_id)
            context["setting"] = setting 
            context["template"] = 'global/base.html'      
        return context

class CustomPasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = "password/password_change_success.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(self.request.session.get('group_name'))
        if self.request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
            anneeacademique_id = self.request.session.get('anneeacademique_id')
            setting = get_setting(anneeacademique_id)
            context["setting"] = setting 
            context["template"] = 'global/base_sup_admin.html'
        elif self.request.session.get('group_name') in ["Super user", "Super admin"]:
            setting = get_setting_sup_user()
            context["setting"] = setting 
            context["template"] = 'global/base_supuser.html'     
        else:
            anneeacademique_id = self.request.session.get('anneeacademique_id')
            setting = get_setting(anneeacademique_id)
            context["setting"] = setting 
            context["template"] = 'global/base.html'      
        return context

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = "password/password_reset.html"
    success_url = reverse_lazy('password_reset_done')
    form_class = PasswordResForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setting = get_setting_sup_user()
        context["setting"] = setting
        return context
    
class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "password/password_reset_sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setting = get_setting_sup_user()
        context["setting"] = setting    
        return context
    
class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "password/password_reset_form.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setting = get_setting_sup_user()
        context["setting"] = setting       
        return context
    
class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "password/password_reset_done.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setting = get_setting_sup_user()
        context["setting"] = setting       
        return context
    
    
# ===================================== Gestion de parents ===========================================

# Gestion des parents
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def parents(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("setting/maintenance")
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    parents = Parent.objects.filter(etablissement_id=etablissement_id)
    context = {
        "setting": setting,
        "parents": parents,
        "anneeacademique": anneeacademique
    }
    return render(request, "parent/parents.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def detail_parent(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("setting/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    parent = Parent.objects.get(id=user_id)
    students = Student.objects.filter(parent_id=user_id, etablissement_id=etablissement_id)
    nbr_enfants = students.count()
    context={
        "setting": setting,
        "parent": parent,
        "students": students,
        "nbr_enfants": nbr_enfants
    }
    return render(request, "parent/detail_parent.html", context)

@unauthenticated_customer
def profile_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    parent_id = request.session.get('parent_id')
    parent = Parent.objects.get(id=parent_id)
    
    if request.method == "POST":
        address = bleach.clean(request.POST["address"].strip())
        phone = bleach.clean(request.POST["phone"].strip())
        profession = bleach.clean(request.POST["profession"].strip())
        
        parent.address = address   
        parent.phone = phone
        parent.profession = profession 
        parent.save()
        return redirect("parent/profile_parent")
    
    students = Student.objects.filter(parent_id=parent_id)
    tabstudents = []
    for student in students:
        if Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id).exists():
            tabstudents.append(student)
    
    context = {
        "setting": setting,
        "parent": parent,
        "students": tabstudents
    }
    return render(request, "parent/profile_parent.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("setting/maintenance")
    
    if request.method == "POST":
        firstname = bleach.clean(request.POST["firstname"].strip())
        lastname = bleach.clean(request.POST["lastname"].strip())
        address = bleach.clean(request.POST["address"].strip())
        phone = bleach.clean(request.POST["phone"].strip())
        profession = bleach.clean(request.POST["profession"].strip())
        gender = request.POST["gender"]
        country = request.POST["country"]
        #Determination du mot de passe
        lastnames = lastname.split()
        firstnames = firstname.split()
        prenomf = ""
        for p in firstnames:
            prenomf = prenomf+""+p[0]

        nomf = "".join(lastnames)
        password = (prenomf+""+nomf).lower()
        #Existence du parent
        query = Parent.objects.filter(lastname=lastname, firstname=firstname, phone=phone, etablissement_id=etablissement_id)
        if Parent.objects.filter(phone=phone, etablissement_id=etablissement_id):#On verifie si ce parent existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Ce téléphone existe déjà."})
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce parent existe déjà."})
        else:
            parent = Parent(
                etablissement_id=etablissement_id,
                username=phone,
                firstname=firstname, 
                lastname=lastname,
                address=address,
                phone=phone,
                profession=profession,
                gender=gender,
                country=country,
                password=password)
            
            # Nombre de parents avant l'ajout
            count0 = Parent.objects.all().count()
            parent.save()
            # Nombre de parent après l'ajout
            count1 = Parent.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Parent enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "countries": countries,
        "contrat": contrat
    }
    return render(request, "parent/add_parent.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_parent(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("setting/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    parent = Parent.objects.get(id=user_id)
    
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]
    tabcountries = [ country for country in countries if country != parent.country]
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "parent": parent,
        "countries": tabcountries,
        "contrat": contrat
    }
    return render(request, "parent/edit_parent.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_pa(request):
    etablissement_id = request.session.get('etablissement_id')
    if request.method=="POST":
        id = int(request.POST["id"])
        try:
            parent = Parent.objects.get(id=id)
        except:
            parent = None

        if parent is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            firstname = bleach.clean(request.POST["firstname"].strip())
            lastname = bleach.clean(request.POST["lastname"].strip())
            address = bleach.clean(request.POST["address"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            profession = bleach.clean(request.POST["profession"].strip())
            gender = request.POST["gender"]
            country = request.POST["country"]
            #On verifie si ce parent a déjà été enregistrée
            parents = Parent.objects.filter(etablissement_id=etablissement_id).exclude(id=id)
            tabParent = []
            tabPhone = []
            for p in parents:  
                dic = {}
                dic["lastname"] = p.lastname   
                dic["firstname"] = p.firstname
                dic["phone"] = p.phone  
                dic["etablissement_id"] = int(p.etablissement.id) 
                tabParent.append(dic)
                tabPhone.append(p.phone)
                
            new_dic = {}
            new_dic["lastname"] = lastname
            new_dic["firstname"] = firstname
            new_dic["phone"] = phone
            new_dic["etablissement_id"] = int(etablissement_id)
            
            if phone in tabPhone:#On verifie si ce parent existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Ce téléphone existe déjà."})
            if new_dic in tabParent:#On verifie si ce parent existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Ce parent existe déjà."})
            else:
                parent.lastname = lastname
                parent.firstname = firstname
                parent.address = address
                parent.phone = phone
                parent.profession = profession
                parent.gender = gender
                parent.country = country
                parent.etablissement_id = etablissement_id
                parent.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Parent modifié avec succès."})

@login_required(login_url='connection/account')     
@allowed_users(allowed_roles=permission_gestionnaire)       
def del_parent(request, id):
    try:
        user_id = int(dechiffrer_param(str(id)))
        parent = Parent.objects.get(id=user_id)
    except:
        parent = None
        
    if parent:
        parent.delete()
    return redirect("parent/parents")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def delete_parent(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    parent = Parent.objects.get(id=user_id)
    nombre = {}
    nombre["nombre_students"] = Student.objects.filter(parent_id=parent.id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur

    context = {
        "setting": setting,
        "parent": parent,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "parent/delete_parent.html", context)

@unauthenticated_customer
def update_password_parent(request):
    parent_id = request.session.get('parent_id')
    if request.method == "POST":
        password = bleach.clean(request.POST["password"].strip())
        newpassword = bleach.clean(request.POST["newpassword"].strip())
        renewpassword = bleach.clean(request.POST["renewpassword"].strip())
        
        query = Parent.objects.filter(id=parent_id, password=password)
        if query.exists():
            if newpassword == renewpassword:
                parent = Parent.objects.get(id=parent_id)
               
                parent.password = newpassword
                parent.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Mot de passe modifié avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La confirmation du mot de passe ne correspond pas."})
        else:
            return JsonResponse({
                    "status": "error",
                    "message": "Mot de passe incorrect."})

#======================================== Gestion des étudiants =========================================

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def students(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    students = Student.objects.select_related("parent").filter(etablissement_id=etablissement_id).order_by("lastname")
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "students": students,
        "anneeacademique": anneeacademique
    }
    return render(request, "student/students.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def detail_student(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))  
    student = Student.objects.get(id=user_id)
    
    context = {
        "setting": setting,
        "student": student
    }
    return render(request, "student/detail_student.html", context)

@unauthenticated_customer
def profile_student(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = request.session.get('student_id')
    student = Student.objects.get(id=student_id)
    
    if request.method == "POST":
        address = bleach.clean(request.POST["address"].strip())
        
        student.address = address    
        student.save()
        return redirect("student/profile_student")
        
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()   
    context = {
        "setting": setting,
        "student": student,
        "salle": inscription.salle
    }
    return render(request, "student/profile_student.html", context)


@login_required(login_url='connection/account')   
@allowed_users(allowed_roles=permission_gestionnaire) 
def add_student(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        firstname = bleach.clean(request.POST["firstname"].strip())
        lastname = bleach.clean(request.POST["lastname"].strip())
        address = bleach.clean(request.POST["address"].strip())
        datenais = request.POST["datenais"]
        lieunais = bleach.clean(request.POST["lieunais"].strip())
        gender = request.POST["gender"]
        country = request.POST["country"]
        parent = request.POST["parent"]
        #Determination du mot de passe
        lastnames = lastname.split()
        firstnames = firstname.split()
        prenomf = ""
        for p in firstnames:
            prenomf = prenomf+""+p[0]

        nomf = "".join(lastnames)
        password = (prenomf+""+nomf).lower()
        #Existence de l'étudiant
        query = Student.objects.filter(lastname=lastname, firstname=firstname, datenais=datenais, etablissement_id=etablissement_id)
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet étudiant existe déjà."})
        else:
            username = datenais
            student = Student(
                etablissement_id=etablissement_id,
                username=username,
                firstname=firstname, 
                lastname=lastname,
                address=address,
                datenais=datenais,
                lieunais=lieunais,
                gender=gender,
                country=country,
                password=password,
                parent_id=parent)
            
            # Nombre d'étudiants avant l'ajout
            count0 = Student.objects.all().count()
            student.save()
            # Nombre d'étudiants après l'ajout
            count1 = Student.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Elève enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]
    parents = Parent.objects.filter(etablissement_id=etablissement_id)
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "countries": countries,
        "parents": parents,
        "contrat": contrat
    }
    return render(request, "student/add_student.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_student(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    student = Student.objects.get(id=user_id)
    parents = Parent.objects.filter(etablissement_id=etablissement_id).exclude(id=student.parent.id)
    countries = [
                'Afrique du Sud',
                'Afghanistan',
                'Albanie',
                'Allemagne',
                'Andorre',
                'Angola',
                'Antigua-et-Barbuda',
                'Arabie Saoudite',
                'Argentine',
                'Arménie',
                'Australie',
                'Autriche',
                'Azerbaïdjan',
                'Bahamas',
                'Bahreïn',
                'Bangladesh',
                'Barbade',
                'Belgique',
                'Belize',
                'Bénin',
                'Bhoutan',
                'Biélorussie',
                'Birmanie',
                'Bolivie',
                'Bosnie-Herzégovine',
                'Botswana',
                'Brésil',
                'Brunei',
                'Bulgarie',
                'Burkina Faso',
                'Burundi',
                'Cambodge',
                'Cameroun',
                'Canada',
                'Cap-Vert',
                'Chili',
                'Chine',
                'Chypre',
                'Colombie',
                'Comores',
                'Congo-Brazzaville',
                'Corée du Nord',
                'Corée du Sud',
                'Costa Rica	San',
                'Côte d’Ivoire',
                'Croatie',
                'Cuba',
                'Danemark',
                'Djibouti',
                'Dominique',
                'Égypte',
                'Émirats arabes unis',
                'Équateur',
                'Érythrée',
                'Espagne',
                'Eswatini',
                'Estonie',
                'États-Unis',
                'Éthiopie',
                'Fidji',
                'Finlande',
                'France',
                'Gabon',
                'Gambie',
                'Géorgie',
                'Ghana',
                'Grèce',
                'Grenade',
                'Guatemala',
                'Guinée',
                'Guinée équatoriale',
                'Guinée-Bissau',
                'Guyana',
                'Haïti',
                'Honduras',
                'Hongrie',
                'Îles Cook',
                'Îles Marshall',
                'Inde',
                'Indonésie',
                'Irak',
                'Iran',
                'Irlande',
                'Islande',
                'Israël',
                'Italie',
                'Jamaïque',
                'Japon',
                'Jordanie',
                'Kazakhstan',
                'Kenya',
                'Kirghizistan',
                'Kiribati',
                'Koweït',
                'Laos',
                'Lesotho',
                'Lettonie',
                'Liban',
                'Liberia',
                'Libye',
                'Liechtenstein',
                'Lituanie',
                'Luxembourg',
                'Macédoine',
                'Madagascar',
                'Malaisie',
                'Malawi',
                'Maldives',
                'Mali',
                'Malte',
                'Maroc',
                'Maurice',
                'Mauritanie',
                'Mexique',
                'Micronésie',
                'Moldavie',
                'Monaco',
                'Mongolie',
                'Monténégro',
                'Mozambique',
                'Namibie',
                'Nauru',
                'Népal',
                'Nicaragua',
                'Niger',
                'Nigeria',
                'Niue',
                'Norvège',
                'Nouvelle-Zélande',
                'Oman',
                'Ouganda',
                'Ouzbékistan',
                'Pakistan',
                'Palaos',
                'Palestine',
                'Panama',
                'Papouasie-Nouvelle-Guinée',
                'Paraguay',
                'Pays-Bas',
                'Pérou',
                'Philippines',
                'Pologne',
                'Portugal',
                'Qatar',
                'République centrafricaine',
                'République démocratique du Congo',
                'République Dominicaine',
                'République tchèque',
                'Roumanie',
                'Royaume-Uni',
                'Russie',
                'Rwanda',
                'Saint-Kitts-et-Nevis',
                'Saint-Vincent-et-les-Grenadines',
                'Sainte-Lucie',
                'Saint-Marin',
                'Salomon',
                'Salvador',
                'Samoa',
                'São Tomé-et-Principe',
                'Sénégal',
                'Serbie',
                'Seychelles',
                'Sierra Leone',
                'Singapour',
                'Slovaquie',
                'Slovénie',
                'Somalie',
                'Soudan',
                'Soudan du Sud',
                'Sri Lanka',
                'Suède',
                'Suisse',
                'Suriname',
                'Syrie',
                'Tadjikistan',
                'Tanzanie',
                'Tchad',
                'Thaïlande',
                'Timor oriental',
                'Togo',
                'Tonga',
                'Trinité-et-Tobago',
                'Tunisie',
                'Turkménistan',
                'Turquie',
                'Tuvalu',
                'Ukraine',
                'Uruguay',
                'Vanuatu',
                'Vatican',
                'Venezuela',
                'Viêt Nam',
                'Yémen',
                'Zambie',
                'Zimbabwe'
    ]
    tabcountries = [ country for country in countries if country != student.country]
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "student": student,
        "countries": tabcountries,
        "contrat": contrat,
        "parents": parents
    }
    return render(request, "student/edit_student.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_st(request):
    etablissement_id = request.session.get('etablissement_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            student = Student.objects.get(id=id)
        except:
            student = None

        if student is None:
            return JsonResponse({
                    "status": "error",
                    "message": "identifiant inexistant."})
        else: 
            firstname = bleach.clean(request.POST["firstname"].strip())
            lastname = bleach.clean(request.POST["lastname"].strip())
            address = bleach.clean(request.POST["address"].strip())
            datenais = request.POST["datenais"]
            lieunais = bleach.clean(request.POST["lieunais"].strip())
            gender = request.POST["gender"]
            country = request.POST["country"]
            parent = request.POST["parent"]
            #On verifie si cet étudiant a déjà été enregistrée
            st = Student.objects.exclude(id=id)
            tabStudent = []
            for p in st:  
                dic = {}
                dic["lastname"] = p.lastname   
                dic["firstname"] = p.firstname
                dic["datenais"] = p.datenais 
                dic["etablissement_id"] = int(p.etablissement.id)  
                tabStudent.append(dic)
                
            new_dic = {}
            new_dic["lastname"] = lastname
            new_dic["firstname"] = firstname
            new_dic["datenais"] = datenais
            new_dic["etablissement_id"] = int(etablissement_id)
            
            #On verifie si cet étudiant existe déjà
            if new_dic in tabStudent:
                return JsonResponse({
                    "status": "error",
                    "message": "Cet élève existe déjà."})
            else:
                student.lastname = lastname
                student.firstname = firstname
                student.address = address
                student.datenais = datenais
                student.lieunais = lieunais
                student.gender = gender
                student.country = country
                student.parent_id = parent
                student.etablissement_id = etablissement_id

                student.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Etudiant modifié avec succès."})

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)          
def del_student(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        user_id = int(dechiffrer_param(str(id)))
        student = Student.objects.get(id=user_id)
    except:
        student = None
        
    if student:
        student.delete()
    return redirect("student/students")

@unauthenticated_customer
def update_password(request):
    student_id = request.session.get('student_id')
    if request.method == "POST":
        password = bleach.clean(request.POST["password"].strip())
        newpassword = bleach.clean(request.POST["newpassword"].strip())
        renewpassword = bleach.clean(request.POST["renewpassword"].strip())
        
        query = Student.objects.filter(id=student_id, password=password)
        if query.exists():
            if newpassword == renewpassword:
                student = Student.objects.get(id=student_id)
               
                student.password = newpassword
                student.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Mot de passe modifié avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La confirmation du mot de passe ne correspond pas."})
        else:
            return JsonResponse({
                    "status": "error",
                    "message": "Mot de passe incorrect."})
        
        
#========================= Gestion des groupes ================================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def groupes(request):
    
    setting = get_setting_sup_user()
        
    groups = Group.objects.all()
    tabGroup = []
    for group in groups:
            if group.name in permission_sup_user:
                tabGroup.append(group)

    context = {
            "groupes": tabGroup,
            "setting": setting
    }
    return render(request, "group/groups.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def add_group(request):
    setting = get_setting_sup_user()
    if request.method == "POST":
        name = bleach.clean(request.POST["name"].strip())

        query = Group.objects.filter(name=name)
        # Verifier l'existence du groupe
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce groupe existe déjà."})
        else:
            group = Group(name=name)
            group.save()
            return JsonResponse({
                    "status": "success",
                    "message": "Groupe enregistré avec succès."})
                
    groups_names = ["Super user", "Super admin"]  
    context = {
        "setting": setting,
        "groups_names": groups_names
    }
    return render(request, "group/add_group.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def edit_group(request,id):
    setting = get_setting_sup_user()
    
    user_id = int(dechiffrer_param(str(id)))   
    groupe = Group.objects.get(id=user_id)
    groups_names = ["Super user", "Super admin"]
    tabgroups = [name for name in groups_names if groupe.name != name]
         
    context = {
            "groupe":groupe,
            "groups_names": tabgroups,
            "setting": setting
    }
    return render(request, "group/edit_group.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def edit_gr(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            group = Group.objects.get(id=id)
        except:
            group = None

        if group is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            name = bleach.clean(request.POST["name"].strip())
            #On verifie si ce groupe a déjà été enregistrée
            groups = Group.objects.exclude(id=id)
            tabGroup = []
            for c in groups:          
                tabGroup.append(c.name)
            #On verifie si cette année existe déjà
            if name in tabGroup:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce groupe existe déjà."})
            else:
                group.name=name
                group.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Groupe modifié avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def del_group(request, id):
    try:
        user_id = int(dechiffrer_param(str(id)))
        group = Group.objects.get(id=user_id)
    except:
        group = None
        
    if group:
        # Nombre de groupes avant la suppression
        count0 = Group.objects.all().count()
        group.delete()
        # Nombre de groupes après la suppression
        count1 = Group.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("group/groups")

# ======================= Groups users ==========================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def group_users(request):
    setting = get_setting_sup_user()
        
    groups = Group.objects.all()
    roles = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Surveillant Général", "Enseignant"]
    tabGroup = [group for group in groups if group.name in roles]

    context = {
            "groupes": tabGroup,
            "setting": setting
    }
    return render(request, "group/group_users.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def add_group_user(request):
    setting = get_setting_sup_user()
    if request.method == "POST":
        name = bleach.clean(request.POST["name"].strip())

        query = Group.objects.filter(name=name)
        # Verifier l'existence du groupe
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce groupe existe déjà."})
        else:
            group = Group(name=name)
            group.save()
            return JsonResponse({
                    "status": "success",
                    "message": "Groupe enregistré avec succès."})
            
    groups_names = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Enseignant", "Surveillant Général"]              
    context = {
            "setting": setting,
            "groups_names": groups_names
    }
    return render(request, "group/add_group_user.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def edit_group_user(request, id):
    setting = get_setting_sup_user()
    
    group_id = int(dechiffrer_param(str(id)))   
    groupe = Group.objects.get(id=group_id)
    groups_names = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Enseignant" , "Surveillant Général"]
    tabgroups = [name for name in groups_names if groupe.name != name]
        
    context = {
            "groupe":groupe,
            "groups_names": tabgroups,
            "setting": setting
    }
    return render(request, "group/edit_group_user.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def del_group_user(request, id):
    try:
        group_id = int(dechiffrer_param(str(id)))
        group = Group.objects.get(id=group_id)
    except:
        group = None
        
    if group:
        # Nombre de groupes avant la suppression
        count0 = Group.objects.all().count()
        group.delete()
        # Nombre de groupes après la suppression
        count1 = Group.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("group/group_users") 


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def admin_group(request, id):
    setting = get_setting_sup_user()
    
    user_id = int(dechiffrer_param(str(id)))
    user = User.objects.get(id=user_id)
    groups = Group.objects.all()
    
    tabGroup = [g for g in groups if g.name in permission_sup_user]
    
    groups_user = user.groups.all()    
    context = {
        "groups": tabGroup,
        "user": user,
        "list_groups": groups_user,
        "setting": setting
    }
    return render(request, "group/admin_group.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def add_admin_to_group(request):
    if request.method == "POST":
        id = request.POST["id"]
        name = request.POST["name"]
        user = User.objects.get(id=id)
        group = Group.objects.get(name=name)
        # Supprimer les groupes actuels de l'utilisateur
        #user.groups.clear()
        # Vérifie s'il y a un autre utilisateur que `user` dans le groupe
        autres_utilisateurs = group.user_set.exclude(id=user.id)
        if autres_utilisateurs.exists():
            messages.error(request, "Il y a déjà un autre utilisateur dans ce groupe.")
            return redirect("group/admin_group", chiffrer_param(str(id)))
        else:
            # Ajouter le nouveau groupe à l'utilisateur
            user.groups.add(group)
            messages.success(request, "Admin associé au groupe avec succès.")
            return redirect("group/admin_group", chiffrer_param(str(id)))
            
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_sup_user)
def del_user_to_group(request, id, name):
    user_id = int(dechiffrer_param(str(id)))
    group_name = dechiffrer_param(name)
    
    user = User.objects.get(id=user_id)
    group = Group.objects.get(name=group_name)
    user.groups.remove(group)
    
    return redirect("group/admin_group", chiffrer_param(str(id)))
    
    
# ======================= Gestion groups users ==============================

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def roles(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    roles_groups = (EtablissementUser.objects.values("group_id")
              .filter(etablissement_id=etablissement_id)
              .annotate(nombre_users=Count("user"))
    )
    roles = []
    for rg in roles_groups:
        dic = {}
        group = Group.objects.get(id=rg["group_id"])
        
        dic["group"] = group
        dic["roles"] = EtablissementUser.objects.filter(etablissement_id=etablissement_id, group_id=rg["group_id"])
        dic["nombre_users"] = rg["nombre_users"]
        roles.append(dic)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "roles": roles,
        "anneeacademique": anneeacademique,
        "setting": setting
    }
    return render(request, "role/roles.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_role(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        user_id = bleach.clean(request.POST["user"].strip())
        group_id = bleach.clean(request.POST["group"].strip())
        # Verifier l'existence du rôle
        if EtablissementUser.objects.filter(user_id=user_id, group_id=group_id, etablissement_id=etablissement_id):
            return JsonResponse({
                    "status": "error",
                    "message": "Ce rôle existe déjà."})
        else:
            # Récuperer le groupe 
            group = Group.objects.get(id=group_id)
            if group.name == "Promoteur":
                role = EtablissementUser(
                    user_id=user_id, 
                    group_id=group_id, 
                    etablissement_id=etablissement_id
                )
                role.save()
                
                # Mettre à jour le promoteur de l'établissement
                etablissement = Etablissement.objects.get(id=etablissement_id)
                etablissement.promoteur_id = user_id
                etablissement.save()
                
                return JsonResponse({
                        "status": "success",
                        "message": "Rôle enregistré avec succès."})
            else:
                role = EtablissementUser(
                    user_id=user_id, 
                    group_id=group_id, 
                    etablissement_id=etablissement_id
                )
                role.save()
                return JsonResponse({
                        "status": "success",
                        "message": "Rôle enregistré avec succès."})
            
    groups =  Group.objects.exclude(name__in=["Super user", "Super admin"])
    etablissementUsers = EtablissementUser.objects.filter(etablissement_id=etablissement_id).select_related("user")           
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                           
    context = {
            "setting": setting,
            "groups": groups,
            "etablissementUsers": etablissementUsers,
            "contrat": contrat
    }
    return render(request, "role/add_role.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_role(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
     
    role_id = int(dechiffrer_param(str(id)))   
    role = EtablissementUser.objects.get(id=role_id)
    groups = Group.objects.exclude(id=role.group.id).exclude(name__in=["Super user", "Super admin"])
    etablissementUsers = EtablissementUser.objects.filter(etablissement_id=etablissement_id).exclude(user_id=role.user.id)
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                                 
    context = {
        "role": role,
        "etablissementUsers": etablissementUsers,
        "groups": groups,
        "contrat": contrat,
        "setting": setting
    }
    return render(request, "role/edit_role.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
@transaction.atomic
def edit_ro(request):
    etablissement_id = request.session.get('etablissement_id')
    if request.method == "POST":
        id = request.POST["id"]
        try:
            role = EtablissementUser.objects.get(id=id)
        except:
            role = None

        if role:
            user_id = bleach.clean(request.POST["user"].strip())
            group_id = bleach.clean(request.POST["group"].strip())
            roles = EtablissementUser.objects.filter(etablissement_id=etablissement_id).exclude(id=id)
            tabRoles = []
            for r in roles:
                dic = {}
                dic["user_id"] = int(r.user.id)
                dic["group_id"] = int(r.group.id)
                tabRoles.append(dic)
            
            new_dic = {}
            new_dic["user_id"] = int(user_id)
            new_dic["group_id"] = int(group_id)    
            # Verifier l'existence du rôle
            if  new_dic in tabRoles:
                return JsonResponse({
                        "status": "error",
                        "message": "Ce rôle existe déjà."})
            else:
                # Récuperer le groupe
                group = Group.objects.get(id=group_id)
                if group.name == "Promoteur":
                    role.user_id = user_id
                    role.group_id = group_id
                    role.save()
                    
                    # Mettre à jour le promoteur de l'établissement
                    etablissement = Etablissement.objects.get(id=etablissement_id)
                    etablissement.promoteur_id = user_id
                    etablissement.save()
                    
                    return JsonResponse({
                            "status": "success",
                            "message": "Rôle modifié avec succès."})
                else:
                    role.user_id = user_id
                    role.group_id = group_id
                    role.save()
                    
                    return JsonResponse({
                            "status": "success",
                            "message": "Rôle modifié avec succès."})
        return JsonResponse({
                "status": "error",
                "message": "La mise à jour a échouée."})
            
def ajax_delete_role(request, id):
    role = EtablissementUser.objects.get(id=id)
    context = {
        "role": role
    }
    return render(request, "ajax_delete_role.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_role(request, id):
    try:
        role_id = int(dechiffrer_param(str(id)))
        role = EtablissementUser.objects.get(id=role_id)
    except:
        role = None
        
    if role:
        # Nombre de rôles avant la suppression
        count0 = EtablissementUser.objects.all().count()
        role.delete()
        # Nombre de rôles après la suppression
        count1 = EtablissementUser.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("cycles")



@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def group_etablissement_user(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    user = User.objects.get(id=user_id)
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    # Récuperer tous les groupes de l'établissement
    groups = Group.objects.exclude(name__in=["Super user", "Super admin"]) 
    # Récuperer les groupes de l'utilisateur
    roles_user = EtablissementUser.objects.filter(etablissement=etablissement, user=user)
        
    context = {
        "groups": groups,
        "user": user,
        "roles_user": roles_user,
        "setting": setting
    }
    return render(request, "group/group_etablissement_user.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_group_etablissement_to_user(request):
    etablissement_id = request.session.get('etablissement_id')
    if request.method == "POST":
        id = request.POST["id"]
        group_id = bleach.clean(request.POST["group"].strip())
        # Récuperer le groupe
        group = Group.objects.get(id=group_id)
        # Récuperer l'utilisateur
        user = User.objects.get(id=id)
        # Récuperer le group l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        # Vérifier l'existence du rôle
        if EtablissementUser.objects.filter(etablissement=etablissement, group=group, user=user).exists():
            messages.error(request, "Ce rôle existe déjà.")
            return redirect("group/group_etablissement_user", chiffrer_param(str(id)))
        
        status = False # Verifier si l'établissement a déjà un promoteur, un directeur général ou un directeur des études 
        if group.name == "Promoteur":
            roles = EtablissementUser.objects.filter(etablissement=etablissement)
            for role in roles:
                if role.group == group.name:
                    status = True
                    break
        if status:            
            messages.error(request, "L'établissement a déjà un promoteur.")
            return redirect("group/group_etablissement_user", chiffrer_param(str(id)))
        else:
            # Ajouter le nouveau groupe à l'utilisateur
            count0 = EtablissementUser.objects.all().count()
            EtablissementUser.objects.create(etablissement=etablissement, group=group, user=user)
            count1 = EtablissementUser.objects.all().count()
            if count0 < count1:
                messages.success(request, "Utilisateur associé au groupe avec succès.")
            else:
                messages.success(request, "L'association a échouee.")
            return redirect("group/group_etablissement_user", chiffrer_param(str(id)))
        
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_group_etablissement_to_user(request, id):
    etablissement_id = request.session.get('etablissement_id')
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    role_id = int(dechiffrer_param(str(id)))
    role = EtablissementUser.objects.get(id=role_id)
    
    if EtablissementUser.objects.filter(user=role.user, etablissement=etablissement).count() > 1:   
        role.delete()
        messages.success(request, "Rôle suprimé avec succès.")  
    else:
        messages.error(request, "Ce rôle ne peut pas être supprimé.")  
    return redirect("group/group_etablissement_user", chiffrer_param(str(role.user.id)))



