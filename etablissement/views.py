# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count
from django.db import transaction
# Importation des modules locaux
from .models import Etablissement
from anneeacademique.models import AnneeCademique
from app_auth.models import Profile, EtablissementUser
from app_auth.decorator import allowed_users
from school.views import get_setting_sup_user
from scolarite.utils.crypto import dechiffrer_param


permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_supuser = ['Super user', 'Super admin']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def etablissements(request):
    setting = get_setting_sup_user()
    etablissements_groupes = (Etablissement.objects.values("promoteur_id")
                              .annotate(nombre_etablissements=Count("promoteur_id"))
    )
    etablissements = []
    total_etablissement = 0
    for eg in etablissements_groupes:
        dic = {}
        promoteur = User.objects.get(id=eg["promoteur_id"])
        dic["promoteur"] = promoteur
        dic["nombre_etablissements"] = eg["nombre_etablissements"]
        dic["etablissements"] = promoteur.etablissements.all()
        etablissements.append(dic)
        total_etablissement += eg["nombre_etablissements"]
        
    context = {
        "setting": setting,
        "etablissements": etablissements,
        "total_etablissement": total_etablissement
    }
    return render(request, "etablissements.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
@transaction.atomic
def add_etablissement(request):
    user_id = request.user.id
    setting = get_setting_sup_user()
    
    if request.method == "POST":
        promoteur_id = request.POST["promoteur"]
        name = bleach.clean(request.POST["name"].strip())
        abreviation = bleach.clean(request.POST["abreviation"].strip())
        phone = bleach.clean(request.POST["phone"].strip())
        email = bleach.clean(request.POST["email"].strip())
        ville = bleach.clean(request.POST["ville"].strip())
        address = bleach.clean(request.POST["address"].strip())
        # Verifier l'existence du nom et de l'adresse
        if Etablissement.objects.filter(name=name).exists():
            return JsonResponse({
                "status": "error",
                "message": "Cet établissement existe déjà."})
        if Etablissement.objects.filter(abreviation=abreviation).exists():
            return JsonResponse({
                "status": "error",
                "message": "Cette abréviation existe déjà."})
        if Etablissement.objects.filter(address=address).exists():
            return JsonResponse({
                "status": "error",
                "message": "Cette adresse existe déjà."})
        else:            
            etablissement = Etablissement(
                    promoteur_id=promoteur_id,
                    name=name, 
                    abreviation=abreviation,
                    phone=phone,
                    email=email,
                    ville=ville,
                    address=address,
                    user_id= user_id
            )
            # Nombre d'établissements avant l'ajout
            count0 = Etablissement.objects.all().count()
            etablissement.save()
            # Nombre d'établissements après l'ajout
            count1 = Etablissement.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                # Récuperer le group promoteur
                group = Group.objects.get(name="Promoteur")
                # Récuperer l'utilisateur
                user = User.objects.get(id=promoteur_id)
                # Associer l'établissement à l'utilisateur
                EtablissementUser.objects.create(etablissement=etablissement, user=user, group=group)
                
                if Profile.objects.filter(user=user).exists():
                    return JsonResponse({
                        "status": "success",
                        "message": "Etablissement ajouté avec succès."})
                else:
                    # Enregsitrer le profil
                    profil = Profile(user=user)
                    profil.save()
                    return JsonResponse({
                        "status": "success",
                        "message": "Etablissement ajouté avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})
        
    users = User.objects.all()
    promoteurs = []
    for user in users:
        if user.groups.exists():
            groups = user.groups.filter(name__in=["Promoteur", "Super user", "Super admin"])
            if groups.exists() and  user not in promoteurs:
                promoteurs.append(user) 
        else:
            promoteurs.append(user)
            
    for role in EtablissementUser.objects.all():
        if role.group.name == "Promoteur" and role.user not in promoteurs:
            promoteurs.append(role.user)
            
    context = {
        "setting": setting,
        "promoteurs": promoteurs
    }
    return render(request, "add_etablissement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
@transaction.atomic
def edit_etablissement(request,id):
    setting = get_setting_sup_user()
    
    etablissement_id = int(dechiffrer_param(str(id)))
    etablissement = Etablissement.objects.get(id=etablissement_id)
        
    users = User.objects.exclude(id=etablissement.promoteur.id)       
    promoteurs = []
    for user in users:
        if user.groups.exists():
            groups = user.groups.filter(name__in=["Promoteur", "Super user", "Super admin"])
            if groups.exists() and user not in promoteurs :
                promoteurs.append(user) 
        else:
            if user not in promoteurs :
                promoteurs.append(user)
            
    for role in EtablissementUser.objects.all():
        if role.group.name == "Promoteur" and role.user not in promoteurs:
            if role.user.id != etablissement.promoteur.id:
                promoteurs.append(role.user)
             
    context = {
        "setting": setting,
        "etablissement": etablissement,
        "promoteurs": promoteurs
    }
    return render(request, "edit_etablissement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_et(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            etablissement = Etablissement.objects.get(id=id)
        except:
            etablissement = None

        if etablissement is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            promoteur_id = request.POST["promoteur"]
            name = bleach.clean(request.POST["name"].strip())
            abreviation = bleach.clean(request.POST["abreviation"].strip())
            phone = bleach.clean(request.POST["phone"].strip())
            email = bleach.clean(request.POST["email"].strip())
            ville = bleach.clean(request.POST["ville"].strip())
            address = bleach.clean(request.POST["address"].strip())

            etablissements = Etablissement.objects.exclude(id=id)
            tabNames = []
            tabAbreviations = []
            tabAdress = []
            for e in etablissements:          
                tabNames.append(e.name)
                tabAbreviations.append(abreviation)
                tabAdress.append(e.address)

            if name in tabAbreviations: #On verifie si ce nom existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Cette abréviation existe déjà."})
                
            if name in tabNames: #On verifie si cette abréviation existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Ce nom existe déjà."})
                
            if address in tabAdress: #On verifie si cette adresse existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Cette adresse existe déjà."})
            else:
                etablissement.promoteur_id = promoteur_id
                etablissement.name = name
                etablissement.abreviation = abreviation
                etablissement.phone = phone
                etablissement.email = email
                etablissement.ville = ville
                etablissement.address = address
                etablissement.save()
                
               # Récuperer le promoteur
                user = User.objects.get(id=promoteur_id)
                
                roles = EtablissementUser.objects.filter(etablissement=etablissement)
                for role in roles:
                    if role.group.name == "Promoteur":
                        role.user = user
                        role.save()
                        break
                
                return JsonResponse({
                    "status": "success",
                    "message": "Etablissement modifié avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def del_etablissement(request, id):
    try:
        etablissement_id = int(dechiffrer_param(str(id)))
        etablissement = Etablissement.objects.get(id=etablissement_id)
    except:
        etablissement = None
           
    if etablissement:
        # Nombre d'établissement avant la suppression
        count0 = Etablissement.objects.all().count()
        etablissement.delete()
        # Nombre d'établissements après la suppression
        count1 = Etablissement.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("etabs")

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def delete_etablissement(request, id):
    setting = get_setting_sup_user()
    
    etablissement_id = int(dechiffrer_param(str(id)))
    etablissement = Etablissement.objects.get(id=etablissement_id)  
    nombre = {}
    nombre["nombre_anneeacademiques"] = AnneeCademique.objects.filter(etablissement_id=etablissement.id).count()
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
            
    context = {
        "setting": setting,
        "etablissement": etablissement,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_etablissement.html", context)

    