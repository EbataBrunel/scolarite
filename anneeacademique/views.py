# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from datetime import datetime
from django.db import transaction
# Importation des modules locaux 
from .models import*
from school.views import get_setting_sup_user, get_setting
from app_auth.decorator import allowed_users
from school.models import Setting
from classe.models import Classe
from serie.models import Serie
from salle.models import Salle
from programme.models import Programme
from enseignement.models import Enseigner
from matiere.models import Matiere
from paiement.models import AutorisationPayment, AutorisationPaymentSalle, Payment
from calendrier.models import Trimestre
from inscription.models import Inscription
from composition.models import Composer, Deliberation
from absence.models import Absence, AbsenceAdmin
from renumeration.models import Contrat, Renumeration
from emargement.models import Emargement
from publication.models import Publication
from activity.models import Activity
from emploi_temps.models import EmploiTemps
from scolarite.utils.crypto import dechiffrer_param

permission_super_user = ['Super user', 'Super admin']
permission_promoteur_DG = ['Promoteur', 'Directeur Général']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def anneeacademiques(request):
    setting = get_setting_sup_user()
    
    anneeacademiques_groupes = (AnneeCademique.objects.values("etablissement_id")
                                .annotate(nombre_anneeacademiques=Count("id")))
    etablissements = []
    for ag in anneeacademiques_groupes:
        dic = {}
        if ag["etablissement_id"]:
            etablissement = Etablissement.objects.get(id=ag["etablissement_id"])
            dic["etablissement"] = etablissement
            anneeacademiques = etablissement.anneeacademiques.all()
            dic["anneeacademiques"] = anneeacademiques
            dic["nombre_anneeacademiques"] = ag["nombre_anneeacademiques"]
            etablissements.append(dic)
        else:
            dic["etablissement"] = get_setting_sup_user().appname
            dic["anneeacademiques"] = AnneeCademique.objects.filter(etablissement=None)
            dic["nombre_anneeacademiques"] = ag["nombre_anneeacademiques"]
            etablissements.append(dic)
        
        
    context = {
        "setting": setting,
        "etablissements": etablissements
    }
    return render(request, "annee_academiques.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def anneeacademiques_promoteur(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    anneeacademiques = AnneeCademique.objects.filter(etablissement_id=etablissement_id)
    context = {
        "setting": setting,
        "anneeacademiques": anneeacademiques
    }
    return render(request, "anneeacademiques_promoteur.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
@transaction.atomic
def add_anneeacademique(request):
    setting_supuser = get_setting_sup_user()
    
    if request.method == "POST":
        etablissement_id = request.POST["etablissement"]
        annee_debut = bleach.clean(request.POST["annee_debut"].strip())
        annee_fin = bleach.clean(request.POST["annee_fin"].strip())
        separateur = request.POST["separateur"]
        start_date = bleach.clean(request.POST["start_date"].strip())
        end_date = bleach.clean(request.POST["end_date"].strip())
        # Récuperer l'etablissement 
        etablissement = Etablissement.objects.get(id=etablissement_id)
        # Convertir en objet date
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        # Extraire l'année
        start_year = start_date_obj.year
        end_year = end_date_obj.year
        # Difference entre les deux années
        diff_annee = int(annee_debut) - int(annee_fin)
        status = False # La date de début et la date de fin doivent être comprises entre la date de début et la date de fin du groupe
        if etablissement_id:
            
            if AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement=None).exists():
                annee = AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement=None).first()
                if annee.start_date <= start_date_obj.date() and end_date_obj.date() <= annee.end_date: status = False  
                else: status = True                 
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Enregistrer d'abord une année académique du group"})
        if status:
            return JsonResponse({
                    "status": "error",
                    "message": "La date de début et la date de fin doivent être comprises entre la date de début et la date de fin du groupe"})            
        if diff_annee >= 0:
            return JsonResponse({
                        "status": "error",
                        "message": "L'année du début doit être supérieure à l'année de fin."})
        elif  diff_annee != -1:
            return JsonResponse({
                        "status": "error",
                        "message": "L'année de fin doit être supérieure à l'année de début de 1 an."})
        elif int(annee_debut) <= int(start_year) and int(end_year) <= int(annee_fin):
            if etablissement_id:
                # On récupère l'avant dernière année de cet établissement
                derniere_anneeacademique = AnneeCademique.objects.filter(etablissement_id=etablissement_id).first()
                query = AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement_id=etablissement_id)
                if query.exists():
                    return JsonResponse({
                            "status": "error",
                            "message": "Cette année scolaire existe déjà."})
                else:
                    anneeacademique = AnneeCademique(
                        etablissement_id=etablissement_id,
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
                        if derniere_anneeacademique:
                            # Enregister le paramètre de cette année scolaire
                            setting = Setting.objects.filter(anneeacademique_id=derniere_anneeacademique.id).order_by("-id").first()
                            if setting:
                                sett = Setting(
                                    appname = setting.appname,
                                    appeditor = setting.appeditor,
                                    version = setting_supuser.version,
                                    theme = setting.theme,
                                    text_color = setting.text_color,
                                    devise = setting.devise,
                                    address = setting.address,
                                    email = setting.email,
                                    phone = setting.phone,
                                    logo = setting.logo,
                                    width_logo = setting.width_logo,
                                    height_logo = setting.height_logo,
                                    anneeacademique_id =  derniere_anneeacademique.id
                                )
                                # Nombre de paramètre avant l'ajout
                                count2 = Setting.objects.all().count()
                                sett.save()  
                                # Nombre de paramètre après l'ajout
                                count3 = Setting.objects.all().count()
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
                                sett = Setting(
                                    appname = etablissement.name,
                                    appeditor = "EBATA-ATIPO Brunel",
                                    version = setting_supuser.version,
                                    theme = "bg-secondary",
                                    text_color = "text-light",
                                    devise = setting_supuser.devise,
                                    address = etablissement.address,
                                    email = etablissement.email,
                                    phone = etablissement.phone,
                                    logo = "",
                                    width_logo = 70,
                                    height_logo = 70,
                                    anneeacademique_id =  anneeacademique.id
                                )
                                # Nombre de paramètre avant l'ajout
                                count2 = Setting.objects.all().count()
                                sett.save()  
                                # Nombre de paramètre après l'ajout
                                count3 = Setting.objects.all().count()
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
                            sett = Setting(
                                    appname = etablissement.name,
                                    appeditor = "EBATA-ATIPO Brunel",
                                    version = setting_supuser.version,
                                    theme = "bg-secondary",
                                    text_color = "text-light",
                                    devise = setting_supuser.devise,
                                    address = etablissement.address,
                                    email = etablissement.email,
                                    phone = etablissement.phone,
                                    logo = "",
                                    width_logo = 70,
                                    height_logo = 70,
                                    anneeacademique_id =  anneeacademique.id
                            )
                            # Nombre de paramètre avant l'ajout
                            count2 = Setting.objects.all().count()
                            sett.save()  
                            # Nombre de paramètre après l'ajout
                            count3 = Setting.objects.all().count()
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
            else:
                query = AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement=None)
                if query.exists():
                    return JsonResponse({
                            "status": "error",
                            "message": "Cette année scolaire existe déjà."})
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
                        return JsonResponse({
                            "status": "success",
                            "message": "Année scolaire enregistrée avec succès."})
                    else:
                        return JsonResponse({
                            "status": "error",
                            "message": "L'insertion a échouée."})
        else:
            return JsonResponse({
                    "status": "error",
                    "message": "La date de début et la date de fin doivent être comprises entre l’année de début et l’année de fin"})
    
    etablissements = Etablissement.objects.all()      
    context = {
        "setting": setting_supuser,
        "etablissements": etablissements
    }
    return render(request, "add_anneeacademique.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def edit_anneeacademique(request,id):
    setting = get_setting_sup_user()
    if setting is None:
        return redirect("settings/maintenance")
    
    anneeacademique_id = int(dechiffrer_param(str(id)))
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    if anneeacademique.etablissement:
        etablissements = Etablissement.objects.exclude(id=anneeacademique.etablissement.id)
        context = {
            "setting": setting,
            "anneeacademique": anneeacademique,
            "etablissements": etablissements
        }
        return render(request, "edit_anneeacademique.html", context)
    else:
        etablissements = Etablissement.objects.all()
        context = {
            "setting": setting,
            "anneeacademique": anneeacademique,
            "etablissements": etablissements
        }
        return render(request, "edit_anneeacademique.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def edit_anneeac(request):    
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            anneeacademique = AnneeCademique.objects.get(id=id)
        except:
            anneeacademique = None

        if anneeacademique is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else:
            etablissement_id = request.POST["etablissement"]
            annee_debut = bleach.clean(request.POST["annee_debut"].strip())
            annee_fin = bleach.clean(request.POST["annee_fin"].strip())
            separateur = request.POST["separateur"]
            start_date = bleach.clean(request.POST["start_date"].strip())
            end_date = bleach.clean(request.POST["end_date"].strip())
            
            # Convertir en objet date
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            # Extraire l'année
            start_year = start_date_obj.year
            end_year = end_date_obj.year
            # Difference entre les deux années
            diff_annee = int(annee_debut) - int(annee_fin)
            
            #On verifie si cette année a déjà été enregistrée
            anneeacademiques = AnneeCademique.objects.exclude(id=id)
            tabAnneeAcademique = []
            tabAnneeAcademiqueEtablissement = []
            for annee in anneeacademiques:   
                if annee.etablissement:
                    dic = {}  
                    dic["etablissement_id"] = int(annee.etablissement.id)
                    dic["annee_debut"] = annee.annee_debut
                    dic["annee_fin"] = annee.annee_fin
                    tabAnneeAcademiqueEtablissement.append(dic)
                else:
                    dic = {}
                    dic["annee_debut"] = annee.annee_debut
                    dic["annee_fin"] = annee.annee_fin
                    tabAnneeAcademique.append(dic)
                
            #On verifie si cette année existe déjà
            new_dic = {}
            new_dic_etablissement = {}
            if etablissement_id:
                new_dic_etablissement["etablissement_id"] = int(etablissement_id)
                new_dic_etablissement["annee_debut"] = int(annee_debut)
                new_dic_etablissement["annee_fin"] = int(annee_fin)
            else:
                new_dic["annee_debut"] = int(annee_debut)
                new_dic["annee_fin"] = int(annee_fin)
                
            status = False # Indiquer si la date de début et la date de fin doivent être comprises entre la date de début et la date de fin du groupe
            if etablissement_id:
                if AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement=None).exists():
                    s_date = datetime.strptime(start_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
                    e_date = datetime.strptime(end_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
                    annee = AnneeCademique.objects.filter(annee_debut=annee_debut, annee_fin=annee_fin, etablissement=None).first()
                    if annee.start_date <= s_date and e_date <= annee.end_date: status = False  
                    else: status = True                 
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "Enregistrer d'abord une année académique du group"})
            if status:
                return JsonResponse({
                        "status": "error",
                        "message": "La date de début et la date de fin doivent être comprises entre la date de début et la date de fin du groupe"})            
                
            if  diff_annee >= 0:
                return JsonResponse({
                        "status": "error",
                        "message": "L'année du début doit être supérieure à la date de fin."})
            elif  diff_annee != -1:
                return JsonResponse({
                        "status": "error",
                        "message": "L'année de fin doit être supérieure à l'année de début de 1 an."})
            
            elif int(annee_debut) <= int(start_year) and int(end_year) <= int(annee_fin):
                if etablissement_id:            
                    if new_dic_etablissement in tabAnneeAcademiqueEtablissement:
                        return JsonResponse({
                            "status": "error",
                            "message": "Cette année scolaire existe déjà."})
                    
                    else:
                        anneeacademique.etablissement_id = etablissement_id
                        anneeacademique.annee_debut = annee_debut
                        anneeacademique.annee_fin = annee_fin
                        anneeacademique.separateur = separateur
                        anneeacademique.start_date = start_date
                        anneeacademique.end_date = end_date
                        anneeacademique.save()
                        return JsonResponse({
                            "status": "success",
                            "message": "Année scolaire modifiée avec succès."})
                else:
                    if new_dic in tabAnneeAcademique:
                        return JsonResponse({
                            "status": "error",
                            "message": "Cette année scolaire existe déjà."})
                    else:
                        anneeacademique.annee_debut = annee_debut
                        anneeacademique.annee_fin = annee_fin
                        anneeacademique.separateur = separateur
                        anneeacademique.start_date = start_date
                        anneeacademique.end_date = end_date
                        anneeacademique.save()
                        return JsonResponse({
                            "status": "success",
                            "message": "Année scolaire modifiée avec succès."})
            else:
                return JsonResponse({
                        "status": "error",
                        "message": "La date de début et la date de fin doivent être comprises entre l’année de début et l’année de fin"})
                    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def delete_anneeacademique(request,id):
    setting = get_setting_sup_user()
    if setting is None:
        return redirect("settings/maintenance")
    
    anneeacademique_id = int(dechiffrer_param(str(id)))
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    nombre = {}
    nombre["nombre_classes"] = Classe.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_series"] = Serie.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_salles"] = Salle.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_programmes"] = Programme.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_matieres"] = Matiere.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_enseignements"] = Enseigner.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_calendriers"] = Trimestre.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_autorisation_payements_students"] = AutorisationPayment.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_autorisation_payements_salles"] = AutorisationPaymentSalle.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_payments"] = Payment.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_inscriptions"] = Inscription.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_contrats"] = Contrat.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_renumerations_enseignants"] = Renumeration.objects.filter(type_renumeration__in="Administrateur scolaire", anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_renumerations_admin"] = Renumeration.objects.filter(type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_absences_enseignants"] = Absence.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_absences_personnels"] = AbsenceAdmin.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_emargements"] = Emargement.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_publications"] = Publication.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_activites"] = Activity.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_emploitemps"] = EmploiTemps.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_compositions"] = Composer.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_deliberations"] = Deliberation.objects.filter(anneeacademique_id=anneeacademique.id).count()
    nombre["nombre_settings"] = Setting.objects.filter(anneeacademique_id=anneeacademique.id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
            
    context = {
        "setting": setting,
        "anneeacademique": anneeacademique,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_anneeacademique.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def del_anneeacademique(request,id):
    try:
        anneeacademique = AnneeCademique.objects.get(id=id)
    except:
        anneeacademique = None
    
    if anneeacademique :
        # Nombre d'années académiques avant la suppression
        count0 = AnneeCademique.objects.all().count()
        anneeacademique.delete()
        # Nombre d'années académiques après la suppression
        count1 = AnneeCademique.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        
    return redirect("annee_academiques")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def cloture_anneeacademique(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    anneeacademique_id = int(dechiffrer_param(str(id)))
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)

    context = {
        "setting": setting,
        "anneeacademique": anneeacademique
    }
    return render(request, "cloture_anneeacademique.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def clot_anneeacademique(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            anneeacademique = AnneeCademique.objects.get(id=id)
        except:
            anneeacademique = None
        
        if anneeacademique is None:
            return JsonResponse({
                        "status": "error",
                        "message": "Identifiant inexistant."})
        else: 
            password = bleach.clean(request.POST["password"].strip())
            user = User.objects.get(id=request.user.id)
            if user.check_password(password):
                if anneeacademique.status_cloture:
                    anneeacademique.status_cloture = False
                    anneeacademique.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_cloture": anneeacademique.status_cloture,
                                "message": "Cloture de l'année académique désactivée avec succès."})
                else:
                    anneeacademique.status_cloture = True
                    anneeacademique.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_cloture": anneeacademique.status_cloture,
                                "message": "Cloture de l'année académique activée avec succès."})
            else:
                return JsonResponse({
                            "status": "error",
                            "message": "Mot de passe incorrect."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def del_anneeacademique(request,id):
    try:
        anneeacademique_id = int(dechiffrer_param(str(id)))
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    except:
        anneeacademique = None
    
    if anneeacademique :
        # Nombre d'années académiques avant la suppression
        count0 = AnneeCademique.objects.all().count()
        anneeacademique.delete()
        # Nombre d'années académiques après la suppression
        count1 = AnneeCademique.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        
    return redirect("annee_academiques")

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def droit_acces_anneeacademique(request, id):
    setting = get_setting_sup_user()
    
    anneeacademique_id = int(dechiffrer_param(str(id)))
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)

    context = {
        "setting": setting,
        "anneeacademique": anneeacademique
    }
    return render(request, "droit_acces_anneeacademique.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def acces_anneeacademique(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            anneeacademique = AnneeCademique.objects.get(id=id)
        except:
            anneeacademique = None
        
        if anneeacademique is None:
            return JsonResponse({
                        "status": "error",
                        "message": "Identifiant inexistant."})
        else: 
            password = bleach.clean(request.POST["password"].strip())
            user = User.objects.get(id=request.user.id)
            if user.check_password(password):
                if anneeacademique.status_access:
                    anneeacademique.status_access = False
                    anneeacademique.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_access": anneeacademique.status_access,
                                "message": "Droit d'accès de l'année académique désactivé avec succès."})
                else:
                    anneeacademique.status_access = True
                    anneeacademique.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_access": anneeacademique.status_access,
                                "message": "Droit d'accès de l'année académique activé avec succès."})
            else:
                return JsonResponse({
                            "status": "error",
                            "message": "Mot de passe incorrect."})