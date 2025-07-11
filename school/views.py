# Importation des modules standards
import bleach
import re
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required 
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views import View
from django.db.models import Count, Sum
from datetime import date, timedelta
from twilio.rest import Client
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime
# Importation des modules locaux
from .models import Setting, SettingSupUser
from app_auth.decorator import unauthenticated_customer, allowed_users
from app_auth.models import Student, EtablissementUser
from classe.models import Classe
from anneeacademique.models import AnneeCademique
from inscription.models import Inscription
from activity.models import Activity
from programme.models import Programme
from enseignement.models import Enseigner
from calendrier.models import Trimestre, EvenementScolaire
from absence.models import AbsenceAdmin, Absence
from salle.models import Salle
from emargement.models import Emargement
from paiement.models import Payment, Notification, PaymentEtablissement, ContratEtablissement
from absence.models import Absencestudent
from composition.models import Composer
from renumeration.models import Renumeration, Contrat
from contact.models import Contact, Message
from depense.models import Depense
from cycle.models import Cycle
from etablissement.models import Etablissement
from inscription.models import Inscription
from cours.models import Cours, ReadCours
from scolarite.utils.crypto import dechiffrer_param, chiffrer_param

permission_utilisateur = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire', 'Enseignant', 'Surveillant Général', 'Super user', 'Super admin']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire', 'Surveillant Général']
permission_promoteur_DG_Supuser = ['Promoteur', 'Directeur Général', 'Super user']
permission_promoteur_DG_enseignant_supuser = ['Promoteur', 'Directeur Général', 'Enseignant', 'Super user']
permission_super_user = ['Super user', 'Super admin']

#=================================== Définition des mois ===================================== 
def format_mois(month):
    if month == "01":
        return "Janvier"
    elif month == "02":
        return "Février"
    elif month == "03":
        return "Mars"
    elif month == "04":
        return "Avril"
    elif month == "05":
        return "Mai"
    elif month == "06":
        return "Juin"
    elif month == "07":
        return "Juillet"
    elif month == "08":
        return "Août"
    elif month == "Septembre":
        return "09"
    elif month == "10":
        return "Octobre"
    elif month == "11":
        return "Novembre"
    else:
        return "Décembre"
    
# Récuperer le mois dans une date
def get_month_year(annee):
    month = annee.strftime("%m")
    if month == '01':
        return "Janvier"
    elif month == '02':
        return "Février"
    elif month == '03':
        return "Mars"
    elif month == '04':
        return "Avril"
    elif month == '05':
        return "Mai"
    elif month == '06':
        return "Juin"
    elif month == '07':
        return "Juillet"
    elif month == '08':
        return "Août"
    elif month == '09':
        return "Septembre"
    elif month == '10':
        return "Octobre"
    elif month == '11':
        return "Novembre"
    else:
        return "Décembre"
    
# Calculter le salaire
def calcul_montant(cout_heure, heure_totale):
    """ Si 60min -> cout_heure
           15min -> x
           x = (15min * cout_heure) / 60min
    """
    heure_min = heure_totale.split(":")
    heure = heure_min[0]
    minute = heure_min[1]
    cout_min = (float(minute) * float(cout_heure))/60
    
    amount = float(cout_min) + float(heure)*float(cout_heure)
    return round(amount, 2)

# Formatter le temps  
def format_temps(time):
    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
    total_matiere_seconds = time.total_seconds()
    total_matiere_hours = int(total_matiere_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
    total_matiere_minutes = int((total_matiere_seconds % 3600) // 60)

    # Afficher le résultat au format HH:MM
    formatted_time = f"{total_matiere_hours:02}:{total_matiere_minutes:02}"   
    return formatted_time

def get_setting(anneeacademique_id):
    try:
        setting = Setting.objects.filter(anneeacademique_id=anneeacademique_id).first()
    except Exception as e:
        setting = None

    return setting

def get_setting_sup_user():
    try:
        setting = SettingSupUser.objects.all().first()
    except Exception as e:
        setting = None

    return setting

def months_actives(anneeacademique_id):
    months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    tabMonths = []
    
    tabMonthPay = []    
    months_payments = (Payment.objects.values("month")
                        .filter(anneeacademique_id=anneeacademique_id)
                        .annotate(nb_payments=Count("month")))
    for mp in months_payments:
        tabMonthPay.append(mp["month"])
        
    tabMonthRenum = []    
    months_renumerations = (Renumeration.objects.values("month")
                        .filter(anneeacademique_id=anneeacademique_id)
                        .annotate(nb_renumerations=Count("month")))
    for mr in months_renumerations:
        tabMonthRenum.append(mr["month"])
        
    tabMonthDepense = []    
    months_depenses = (Depense.objects.values("month")
                        .filter(anneeacademique_id=anneeacademique_id)
                        .annotate(nb_depenses=Count("month")))
    for mr in months_depenses:
        tabMonthDepense.append(mr["month"])
        
    for month in months:
        if (month in tabMonthRenum) or (month in tabMonthPay) or (month in tabMonthDepense):
            if month not in tabMonths:
                tabMonths.append(month) 
    
    return tabMonths

# Somme totale qu'on a payé les enseignants
def somme_total_renum_salle(salle_id, anneeacademique_id, month): 
    
        matieres_emargements = (Emargement.objects.values("matiere_id")
                                .filter(anneeacademique_id=anneeacademique_id, month=month, salle_id=salle_id)
                                .annotate(nb_matieres=Count("matiere_id")))
        
        total_renum = 0
        for me in matieres_emargements:
            
            emargements = Emargement.objects.filter(anneeacademique_id=anneeacademique_id, month=month, salle_id=salle_id, matiere_id=me["matiere_id"])
            # Initialisation avec une durée nulle
            total_delta = timedelta(0)
            for em in emargements:
                    # Convertir les objets time en timedelta
                    start_delta = timedelta(hours=em.heure_debut.hour, minutes=em.heure_debut.minute)
                    end_delta = timedelta(hours=em.heure_fin.hour, minutes=em.heure_fin.minute)
                    # Calculer la somme des deux
                    total_delta +=  end_delta - start_delta
                    
            # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
            total_seconds = total_delta.total_seconds()
            total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
            total_minutes = int((total_seconds % 3600) // 60)

            # Afficher le résultat au format HH:MM
            formatted_time = f"{total_hours:02}:{total_minutes:02}"
                
            # Recuperer le cout par heure de la matière
            enseignement = Enseigner.objects.filter(
                    salle_id=salle_id,
                    matiere_id=me["matiere_id"],
                    anneeacademique_id=anneeacademique_id).first()
                
            total_renum += calcul_montant(enseignement.cout_heure, formatted_time)
                
        return total_renum    
        
     
def maintenance(request):   
    return render(request, "settings/maintenance.html")

def authorization_etablissement(request, id):
    etablissement_id = int(dechiffrer_param(id))
    setting = get_setting_sup_user()
    etablissement = Etablissement.objects.get(id=etablissement_id)
    context = { 
               "etablissement": etablissement, 
               "setting": setting 
    }
    return render(request, "settings/authorization_etablissement.html", context)

def authorization_etablissement_student(request, id):
    etablissement_id = int(dechiffrer_param(id))
    setting = get_setting_sup_user()
    etablissement = Etablissement.objects.get(id=etablissement_id)
    context = { 
               "etablissement": etablissement, 
               "setting": setting 
    }
    return render(request, "settings/authorization_etablissement_student.html", context)

def authorization(request):
    context = { }
    return render(request, "settings/authorization.html", context)

def session_annee(request, etablissement_id):
    request.session["group_name_old"] = request.session.get('group_name')
    request.session["etablissement_id"] = etablissement_id
    
    anneeacademique = AnneeCademique.objects.filter(etablissement_id=etablissement_id).order_by("-id")[0]    
    request.session["anneeacademique_id"] = anneeacademique.id
    request.session["annee_debut"] = anneeacademique.annee_debut
    request.session["annee_fin"] = anneeacademique.annee_fin
    request.session["separateur"] = anneeacademique.separateur
    
    id = chiffrer_param(str(etablissement_id))
    return redirect("settings/db_cycle", id)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def db_cycle(request, etablissement_id):    
    anneeacademique_id = request.session.get('anneeacademique_id')
    group_name = request.session.get('group_name')
    setting = get_setting(anneeacademique_id)    
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(etablissement_id)))
    cycles = Cycle.objects.filter(etablissement_id=id, anneeacademique_id=anneeacademique_id)
    tabcycles = []
    for cycle in cycles:
        dic = {}
        dic["cycle"] = cycle
        dic["nombre_classes"] = Classe.objects.filter(cycle_id=cycle.id).count()
        tabcycles.append(dic)
     
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=id)
    # Récuperer l'année académique   
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    anneeacademiques = AnneeCademique.objects.filter(etablissement_id=id).exclude(id=anneeacademique_id)
    
    user = request.user
    if group_name in ["Super user"]:
        roles = EtablissementUser.objects.filter(etablissement=etablissement)
        # Supprimer le nom du group principal pour eviter des doublons
        tabgroups = []
        for role in roles:
            if role.group not in tabgroups:
                tabgroups.append(role.group) 
              
        context = {
            "cycles": tabcycles,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "groups": tabgroups,
            "group_name": group_name,
            "user": user,
            "setting": setting
        }
        return render(request, "settings/db_cycle.html", context)
    else:
        roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)  
        # Supprimer le nom du group principal pour eviter des doublons
        tabgroups = []
        for role in roles:
            if role.group.name != group_name and role.group not in tabgroups:
                if group_name in permission_utilisateur:
                    tabgroups.append(role.group) 
                    
        if request.session.get('group_name_old'):
            gp = Group.objects.filter(name=request.session.get('group_name_old')).first()
            tabgroups.append(gp)
                       
        context = {
            "cycles": tabcycles,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "groups": tabgroups,
            "group_name": group_name,
            "user": user,
            "setting": setting
        }
        return render(request, "settings/db_cycle.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def db_classe(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cycle_id = int(dechiffrer_param(str(id))) 
    cycle = Cycle.objects.get(id=cycle_id)
    request.session["cycle_id"] = cycle.id
    request.session["cycle_lib"] = cycle.libelle
    
    classes = Classe.objects.filter(cycle_id=cycle.id, anneeacademique_id=anneeacademique_id)    
    context = {
        "setting": setting,
        "classes": classes
    }
    
    return render(request, "settings/db_classe.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def dashboard(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    group_name = request.session.get('group_name')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = int(dechiffrer_param(id))
    classe = Classe.objects.get(id=classe_id)
    request.session["classe_id"] = classe.id
    request.session["classe_lib"] = classe.libelle
    # Récuperer la dernière activité
    activity = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type="Privée").order_by('-id').first()
    activity_status = False
    if activity:
        date_actuelle = date.today()
        if date_actuelle == activity.date:
            activity_status = True
    # Récuperer toutes les activités
    activities = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type="Privée").order_by('-id')
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)  
    # Determiner le nombre d'administrateurs
    nb_amin = 0
    roles = EtablissementUser.objects.filter(etablissement=etablissement)
    admin = []        
    for role in roles:
        if role.group.name in permission_admin:
            if role.user not in admin:
                admin.append(role.user)
                nb_amin += 1
    
    # Determiner le nombre d'enseignants
    nb_teachers = 0
    enseignants = []
    for role in roles:
        if role.group.name == "Enseignant":
            if role.user not in enseignants:
                enseignants.append(role.user)
                nb_teachers += 1
            
    # Determiner le nombre d'étudiants inscris cette année
    inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id)
    nb_students = 0
    for i in inscriptions:
        if i.salle.classe.id == classe.id:
            nb_students += 1
            
            
    # Absence des administrateurs
    date_actuelle = date.today()
    absences_admin = AbsenceAdmin.objects.filter(date_absence=date_actuelle)
    
    # Absence des enseignants
    absences_enseignants = Absence.objects.filter(date_absence=date_actuelle)
    
    # Compter les nouveaux contacts 
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
    nombre_messages = Message.objects.filter(anneeacademique_id=anneeacademique_id, beneficiaire_id=user_id, reading_status=0).count()
    
    # Total des étudiants inscris chaque années
    annee_cible = AnneeCademique.objects.get(id=anneeacademique_id)
    annee_debut = annee_cible.annee_debut

    # Filtrer les années <= à celle qu'on cible, trier par ordre décroissant et en prendre 3
    annees_academiques = AnneeCademique.objects.filter(annee_debut__lte=annee_debut, etablissement_id=etablissement_id).order_by('-annee_debut')[:3]
            
    inscriptions = []
    for anneeacademique in annees_academiques:
        #anneeacademique = AnneeCademique.objects.get(id=gi["anneeacademique_id"])
        dic = {}
        dic["anneeacademique"] = anneeacademique
        dic["nombre_students"] = Inscription.objects.filter(anneeacademique_id=anneeacademique.id).count()
        inscriptions.append(dic) 
    
    status_contrat = False
    # Vérifie si l'administrateur ou l'enseignant a signé son contrat 
    if group_name in ["Promoteur", "Directeur des Etudes"] and Contrat.objects.filter(user=request.user, anneeacademique=annee_cible, status_signature=False).exists():
        status_contrat = True  
        
    # Compter les motifs d'absences des enseignants que le DG n'a pas encore pris la decision
    nombre_absences_enseignants = 0
    for absence in Absence.objects.filter(status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
        month = get_month_year(absence.date_absence) # Récuperer le mois de l'absence 
        if not Renumeration.objects.filter(user_id=absence.user.id, month=month, anneeacademique_id=anneeacademique_id).exclude(type_renumeration="Administrateur scolaire").exists():
            nombre_absences_enseignants += 1
            
    # Compter les motifs d'absences des admin que le DG n'a pas encore pris la decision
    nombre_absences_admin = 0
    for absence in AbsenceAdmin.objects.filter(status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
        month = get_month_year(absence.date_absence) # Récuperer le mois de l'absence 
        if not Renumeration.objects.filter(user_id=absence.user.id, month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exists():
            nombre_absences_admin += 1
            
    # Compter les motifs d'absences des admin que le DG n'a pas encore pris la decision
    nombre_absences_student = 0
    for absence in Absencestudent.objects.filter(status_decision=0).exclude(motif=""):
        if absence.emargement.anneeacademique.id == anneeacademique_id:
            nombre_absences_student += 1
             
    classe_id = chiffrer_param(str(request.session.get('classe_id')))   
    context = {
        "setting": setting,
        "activity": activity,
        "activity_status": activity_status,
        "activities": activities,
        "nb_admin": nb_amin,
        "nb_teachers": nb_teachers,
        "nb_students": nb_students,
        "absences_admin": absences_admin,
        "absences_enseignants": absences_enseignants,
        "nombre_contacts": nombre_contacts,
        "nombre_messages": nombre_messages,
        "inscriptions": inscriptions,
        "status_contrat": status_contrat,
        "nombre_absences_enseignants":nombre_absences_enseignants,
        "nombre_absences_admin": nombre_absences_admin,
        "nombre_absences_student": nombre_absences_student,
        "classe_id": classe_id
        
    }
    return render(request, "settings/dashboard.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG_enseignant_supuser)
def db(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    enseignant_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'établissement 
    etablissement = Etablissement.objects.get(id=etablissement_id)
    # Récuperer la dernière activité
    activity = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type="Privée").order_by('-id').first()
    
    activity_status = False
    if activity:
        date_actuelle = date.today()
        if date_actuelle == activity.date:
            activity_status = True
    # Récuperer toutes les activités
    activities = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type="Privée").order_by('-id')
        
    # Calucler le nombre total d'élèves inscris dans les salles de l'enseignant
    salles_enseignements = (Enseigner.objects.values("salle_id")
                            .filter(enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id)
                            .annotate(nombres_matieres=Count("matiere"))
    ) 
    
    nombre_eleves = 0
    for se in salles_enseignements:
        nombre_eleves += Inscription.objects.filter(salle_id=se["salle_id"], anneeacademique_id=anneeacademique_id).count()    
        
    # Determiner le salaire exact de l'enseignant du mois actuel
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month = format_mois(month_actuel)
    
    salles_emargements = (Emargement.objects.values("salle_id")
                   .filter(enseignant_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
                   .annotate(nb_emargements=Count("salle_id")))
    
    tabEmargements = []
    total_salle_delta = timedelta(0)
    montant_payer = 0
    somme_cout_heure = 0
    for se in salles_emargements:
        dic = {}
        salle_id = se["salle_id"]
        salle = Salle.objects.get(id=salle_id)
        dic["salle"] = salle
        
        if salle.cycle.libelle in ["Collège", "Lycée"]:
        
            matieres_emargements = (Emargement.objects.values("matiere_id")
                    .filter(enseignant_id=enseignant_id, salle_id=salle_id, month=month, anneeacademique_id=anneeacademique_id)
                    .annotate(nb_emargements=Count("matiere_id")))
            
            matieres = []
            total_matiere_delta = timedelta(0)
            for me in matieres_emargements:
                dic_matiere = {}
                matiere_id = me["matiere_id"]   
                
                # Recupérer le cout par heure de cette matière
                enseignement = Enseigner.objects.filter(
                    enseignant_id=enseignant_id, 
                    salle_id=salle_id, 
                    matiere_id=matiere_id, 
                    anneeacademique_id=anneeacademique_id).first()
                dic_matiere["cout_heure"] = enseignement.cout_heure
                
                somme_cout_heure += enseignement.cout_heure
                
                emargements = Emargement.objects.filter(enseignant_id=enseignant_id, month=month, salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id)
                # Initialisation avec une durée nulle
                total_delta = timedelta(0)
                list_emargements = []
                for em in emargements:
                    dic_em = {}
                    dic_em["emargement"] = em
                    # Convertir les objets time en timedelta
                    start_delta = timedelta(hours=em.heure_debut.hour, minutes=em.heure_debut.minute)
                    end_delta = timedelta(hours=em.heure_fin.hour, minutes=em.heure_fin.minute)
                    # Calculer la somme des deux
                    total_delta +=  end_delta - start_delta
                        
                    dic_em["hour"] = format_temps(total_delta)
                    
                    list_emargements.append(dic_em)     
                
                dic_matiere["emargements"] = list_emargements        
                
                dic_matiere["total_time"] = format_temps(total_delta)
                
                # Calculer le montant à payer pour cette matière
                dic_matiere["montant_total_matiere"] = calcul_montant(enseignement.cout_heure, format_temps(total_delta))
                
                total_matiere_delta += total_delta
                
                matieres.append(dic_matiere)
            
            dic["total_matiere_time"] = format_temps(total_matiere_delta)
            dic["matieres"] = matieres
            
            montant_total = calcul_montant(somme_cout_heure, format_temps(total_matiere_delta))
            dic["montant_total_salle"] = montant_total
            tabEmargements.append(dic)
            total_salle_delta += total_matiere_delta
            
            montant_payer += montant_total
    
    
    # Récuperer les administrateurs
    administrateurs = []
    nombre_admin = 0
    for role in EtablissementUser.objects.filter(etablissement=etablissement):
        if role.group.name != "Enseignant":
            
            dic = {}
            dic["administrateur"] = role.user
            dic["nombre_groupes"] = EtablissementUser.objects.filter(user=role.user, etablissement=etablissement).count() # Nombre de groupes de l'utilisateur
            if dic not in administrateurs:
                nombre_admin += 1
                administrateurs.append(dic)
    
    # Nombre total d'étudiants inscris cette année
    nombre_total_student_inscris = Inscription.objects.filter(anneeacademique_id=anneeacademique_id).count()
    # Récuperer les enseignants de cetta année
    # Calucler le nombre total d'élèves inscris dans les salles de l'enseignant
    enseignants = []
    nombre_enseignants = 0
    for role in EtablissementUser.objects.filter(etablissement=etablissement):
        if role.group.name == "Enseignant":
            dic = {}
            dic["enseignant"] = role.user
            dic["nombre_groupes"] = EtablissementUser.objects.filter(user=role.user, etablissement=etablissement).count() # Nombre de groupes de l'utilisateur
            if dic not in enseignants:
                nombre_enseignants += 1
                enseignants.append(dic)
        
    # Nombre de nouvelles payes de l'enseignant
    nombre_renumerations = Renumeration.objects.filter(user_id=enseignant_id, anneeacademique_id=anneeacademique_id, status=False).count()
    # Nombre d'absences de l'enseignants
    absences_groupes = (Absence.objects.values("salle_id")
                        .filter(enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id, status=False)
                        .annotate(nombre_absences=Count("salle_id"))
    )
    absence_totale = 0
    absences_enseignants = []
    for ag in absences_groupes:
        dic = {}
        # Récuperer la salle
        salle = Salle.objects.get(id=ag["salle_id"])
        dic["salle"] = salle
        dic["nombre_absences"] = ag["nombre_absences"]
        absence_totale += ag["nombre_absences"]
        
        absences_enseignants.append(dic)
        
    # Emargements de l'enseignants
    emargements_groupes = (Emargement.objects.values("salle_id")
                        .filter(enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id, status=False)
                        .annotate(nombre_emargements=Count("salle_id"))
    )
    emargements_total = 0
    emargements_enseignants = []
    for ag in emargements_groupes:
        dic = {}
        # Récuperer la salle
        salle = Salle.objects.get(id=ag["salle_id"])
        dic["salle"] = salle
        dic["nombre_emargements"] = ag["nombre_emargements"]
        emargements_total += ag["nombre_emargements"]
        emargements_enseignants.append(dic)
        
    nombre_absences = AbsenceAdmin.objects.filter(user_id=request.user.id, anneeacademique_id=anneeacademique_id, status=False).count()
    
    nombre_messages = Message.objects.filter(anneeacademique_id=anneeacademique_id, beneficiaire_id=request.user.id, reading_status=0).count()
    
    
    #============================== Récette =========================
    
    months = months_actives(anneeacademique_id)
    caisses = []
    recette_totale = 0
    for month in months:
        dic_caisse = {}
        dic_caisse["month"] = month
        total_renum_enseignant = 0        
        # Somme totale payée par les étudiants
        total_paiement_student = (Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
            
        months_emargements = (Emargement.objects.values("salle_id")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(nb_emargements=Count("salle_id")))
        
        for me in months_emargements:
            # Somme totale qu'on a payé les enseignants
            sum_renum = somme_total_renum_salle(me["salle_id"], anneeacademique_id, month)
            total_renum_enseignant += sum_renum
            
        # Calculer toutes les indemnités des enseignant d'un mois
        sum_indemnite = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
        
        # Calucler le montant total de renumeration des administarteurs
        total_amount = (Renumeration.objects.filter(month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
        total_indemnite = (Renumeration.objects.filter(month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
        total_renum_admin = float(total_amount) + float(total_indemnite)
        
        
        # Recupérer les dépenses d'un mois
        total_depense = 0
        tabdepenses = []
        type_depenses = (Depense.objects.values("signe")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(sum_depense=Sum("amount")))
        for tp in type_depenses:
            dic = {}
            dic["signe"] = tp["signe"]
            dic["sum_depense"] = tp["sum_depense"]
            dic["depenses"] = Depense.objects.filter(signe=tp["signe"], month=month, anneeacademique_id=anneeacademique_id)
            tabdepenses.append(dic)
            
            if tp["signe"] == "Entrée":
                total_depense += float(tp["sum_depense"])
            else:
                total_depense = total_depense - float(tp["sum_depense"]) 
        
        recette_month = float(total_paiement_student) - float(total_renum_enseignant) - float(sum_indemnite) - total_renum_admin + total_depense
        
        dic_caisse["recette_month"] = recette_month
        
        recette_totale += recette_month
        
        caisses.append(dic_caisse)
    
    # Total des étudiants inscris chaque années
    annee_cible = AnneeCademique.objects.get(id=anneeacademique_id)
    annee_debut = annee_cible.annee_debut

    # Filtrer les années <= à celle qu'on cible, trier par ordre décroissant et en prendre 3
    annees_academiques = AnneeCademique.objects.filter(annee_debut__lte=annee_debut, etablissement_id=etablissement_id).order_by('-annee_debut')[:3]
    
    inscriptions = []
    for anneeacademique in annees_academiques:
        dic = {}
        dic["anneeacademique"] = anneeacademique
        dic["nombre_students"] = Inscription.objects.filter(anneeacademique_id=anneeacademique_id).count()
        inscriptions.append(dic)
    
    group_name = request.session.get('group_name')
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)    
    # Récuperer l'année académique du groupe 
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    status_contrat = False
    # Verifier si le promoteur a signé le contrat de l'établissement
    if group_name == "Promoteur" and ContratEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_group.id, status_signature=False).exists():
        status_contrat = True
        
    # Vérifie si l'administrateur ou l'enseignant a signé son contrat 
    if group_name in ["Enseignant", "Surveillant Général"] and Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique_etablissement, status_signature=False).exists():
        status_contrat = True   
    
    template = ''
    if group_name in permission_promoteur_DG_Supuser:
        template = 'global/base_sup_admin.html'
                  
    if group_name in ["Enseignant", "Surveillant Général"]:
        template = 'global/base.html' 
        
    context = {
        "setting": setting,
        "activities": activities,
        "activity": activity,
        "activity_status": activity_status,
        "montant_payer": montant_payer,
        "nombre_eleves": nombre_eleves,
        "administrateurs": administrateurs,
        "nombre_admin": nombre_admin,
        "nombre_total_student_inscris": nombre_total_student_inscris,
        "enseignants": enseignants,
        "nombre_enseignants": nombre_enseignants,
        "nombre_renumerations": nombre_renumerations,
        "absences_enseignants": absences_enseignants,
        "absence_totale": absence_totale,
        "emargements_enseignants": emargements_enseignants,
        "emargements_total": emargements_total,
        "nombre_absences": nombre_absences,
        "nombre_messages": nombre_messages,
        "caisses": caisses,
        "inscriptions": inscriptions,
        "status_contrat": status_contrat,
        "template": template
    }
    
    return render(request, "settings/db.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def db_supuser(request):
    setting = get_setting_sup_user()
    
    # Récuperer les administrateurs
    users = User.objects.all()
    anneeacademique_id = request.session.get('annee_id')
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    news_users = []
    super_admin = []
    tabUsers = []
    for user in users:
        if user.groups.exists():
            groups = user.groups.all()
            for group in groups:
                if group.name in ["Super user", "Super admin"]:
                    dic = {}
                    dic["user"] = user
                    groupes = user.groups.exclude(name__in=["Promoteur", "Directeur Géneral", "Directeur des Etudes", "Gestionnaire", "Surveillant Général", "Enseignant"])
                    dic["groups"] = groupes
                    dic["nombre_groupes"] = groupes.count()
                    if user not in tabUsers:
                        tabUsers.append(user)
                        super_admin.append(dic)
        else:
            if EtablissementUser.objects.filter(user=user).exists(): continue
            else: news_users.append(user)
                            
    promoteurs = []
    for role in EtablissementUser.objects.all():
        if role.group.name == "Promoteur" and role.user not in promoteurs:
            promoteurs.append(role.user)

    nombre_promoteurs = len(promoteurs)   
    total_etablissements = 0
    etablissements = Etablissement.objects.all()
    tabEtablissements = []
    for etablissement in etablissements:
        query = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=etablissement.id)
        if query.exists():
            anneeacademeique_etablissement = query.first()
            total_etablissements += 1
            dic = {}
            dic["etablissement"] = etablissement
            dic["nombre_students"] = etablissement.inscriptions.filter(anneeacademique_id=anneeacademeique_etablissement.id).count()
            dic["nombre_students_actif"] = etablissement.inscriptions.filter(anneeacademique_id=anneeacademeique_etablissement.id, status_block=True).count()
            dic["nombre_students_block"] = etablissement.inscriptions.filter(anneeacademique_id=anneeacademeique_etablissement.id, status_block=False).count()
            tabEtablissements.append(dic)    
    
    # Somme totale par mois
    payments_groups = (PaymentEtablissement.objects.values("month")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nombre_payments=Count("etablissement_id"))
    )
    payments = []
    for pg in payments_groups:
        dic = {}
        dic["month"] = pg["month"]
        dic["somme_totale"] = (PaymentEtablissement.objects.filter(month=pg["month"], anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0)
        payments.append(dic)
        
    # Somme totale par année académique
    annee_cible = AnneeCademique.objects.get(id=anneeacademique_id)
    annee_debut = annee_cible.annee_debut

    # Filtrer les années <= à celle qu'on cible, trier par ordre décroissant et en prendre 3
    annees_academiques = AnneeCademique.objects.filter(annee_debut__lte=annee_debut, etablissement=None).order_by('-annee_debut')[:3]
    tabAnneeacademique = []
    for anneeacademique in annees_academiques:
        dic = {}
        somme_totale_an = (PaymentEtablissement.objects
                            .filter(anneeacademique_id=anneeacademique.id)
                            .aggregate(Sum("amount"))["amount__sum"] or 0)
        dic["anneeacademique"] = anneeacademique
        dic["somme_totale_an"] = somme_totale_an
        tabAnneeacademique.append(dic)
        
    # Nouveaux paiements effectués par les promoteurs
    nombre_payments = PaymentEtablissement.objects.filter(anneeacademique_id=anneeacademique_id, status=False).count()
        
    context = {
        "setting": setting,
        "promoteurs": promoteurs,
        "super_admin": super_admin,
        "news_users": news_users,
        "nombre_supadmin": len(super_admin),
        "nombre_newusers": len(news_users),
        "nombre_promoteurs": nombre_promoteurs,
        "etablissements": tabEtablissements,
        "total_etablissements": total_etablissements,
        "payments": payments,
        "anneeacademiques": tabAnneeacademique,
        "nombre_payments": nombre_payments
    }
    
    return render(request, "settings/db_supuser.html", context)

@unauthenticated_customer
def home(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    student_id = request.session.get('student_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Nombre de nouveaux paiements
    nombre_nouveaux_payments = Payment.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id, status=False).count()
    # Nombre de nouvelles absences
    absences_students = Absencestudent.objects.filter(student_id=student_id, status=False)
    nombre_absences_students = 0
    for absence in absences_students:
        if absence.emargement.anneeacademique.id == anneeacademique_id:
            nombre_absences_students += 1
    # Nombre de compositions des étudiants
    nombre_nouvelles_compositions = Composer.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id, status=False).count()
    nombre_gestions_etudes =  nombre_absences_students + nombre_nouvelles_compositions
    
    #=========================== Cas du parent ===========================
    parent_id = request.session.get('parent_id')
    # Récuperer les enfants du parent
    students_parents = Student.objects.filter(parent_id=parent_id) 
    # Selectionner les enfants du parent qui sont inscris cette année
    tabinscription_parents = []
    tabstudents = []
    for student in students_parents:
        query = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id)
        if query.exists():
            # Récuperer l'inscription
            inscription = query.first()
            tabinscription_parents.append(inscription)
            tabstudents.append(student)
            
    # Nombre de nouveaux paiements des enfants
    nombres_nouveaux_paiements_parents = 0
    paiements_parents = []
    for student in tabstudents:
        dic = {}
        dic["student"] = student
        nombre_payes = Payment.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id, status_parent=False).count()
        dic["nombre_payes"] = nombre_payes
        nombres_nouveaux_paiements_parents += nombre_payes
        paiements_parents.append(dic)
        
    gestions = []    
    total_gestion_etudes = 0   
    for inscription in tabinscription_parents:
        dic = {}
        dic["inscription"] = inscription
        # Absence des étudiants
        absences = Absencestudent.objects.filter(student_id=inscription.student.id, status_parent=0)
        nombre_absences = 0
        for absence in absences:
            if absence.emargement.anneeacademique.id == anneeacademique_id:
                nombre_absences += 1
        
        dic["nombre_absences"] = nombre_absences
        # Récuperer les composition de l'étudiant        
        nombre_compositions = Composer.objects.filter(anneeacademique_id=anneeacademique_id, student_id=inscription.student.id, status_parent=0).count()
            
        dic["nombre_compositions"] = nombre_compositions
        
        total_gestion_etudes += nombre_compositions + nombre_absences
        
        gestions.append(dic)
        
    # Nombre de nouveau contacts
    nombre_contacts_students = Contact.objects.filter(student_id=student_id, sending_status=True, reading_status=0, anneeacademique_id=anneeacademique_id).count() 
    # Nombre de notification des parents
    nombre_notifications_parents = Notification.objects.filter(parent_id=parent_id, anneeacademique_id=anneeacademique_id, status=False).count() 
    nombre_cours = 0
    if student_id:
        # Récuperer la salle de l'étudiant
        inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()
        # Nombre de nouvelles publications des cours en ligne par l'enseignant  
        cours = Cours.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id)    
        for cour in cours:
            if ReadCours.objects.filter(cours_id=cour.id, student_id=student_id).exists(): continue
            else: nombre_cours += 1
            
    context = {
        "setting": setting,
        "nombre_nouveaux_payments": nombre_nouveaux_payments,
        "nombre_absences_students": nombre_absences_students,
        "nombre_nouvelles_compositions": nombre_nouvelles_compositions,
        "nombre_gestions_etudes": nombre_gestions_etudes,
        "inscriptions_parents": tabinscription_parents,
        "nombres_nouveaux_paiements_parents": nombres_nouveaux_paiements_parents,
        "paiements_parents": paiements_parents,
        "gestions": gestions,
        "total_gestion_etudes": total_gestion_etudes,
        "nombre_contacts_students": nombre_contacts_students,
        "nombre_notifications_parents": nombre_notifications_parents,
        "nombre_cours": nombre_cours
    }
    return render(request, "settings/home.html", context=context)

# =============================== Gestion des études ====================================
@unauthenticated_customer
def resources_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = request.session.get('student_id')
    # Récuperer l'année academique 
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    programmes = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id).select_related('matiere')
    
    trimestres_enseignements = (Enseigner.objects.values("trimestre")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id)
                     .annotate(nb_trimestre=Count("trimestre")))
    
    tabEnseignements = []   
    i = 0 
    for te in trimestres_enseignements:
        i += 1
        dic = {}
        
        dic["i"] = i
        dic["trimestre"] = te["trimestre"]
        enseignements = Enseigner.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id, trimestre=te["trimestre"])
        dic["enseignements"] = enseignements
        tabEnseignements.append(dic)
        
    # Calendriers
    evenements_groupes = (EvenementScolaire.objects.values("trimestre_id")
                              .annotate(nombres_evenements=Count("trimestre_id"))
    )
    
    tabEvenements = []
    for eg in evenements_groupes:
        
        trimestre = Trimestre.objects.get(id=eg["trimestre_id"])
        if trimestre.anneeacademique.id == anneeacademique_id:
            dic = {}
            dic["trimestre"] = trimestre
            dic["nombres_evenements"] = eg["nombres_evenements"]
            dic["evenements"] = trimestre.evenementscolaires.all()
            tabEvenements.append(dic)
    
    # Liste des sujets
    subjects = ['Réclamation de notes', 'Harcèlement', 'Paiement des frais']      
    context = {
        "setting": setting,
        "programmes": programmes,
        "enseignements": tabEnseignements,
        "evenements": tabEvenements,
        "anneeacademique": anneeacademique,
        "subjects": subjects
    }
    return render(request, "settings/resources_admin.html", context=context)


# =============================== Gestion des études ====================================
@unauthenticated_customer
def resources_admin_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'année academique 
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    
    parent_id = request.session.get('parent_id')
    # Récuperer les enfants du parent
    students_parents = Student.objects.filter(parent_id=parent_id) 
    # Selectionner les enfants du parent qui sont inscris cette année
    tabinscription_parents = []
    tabstudents = []
    for student in students_parents:
        query = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id)
        if query.exists():
            # Récuperer l'inscription
            inscription = query.first()
            tabinscription_parents.append(inscription)
            tabstudents.append(student)
    
    resources = []
    for inscription in tabinscription_parents: 
        resource_dic = {}
        resource_dic["inscription"] = inscription
        programmes = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id).select_related('matiere')
        resource_dic["programmes"] = programmes
        trimestres_enseignements = (Enseigner.objects.values("trimestre")
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id)
                        .annotate(nb_trimestre=Count("trimestre")))
        
        tabEnseignements = []   
        i = 0 
        for te in trimestres_enseignements:
            i += 1
            dic = {}
            
            dic["i"] = i
            dic["trimestre"] = te["trimestre"]
            enseignements = Enseigner.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id, trimestre=te["trimestre"])
            dic["enseignements"] = enseignements
            tabEnseignements.append(dic)
        
        resource_dic["enseignements"] = tabEnseignements
        resources.append(resource_dic)
        
    # Calendriers
    evenements_groupes = (EvenementScolaire.objects.values("trimestre_id")
                              .annotate(nombres_evenements=Count("trimestre_id"))
    )
    
    tabEvenements = []
    for eg in evenements_groupes:
        
        trimestre = Trimestre.objects.get(id=eg["trimestre_id"])
        if trimestre.anneeacademique.id == anneeacademique_id:
            dic = {}
            dic["trimestre"] = trimestre
            dic["nombres_evenements"] = eg["nombres_evenements"]
            dic["evenements"] = trimestre.evenementscolaires.all()
            tabEvenements.append(dic)
    
    # Liste des sujets
    subjects = ['Réclamation de notes', 'Harcèlement', 'Paiement des frais']      
    context = {
        "setting": setting,
        "resources": resources,
        "enseignements": tabEnseignements,
        "evenements": tabEvenements,
        "anneeacademique": anneeacademique,
        "subjects": subjects
    }
    return render(request, "settings/resources_admin_parent.html", context=context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def resources_admin_user(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'année academique 
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    
    programmes_groupes = (
        Programme.objects.values('salle_id')
        .filter(anneeacademique_id=anneeacademique_id)
        .annotate(nombre_matieres=Count('matiere'))
    )

    liste_programmes = []
    for programme in programmes_groupes:
        dic = {}
        # Récuperer la salle
        salle = Salle.objects.get(id=programme["salle_id"])
        dic["salle"] = salle
        dic["nombre_matieres"] = programme["nombre_matieres"]
        # Récuperer tous les programmes de cette salle
        dic["programmes"] = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id)
        liste_programmes.append(dic)
        
    enseignements_groupes = (
        Enseigner.objects.values('salle_id')
        .filter(anneeacademique_id=anneeacademique_id)
        .annotate(nombre_trimestre=Count('trimestre'))
    )

    liste_enseignements = []
    for enseignement in enseignements_groupes:
        dic_enseignement = {}
        # Récuperer la salle
        salle = Salle.objects.get(id=enseignement["salle_id"])
        dic_enseignement["salle"] = salle
        
        trimestres_enseignements = (Enseigner.objects.values("trimestre")
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                        .annotate(nb_matieres=Count("matiere")))
        
        tabEnseignements = []   
        i = 0 
        for te in trimestres_enseignements:
            i += 1
            dic = {}
            dic["i"] = i
            dic["trimestre"] = te["trimestre"]
            enseignements = Enseigner.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, trimestre=te["trimestre"])
            dic["enseignements"] = enseignements
            tabEnseignements.append(dic)
            
        dic_enseignement["enseignements"] = tabEnseignements
        liste_enseignements.append(dic_enseignement)
        
    # Calendriers
    evenements_groupes = (EvenementScolaire.objects.values("trimestre_id")
                              .annotate(nombres_evenements=Count("trimestre_id"))
    )
    
    tabEvenements = []
    for eg in evenements_groupes:
        
        trimestre = Trimestre.objects.get(id=eg["trimestre_id"])
        if trimestre.anneeacademique.id == anneeacademique_id:
            dic = {}
            dic["trimestre"] = trimestre
            dic["nombres_evenements"] = eg["nombres_evenements"]
            dic["evenements"] = trimestre.evenementscolaires.all()
            tabEvenements.append(dic)
        
    # Liste des sujets
    subjects = ['Réclamation de notes', 'Harcèlement', 'Harcèlement', 'Paiement des frais']  
    # Récuperer les administrateurs
    administrateurs = []
    users = User.objects.all()
    for user in users:
        if user.groups.exists():
            groups = user.groups.all()
            dic = {}
            dic["administrateur"] = user
            for group in groups:
                if group.name in ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire"]:                       
                    if dic not in administrateurs:
                        dic["group"] = group.name
                        administrateurs.append(dic)
    
    context = {
        "setting": setting,
        "programmes": liste_programmes,
        "enseignements": liste_enseignements,
        "evenements": tabEvenements,
        "anneeacademique": anneeacademique,
        "subjects": subjects,
        "administrateurs": administrateurs
    }
    return render(request, "settings/resources_admin_user.html", context=context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def need_help(request): 
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance") 
    
    context = {
        "setting": setting
    }
    return render(request, "settings/help.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_utilisateur)
def need_help_sup_admin(request): 
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance") 
    
    context = {
        "setting": setting
    }
    return render(request, "settings/help_sup_admin.html", context)

@unauthenticated_customer
def need_help_customer(request): 
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance") 
    
    context = {
        "setting": setting
    }
    return render(request, "settings/help_customer.html", context=context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def index(request):
    if request.session.get('annee_id') and request.session.get('group_name'):
        annee_id = request.session.get('annee_id')
        group_name = request.session.get('group_name')
        
        setting = get_setting_sup_user()    
        
        etablissements = Etablissement.objects.all()
        tabEtablissements = []
        for etablissement in etablissements:
            # Récuperer l'année académique
            anneeacademique = AnneeCademique.objects.get(id=annee_id)
            if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin).exists():
                dic = {}
                dic["etablissement"] = etablissement
                if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, status_access=True).exists():               
                    dic["access"] = True
                else:
                    dic["access"] = False
                tabEtablissements.append(dic)
            
        user = request.user
        groups = user.groups.all()
        # Supprimer le nom du group principal pour eviter des doublons
        tabgroups = []
        for group in groups:
            if group.name != group_name:
                if group.name in ["Super user", "Super admin"]:
                    tabgroups.append(group) 
        
        anneeacademique = AnneeCademique.objects.get(id=annee_id)
        anneeacademiques = AnneeCademique.objects.filter(etablissement_id=None).exclude(id=annee_id)        
        context = {
            "etablissements": tabEtablissements,
            "groups": tabgroups,
            "group_name": group_name,
            "user": user,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "setting": setting
        }
        return render(request, "index.html", context)
    else:
        return redirect("connection/login")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG_Supuser)
def setting(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    if setting is None:
        return redirect("settings/maintenance")
    
    setting = Setting.objects.filter(anneeacademique_id=anneeacademique_id).order_by("-id")[0]    
        
    context = {
        "setting": setting
    }
    return render(request, "settings/setting.html",context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG_Supuser)
def setting_supuser(request):
    setting = get_setting_sup_user()
    
    if request.method == "POST":           
            id = request.POST["id"]
            if id:                
                sett = SettingSupUser.objects.get(id=id)
                appname = bleach.clean(request.POST["appname"].strip())
                appeditor = bleach.clean(request.POST["appeditor"].strip())
                version = bleach.clean(request.POST["version"].strip())
                theme = request.POST["theme"].strip()
                text_color = request.POST["text_color"]
                address = bleach.clean(request.POST["address"].strip())
                devise = bleach.clean(request.POST["devise"].strip())
                email = request.POST["email"]
                
                #On verifie si l'adresse e-mail correspond bien
                regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
                if not re.search(regexp, email):
                    messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
                else:
                    
                    phone = bleach.clean(request.POST["phone"].strip())
                    logo = None
                    if request.POST.get('logo', True):
                        logo = request.FILES["logo"]
                    width = request.POST["width"].strip()
                    height = request.POST["height"].strip()

                    sett.appname = appname
                    sett.appeditor = appeditor
                    sett.version = version
                    sett.theme = theme
                    sett.text_color = text_color
                    sett.devise = devise
                    sett.address = address
                    sett.email = email
                    sett.phone = phone
                    if logo is not None:
                        sett.logo = logo
                    sett.width_logo = width
                    sett.height_logo = height

                    sett.save()
                    messages.success(request, "Paramètre modifié avec succès.")
                    return redirect("settings/setting_supuser")
            else:
                appname = bleach.clean(request.POST["appname"].strip())
                appeditor = bleach.clean(request.POST["appeditor"].strip())
                version = bleach.clean(request.POST["version"].strip())
                theme = request.POST["theme"]
                text_color = request.POST["text_color"]
                address = bleach.clean(request.POST["address"].strip())
                devise = bleach.clean(request.POST["devise"].strip())
                email = request.POST["email"]
                #On verifie si l'adresse e-mail correspond bien
                regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
                if not re.search(regexp, email):
                    messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
                else:
                    phone = bleach.clean(request.POST["phone"].strip())
                    logo = None
                    if request.POST.get('logo', True):
                            logo = request.FILES["logo"]
                    width = bleach.clean(request.POST["width"].strip())
                    height = bleach.clean(request.POST["height"].strip())

                    sett = Setting(
                        appname = appname,
                        appeditor = appeditor,
                        version = version,
                        theme = theme,
                        text_color = text_color,
                        devise = devise,
                        address = address,
                        email = email,
                        phone = phone,
                        logo = logo,
                        width_logo = width,
                        height_logo = height)
                    
                    sett.save()
                    messages.success(request, "Paramètre enregistré avec succès.")
                    return redirect("settings/setting_supuser")

    context = {
        "setting": setting
    }
    return render(request, "settings/setting_supuser.html",context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG_Supuser)
def setting_sup_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    if setting is None:
        return redirect("settings/maintenance")
    else:       
        if request.method == "POST":           
            id = request.POST["id"]
            if id:                
                sett = Setting.objects.get(id=id)
                appname = bleach.clean(request.POST["appname"].strip())
                appeditor = bleach.clean(request.POST["appeditor"].strip())
                version = bleach.clean(request.POST["version"].strip())
                theme = request.POST["theme"].strip()
                text_color = request.POST["text_color"]
                address = bleach.clean(request.POST["address"].strip())
                devise = bleach.clean(request.POST["devise"].strip())
                email = request.POST["email"]
                
                #On verifie si l'adresse e-mail correspond bien
                regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
                if not re.search(regexp, email):
                    messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
                else:
                    
                    phone = bleach.clean(request.POST["phone"].strip())
                    logo = None
                    if request.POST.get('logo', True):
                        logo = request.FILES["logo"]
                    width = request.POST["width"].strip()
                    height = request.POST["height"].strip()

                    sett.appname = appname
                    sett.appeditor = appeditor
                    sett.version = version
                    sett.theme = theme
                    sett.text_color = text_color
                    sett.devise = devise
                    sett.address = address
                    sett.email = email
                    sett.phone = phone
                    if logo is not None:
                        sett.logo = logo
                    sett.width_logo = width
                    sett.height_logo = height
                    sett.anneeacademique_id = anneeacademique_id

                    sett.save()
                    messages.success(request, "Paramètre modifié avec succès.")
                    return redirect("settings/setting_sup_admin")
            else:
                appname = bleach.clean(request.POST["appname"].strip())
                appeditor = bleach.clean(request.POST["appeditor"].strip())
                version = bleach.clean(request.POST["version"].strip())
                theme = request.POST["theme"]
                text_color = request.POST["text_color"]
                address = bleach.clean(request.POST["address"].strip())
                devise = bleach.clean(request.POST["devise"].strip())
                email = request.POST["email"]
                #On verifie si l'adresse e-mail correspond bien
                regexp = r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$"
                if not re.search(regexp, email):
                    messages.error(request, "Le format de l'adresse e-mail ne correspond pas.")
                else:
                    phone = bleach.clean(request.POST["phone"].strip())
                    logo = None
                    if request.POST.get('logo', True):
                            logo = request.FILES["logo"]
                    width = bleach.clean(request.POST["width"].strip())
                    height = bleach.clean(request.POST["height"].strip())

                    sett = Setting(
                        appname = appname,
                        appeditor = appeditor,
                        version = version,
                        theme = theme,
                        text_color = text_color,
                        devise = devise,
                        address = address,
                        email = email,
                        phone = phone,
                        logo = logo,
                        width_logo = width,
                        height_logo = height,
                        anneeacademique_id =  anneeacademique_id)
                    
                    sett.save()
                    messages.success(request, "Paramètre enregistré avec succès.")
                    return redirect("settings/setting_sup_admin")

        context = {
            "setting": setting
        }
        return render(request, "settings/setting_sup_admin.html",context)
    
class ajaxyear(View):
    def get(self, request, id, *args, **kwargs):
        setting = get_setting(id)
        etablissement_id = request.session.get('etablissement_id')
        # Récuperer l'établissement 
        etablissement = Etablissement.objects.get(id=etablissement_id)
        # Récuperer l'année académique 
        anneeacademique = AnneeCademique.objects.get(id=id)
        request.session["anneeacademique_id"] = anneeacademique.id
        request.session["annee_debut"] = anneeacademique.annee_debut
        request.session["annee_fin"] = anneeacademique.annee_fin
        request.session["separateur"] = anneeacademique.separateur

        anneeacademiques = AnneeCademique.objects.filter(etablissement_id=etablissement_id).exclude(id=id)       
        
        user = request.user
        group_name = request.session.get('group_name')
    
        cycles = Cycle.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique.id)
        tabcycles = []
        for cycle in cycles:
            dic = {}
            dic["cycle"] = cycle
            dic["nombre_classes"] = Classe.objects.filter(cycle_id=cycle.id).count()
            tabcycles.append(dic)
        
        if group_name in permission_super_user:
            roles = EtablissementUser.objects.filter(etablissement=etablissement)  
            # Supprimer le nom du group principal pour eviter des doublons
            tabgroups = []
            for role in roles:
                if role.group not in tabgroups and role.group.name != group_name:
                    tabgroups.append(role.group)  
            tabgroups.append(Group.objects.get(name="Super user"))        
            context = {
                "cycles": tabcycles,
                "anneeacademique": anneeacademique,
                "anneeacademiques": anneeacademiques,
                "groups": tabgroups,
                "group_name": group_name,
                "setting": setting
            }
            return render(request, "ajaxyear.html", context)
        else:
            roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)    
            # Supprimer le nom du group principal pour eviter des doublons
            tabgroups = []
            for role in roles:
                if role.group.name != group_name:
                    tabgroups.append(role.group)
                        
            if request.session.get('group_name_old'):
                gp = Group.objects.filter(name=request.session.get('group_name_old')).first()
                tabgroups.append(gp)        

            context = {
                "cycles": tabcycles,
                "anneeacademique": anneeacademique,
                "anneeacademiques": anneeacademiques,
                "groups": tabgroups,
                "group_name": group_name,
                "setting": setting
            }
            return render(request, "ajaxyear.html", context)   
    
    
class ajaxyear_index(View):
    def get(self, request, id, *args, **kwargs):
        setting = get_setting_sup_user()
        anneeacademique = AnneeCademique.objects.get(id=id)
        request.session["annee_id"] = anneeacademique.id
        request.session["annee_d"] = anneeacademique.annee_debut
        request.session["annee_f"] = anneeacademique.annee_fin
        request.session["sep"] = anneeacademique.separateur

        anneeacademiques = AnneeCademique.objects.filter(etablissement=None).exclude(id=id)       
        
        user = request.user
        groups = user.groups.all()
        group_name = request.session.get('group_name')
        
        # Supprimer le nom du group principal pour eviter des doublons
        tabgroups = []
        for group in groups:
            if group.name in ["Super user", "Super admin"]:
                if group.name != group_name:
                    tabgroups.append(group) 
              
        
        etablissements = Etablissement.objects.all()
        tabEtablissements = []
        for etablissement in etablissements:
            if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin).exists():
                dic = {}
                dic["etablissement"] = etablissement
                if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, status_access=True).exists():               
                    dic["access"] = True
                else:
                    dic["access"] = False
                tabEtablissements.append(dic)
            
        context = {
            "setting": setting,
            "groups": tabgroups,
            "group_name": group_name,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "etablissements": tabEtablissements
        }
        return render(request, "ajaxyear_index.html", context)
    
class fetchgroup(View):
    def get(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        groups = user.groups.exclude(name__in=["Promoteur", "Directeur Géneral", "Directeur des Etudes", "Gestionnaire", "Surveillant Général", "Enseignant"])
        context = {
            "groupes": groups,
            "user": user
        }
        return render(request, "fetchgroup.html", context)
    
class fetchgroup_etablissement_user(View):
    def get(self, request, id, *args, **kwargs):
        etablissement_id = request.session.get('etablissement_id')
        etablissement = Etablissement.objects.get(id=etablissement_id)
        user = User.objects.get(id=id)
        roles = EtablissementUser.objects.filter(etablissement=etablissement, user=user)
        context = {
            "roles": roles,
            "user": user
        }
        return render(request, "fetchgroup_etablissement_user.html", context)
        
    
class ajax_group_name(View):
    def get(self, request, group_name, *args, **kwargs):
        etablissement_id = request.session.get('etablissement_id')
        anneeacademique_id = request.session.get('anneeacademique_id') 
        setting = get_setting(anneeacademique_id)
        user = request.user
        request.session["group_name"] = group_name
        
        # Récuperer l'établissement
        etablissement = Etablissement.objects.get(id=etablissement_id)
        tabgroups = []
        if group_name in permission_super_user:
            roles = EtablissementUser.objects.filter(etablissement=etablissement)   
            # Supprimer le nom du group principal pour eviter des doublons
            for role in roles:
                if role.group not in tabgroups and role.group.name != group_name:
                    tabgroups.append(role.group) 
        else:
            roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)       
            # Supprimer le nom du group principal pour eviter des doublons
            for role in roles:
                if role.group.name != group_name:
                    tabgroups.append(role.group) 
                    
            if request.session.get('group_name_old'):
                gp = Group.objects.filter(name=request.session.get('group_name_old')).first()
                tabgroups.append(gp)
                
                
        # Récuperer l'année académique      
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        anneeacademiques = AnneeCademique.objects.filter(etablissement_id=etablissement_id).exclude(id=anneeacademique_id)
        
        cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id)
        tabcycles = []
        for cycle in cycles:
            dic = {}
            dic["cycle"] = cycle
            dic["nombre_classes"] = Classe.objects.filter(cycle_id=cycle.id, anneeacademique_id=anneeacademique_id)
            tabcycles.append(dic)
        context = {
            "setting": setting,
            "groups": tabgroups,
            "group_name": group_name,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "cycles": tabcycles
        }
        return render(request, "ajax_group_name.html", context)
    
class ajax_group_name_index(View):
    def get(self, request, group_name, *args, **kwargs):
        annee_id = request.session.get('annee_id') 
        setting = get_setting_sup_user()
        user = request.user
        groups = user.groups.all()
        request.session["group_name"] = group_name
        
        # Supprimer le nom du group principal pour eviter des doublons
        tabgroups = []
        for group in groups:
            if group.name != group_name:
                if group.name in ["Super user", "Super admin"]:
                    tabgroups.append(group) 
              
        anneeacademique = AnneeCademique.objects.get(id=annee_id)
        anneeacademiques = AnneeCademique.objects.filter(etablissement_id=None).exclude(id=annee_id)
        
        etablissements = Etablissement.objects.filter()
        tabEtablissements = []
        for etablissement in etablissements:
            if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin).exists():
                dic = {}
                dic["etablissement"] = etablissement
                if AnneeCademique.objects.filter(etablissement_id=etablissement.id, annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, status_access=True).exists():               
                    dic["access"] = True
                else:
                    dic["access"] = False
                tabEtablissements.append(dic)
        context = {
            "setting": setting,
            "groups": tabgroups,
            "group_name": group_name,
            "anneeacademique": anneeacademique,
            "anneeacademiques": anneeacademiques,
            "etablissements": tabEtablissements
        }
        return render(request, "ajax_group_name_index.html", context)
    
def ajax_content_salle_etablissement(request, id):
    anneeacademique_id = request.session.get('annee_id')
    etablissement = Etablissement.objects.get(id=id)
    # Récuperer l'année académique du group
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=etablissement.id).first()
    salle_groupes = (
        Inscription.objects.values("salle_id")
        .filter(anneeacademique_id=anneeacademique_etablissement.id)
        .annotate(nombre_students=Count("student"))
    )
    salles = []
    for sg in salle_groupes:
        dic = {}
        salle = Salle.objects.get(id=sg["salle_id"])
        dic["salle"] = salle
        dic["nombre_students"] = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_etablissement.id).count()
        dic["nombre_students_actif"] = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_etablissement.id, status_block=True).count()
        dic["nombre_students_block"] = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_etablissement.id, status_block=False).count()
        salles.append(dic)
        
    context = {
        "etablissement": etablissement,
        "salles": salles
    }
    return render(request, "ajax_content_salle_etablissement.html", context)

def ajax_content_student_etablissement(request, id):
    salle = Salle.objects.get(id=id)
    inscriptions = Inscription.objects.filter(salle_id=salle.id)              
    context = {
        "salle": salle,
        "inscriptions": inscriptions
    }
    return render(request, "ajax_content_student_etablissement.html", context)

def ajax_modal_block_student_etablissement(request, id):
    inscription = Inscription.objects.get(id=id)
    if inscription.status_block:
        return JsonResponse({
            "status": inscription.status_block,
            "student": {
                "lastname": inscription.student.lastname,
                "firstname": inscription.student.firstname
            }
        })
    else:
        return JsonResponse({
            "status": inscription.status_block,
            "student": {
                "lastname": inscription.student.lastname,
                "firstname": inscription.student.firstname 
            }
            ,
            "inscription": {
                "date_block": inscription.date_block,
                "last_name": inscription.responsable.last_name,
                "first_name": inscription.responsable.first_name 
            }
        })

def ajax_block_student_etablissement(request, id):
    user = request.user
    inscription = Inscription.objects.get(id=id)
    if inscription.status_block:
        inscription.status_block = False
        inscription.responsable = user
        inscription.save()
        
        # Nombre d'étudiants actifs et bloqués dans l'établissement de l'etudiant
        nombre_students_actif_etablissement = Inscription.objects.filter(etablissement=inscription.etablissement, anneeacademique=inscription.anneeacademique, status_block=True).count()
        nombre_students_block_etablissement = Inscription.objects.filter(etablissement=inscription.etablissement, anneeacademique=inscription.anneeacademique, status_block=False).count()
        # Nombre d'étudiants actifs et bloqués dans la salle de l'étudiant
        nombre_students_actif_salle = Inscription.objects.filter(salle=inscription.salle, anneeacademique=inscription.anneeacademique, status_block=True).count()
        nombre_students_block_salle = Inscription.objects.filter(salle=inscription.salle, anneeacademique=inscription.anneeacademique, status_block=False).count()
        
        return JsonResponse({
            "status": inscription.status_block,
            "id": {
                "etablissement_id": inscription.etablissement.id,
                "salle_id": inscription.salle.id
            },
            "nombre": {
                "nombre_students_actif_etablissement": nombre_students_actif_etablissement,
                "nombre_students_block_etablissement": nombre_students_block_etablissement,
                "nombre_students_actif_salle": nombre_students_actif_salle,
                "nombre_students_block_salle": nombre_students_block_salle
            }
        })
    else:
        inscription.status_block = True
        inscription.responsable = user
        inscription.save()
        
        # Nombre d'étudiants actifs et bloqués dans l'établissement de l'etudiant
        nombre_students_actif_etablissement = Inscription.objects.filter(etablissement=inscription.etablissement, anneeacademique=inscription.anneeacademique, status_block=True).count()
        nombre_students_block_etablissement = Inscription.objects.filter(etablissement=inscription.etablissement, anneeacademique=inscription.anneeacademique, status_block=False).count()
        # Nombre d'étudiants actifs et bloqués dans la salle de l'étudiant
        nombre_students_actif_salle = Inscription.objects.filter(salle=inscription.salle, anneeacademique=inscription.anneeacademique, status_block=True).count()
        nombre_students_block_salle = Inscription.objects.filter(salle=inscription.salle, anneeacademique=inscription.anneeacademique, status_block=False).count()
        
        return JsonResponse({
            "status": inscription.status_block,
            "id": {
                "etablissement_id": inscription.etablissement.id,
                "salle_id": inscription.salle.id
            },
            "nombre": {
                "nombre_students_actif_etablissement": nombre_students_actif_etablissement,
                "nombre_students_block_etablissement": nombre_students_block_etablissement,
                "nombre_students_actif_salle": nombre_students_actif_salle,
                "nombre_students_block_salle": nombre_students_block_salle
            }
        })
    

def send_sms(to, msg):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=msg,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to
    )
    return message.sid  # tu peux logguer ou afficher l'ID si besoin

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def del_new_user(request, id):
    user_id = int(dechiffrer_param(str(id)))
    try:
        user = User.objects.get(id=user_id)
    except:
        user = None
    if user:
        user.delete()
    
    return redirect("settings/db_supuser")

def ajax_delete_new_user(request, id):
    user = User.objects.get(id=id)
    context = {
        "user": user
    }
    return render(request, "ajax_delete_new_user.html", context)

def ajax_group_new_user(request, id):
    user = User.objects.get(id=id)
    groups = Group.objects.all()
    tabGroup = []
    for group in groups:
        if group.name in ["Super admin", "Promoteur"]:
            tabGroup.append(group)
    context = {
        "user": user,
        "groups": tabGroup
    }
    return render(request, "ajax_group_new_user.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_super_user)
def add_new_user_to_group(request):
    if request.method == "POST":
        id = request.POST["id"]
        name = request.POST["name"]
        user = User.objects.get(id=id)
        group = Group.objects.get(name=name)
        user.groups.add(group)
        #messages.success(request, "Admin associé au groupe avec succès.")
        return redirect("settings/db_supuser")
    
def alert_signature_contrat(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
        setting = get_setting_sup_user()
        try:
            # Récuperer l'établissement
            etablissement = Etablissement.objects.get(id=etablissement_id)
            # Récuperer l'année académique de l'établissement
            anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
            # Récuperer l'année académique du groupe
            anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
            # Récuperer le contrat 
            contrat = ContratEtablissement.objects.filter(etablissement=etablissement, anneeacademique=anneeacademique_group, status_signature=False).first()
        except:
            contrat = None
            
        context = {
            "setting": setting,
            "contrat": contrat
        }
        return render(request, "alert_signature_contrat.html", context)
    else:
        setting = get_setting(anneeacademique_id)
        try:
            # Récuperer l'année académique de l'établissement
            anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
            # Récuperer le contrat 
            contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique, status_signature=False).first()
        except:
            contrat = None
            
        context = {
            "setting": setting,
            "contrat": contrat
        }
        return render(request, "alert_signature_contrat.html", context)
    
def alert_signature_contrat_de(request, id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
        setting = get_setting_sup_user()
        try:
            # Récuperer l'établissement
            etablissement = Etablissement.objects.get(id=etablissement_id)
            # Récuperer l'année académique de l'établissement
            anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
            # Récuperer l'année académique du groupe
            anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
            # Récuperer le contrat 
            contrat = ContratEtablissement.objects.filter(etablissement=etablissement, anneeacademique=anneeacademique_group, status_signature=False).first()
        except:
            contrat = None
            
        context = {
            "setting": setting,
            "contrat": contrat
        }
        return render(request, "alert_signature_contrat.html", context)
    else:
        setting = get_setting(anneeacademique_id)
        try:
            # Récuperer l'année académique de l'établissement
            anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
            # Récuperer le contrat 
            contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique, status_signature=False).first()
        except:
            contrat = None
            
        context = {
            "setting": setting,
            "contrat": contrat
        }
        return render(request, "alert_signature_contrat.html", context)

def send_message(request):
    to = '+330755873258'  # numéro du destinataire
    msg = "Bonjour Monsieur Ngalebo Le Prince d'avoir inscris votre enfant dans notre école"
    sid = send_sms(to, msg)
    
    return redirect('settings/help')