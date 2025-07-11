# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.contrib import messages
# Importation des modules locaux
from .models import Emargement
from salle.models import Salle
from emploi_temps.models import EmploiTemps
from matiere.models import Matiere
from enseignement.models import Enseigner
from renumeration.models import Renumeration, Contrat
from anneeacademique.models import AnneeCademique
from cycle.models import Cycle
from renumeration.views import calculer_montant
from school.views import get_setting
from school.methods import heure_par_jour_et_moyenne, nombre_absence_enseignant, salaire_enseignant_cycle_fondament_avec_absence
from renumeration.views import format_time
from app_auth.decorator import allowed_users
from renumeration.views import status_contrat_user
from scolarite.utils.crypto import dechiffrer_param

permission_directeur_etude = ['Promoteur', 'Directeur Général', 'Directeur des Etudes']
permission_enseignant = ['Enseignant']

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_directeur_etude)
def emargements(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        enseignants_emargements = (Emargement.objects.values("enseignant_id")
                               .filter(anneeacademique_id=anneeacademique_id)
                               .annotate(nb_emargements =Count("enseignant_id")))
        liste_emargements = []
        for ee in enseignants_emargements:
            user = User.objects.get(id=ee["enseignant_id"])
            dic = {}
            dic["enseignant"] = user
            # Compter le nombre de salles
            salles_emargements = (Emargement.objects.values("salle_id")
                               .filter(anneeacademique_id=anneeacademique_id, enseignant_id=ee["enseignant_id"])
                               .annotate(nb_salles=Count("salle_id")))
            nb_salles = 0
            for se in salles_emargements:
                 nb_salles += 1
                 
            dic["nb_salles"] = nb_salles
            
            liste_emargements.append(dic)
            
        context = {
            "emargements": liste_emargements,
            "setting": setting
        }
        return render(request, "emargements.html", context=context)

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_directeur_etude)   
def salles_emargements(request, enseignant_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    id = int(dechiffrer_param(str(enseignant_id)))
    enseignant = User.objects.get(id=id)
    salles_emargements = (Emargement.objects.values("salle_id")
                  .filter(anneeacademique_id=anneeacademique_id, enseignant_id=id)
                  .annotate(nb_emargements=Count("salle_id")))
    
    tabEmargements = []
    for se in salles_emargements:
        salle = Salle.objects.get(id=se["salle_id"])
        dic = {}
        dic["salle"] = salle
        
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            matieres_emargements = (Emargement.objects.values("matiere_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=id, salle_id=se["salle_id"])
                    .annotate(nb_emargements=Count("matiere_id")))
            
            nb_matieres = 0
            for me in matieres_emargements:
                nb_matieres += 1
            dic["nb_matieres"] = nb_matieres
            tabEmargements.append(dic)
        else:    
            dic["nb_emargements"] = se["nb_emargements"]
            dic["emargements"] = Emargement.objects.filter(enseignant_id=id, salle_id=salle.id, anneeacademique_id=anneeacademique_id)
            tabEmargements.append(dic)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)        
    context = {
        "emargements": tabEmargements,
        "enseignant": enseignant,
        "anneeacademique": anneeacademique,
        "setting": setting,
    }   
    
    return render(request, "salles_emargements.html", context=context) 

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_directeur_etude)    
def matieres_emargements(request, enseignant_id, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    en_id = int(dechiffrer_param(str(enseignant_id)))
    sl_id = int(dechiffrer_param(str(salle_id)))
    
    enseignant = User.objects.get(id=en_id)
    salle = Salle.objects.get(id=sl_id)
    matieres_emargements = (Emargement.objects.values("matiere_id")
                  .filter(anneeacademique_id=anneeacademique_id, enseignant_id=en_id, salle_id=sl_id)
                  .annotate(nb_emargements=Count("matiere_id")))
    
    tabEmargements = []
    for me in matieres_emargements:
        matiere = Matiere.objects.get(id=me["matiere_id"])
        dic = {}
        dic["matiere"] = matiere
        # Compter le nombre de mois
        months_emargements = (Emargement.objects.values("month")
                               .filter(anneeacademique_id=anneeacademique_id, enseignant_id=en_id, matiere_id=me["matiere_id"])
                               .annotate(nb_month=Count("month")))
        nb_month = 0
        for se in months_emargements:
            nb_month += 1
            
        dic["nb_month"] = nb_month
        tabEmargements.append(dic)

    context = {
        "emargements": tabEmargements,
        "setting": setting,
        "enseignant": enseignant,
        "salle": salle
    }   
    
    return render(request, "matieres_emargements.html", context=context) 

@login_required(login_url='connection/account')   
@allowed_users(allowed_roles=permission_directeur_etude)  
def months_emargements(request, enseignant_id, salle_id, matiere_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    en_id = int(dechiffrer_param(str(enseignant_id)))
    sl_id = int(dechiffrer_param(str(salle_id)))
    mt_id = int(dechiffrer_param(str(matiere_id)))
    
    enseignant = User.objects.get(id=en_id)
    salle = Salle.objects.get(id=sl_id)
    matiere = Matiere.objects.get(id=mt_id)
    months_emargements = (Emargement.objects.values("month")
                  .filter(anneeacademique_id=anneeacademique_id, enseignant_id=en_id, salle_id=sl_id, matiere_id=mt_id)
                  .annotate(nb_emargements=Count("month")))
    
    tabEmargements = []
    for me in months_emargements:
        dic = {}
        dic["month"] = me["month"]            
        dic["nb_emargements"] = me["nb_emargements"]
        tabEmargements.append(dic)

    context = {
        "emargements": tabEmargements,
        "setting": setting,
        "enseignant": enseignant,
        "salle": salle,
        "matiere": matiere
    }   
    
    return render(request, "months_emargements.html", context=context) 
        
@login_required(login_url='connection/account')   
@allowed_users(allowed_roles=permission_directeur_etude) 
def detail_emargements(request, enseignant_id, salle_id, matiere_id, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    en_id = int(dechiffrer_param(str(enseignant_id)))
    sl_id = int(dechiffrer_param(str(salle_id)))
    mt_id = int(dechiffrer_param(str(matiere_id)))
    month_cry = dechiffrer_param(str(month))
    
    enseignant = User.objects.get(id=en_id)
    salle = Salle.objects.get(id=sl_id)
    matiere = Matiere.objects.get(id=mt_id)
    emargements = Emargement.objects.filter(
        anneeacademique_id=anneeacademique_id, 
        enseignant_id=en_id, 
        salle_id=sl_id,
        matiere_id=mt_id,
        month=month_cry)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "emargements": emargements,
        "enseignant": enseignant,
        "salle": salle,
        "matiere": matiere,
        "month": month_cry,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_emargements.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etude)
def add_emargement(request, emploi_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'emargement
    emploitemps_id = int(dechiffrer_param(str(emploi_id)))
    emploitemps = EmploiTemps.objects.get(id=emploitemps_id)  
    months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Novembre', 'Décembre']
    seances = ['Cours','Travail Dirigé', 'Contrôle', 'Travail Pratique'] 
    
    # Verifier le statut du contrat de l'enseignant 
    user_id = emploitemps.enseignant.id
    status_contrat = status_contrat_user(user_id, anneeacademique_id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "emploitemps": emploitemps,
        "months": months,
        "seances": seances,
        "status_contrat": status_contrat,
        "contrat": contrat
    }
    return render(request, "add_emargement.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etude)
def add_em(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        month = bleach.clean(request.POST["month"].strip())
        date_emargement = request.POST["date_emargement"]
        emploi_id = request.POST["emploi_id"]
         
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)    
        # Récuperer l'emploi du temps
        emploitemps = EmploiTemps.objects.get(id=emploi_id)  
        
        matiere = None
        seance = ""
        titre = ""
        heure_debut = ""
        heure_fin = ""
        if emploitemps.salle.cycle in ["Collège", "Lycée"]:
            matiere = emploitemps.matiere
            seance = bleach.clean(request.POST["seance"].strip())
            titre = bleach.clean(request.POST["titre"].strip())
            heure_debut = emploitemps.heure_debut
            heure_fin = emploitemps.heure_fin
        else:
            heure_debut = request.POST["heure_debut"]
            heure_fin = request.POST["heure_fin"]
        user_id = request.user.id
        query = Emargement.objects.filter(
            anneeacademique_id=emploitemps.anneeacademique.id,
            salle_id=emploitemps.salle.id,
            matiere=matiere,
            enseignant_id=emploitemps.enseignant.id,
            jour=emploitemps.jour, 
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            date_emargement=date_emargement,
            month=month)
        
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})         
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet émargement existe déjà."})
        else:
                
            emargement = Emargement(
                anneeacademique_id=emploitemps.anneeacademique.id,
                salle_id=emploitemps.salle.id,
                matiere=matiere,
                enseignant_id=emploitemps.enseignant.id,
                jour=emploitemps.jour, 
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                user_id=user_id,
                date_emargement=date_emargement,
                seance=seance,
                titre=titre,
                month=month
            )
            # Nombre d'émargement avant l'ajout
            count0 = Emargement.objects.all().count()
            emargement.save()
            # Nombre d'emargement après l'ajout
            count1 = Emargement.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Emargement enrgistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'opération a échouée."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etude)
def edit_emargement(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    emargement_id = int(dechiffrer_param(str(id)))
    emargement = Emargement.objects.get(id=emargement_id)
    months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Novembre', 'Décembre']
    seances = ['Cours','Travail Dirigé', 'Contrôle', 'Travail Pratique']    
    tabMonths = [month for month in months if month != emargement.month]
            
    tabSeance = [seance for seance in seances if seance != emargement.seance] 
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "emargement": emargement,
        "setting": setting,
        "months": tabMonths,
        "seances":tabSeance,
        "contrat": contrat
    }
    return render(request, "edit_emargement.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etude)
def edit_em(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            emargement = Emargement.objects.get(id=id)
        except:
            emargement = None

        if emargement is None:
            return JsonResponse({'status':1})
        else:
            month = bleach.clean(request.POST["month"].strip())
            date_emargement = request.POST["date_emargement"]
            
            matiere = None
            seance = ""
            titre = ""
            heure_debut = ""
            heure_fin = ""
            if emargement.salle.cycle.libelle in ["Collège", "Lycée"]:
                matiere = emargement.matiere
                seance = bleach.clean(request.POST["seance"].strip())
                titre = bleach.clean(request.POST["titre"].strip())
                heure_debut = emargement.heure_debut
                heure_fin = emargement.heure_fin
            else:
                heure_debut = request.POST["heure_debut"]
                heure_fin = request.POST["heure_fin"]
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
            #On verifie si cette classe a été déjà enregistrée
            emargements = Emargement.objects.exclude(id=id)
            tabEmargements = []
            for e in emargements:          
                tabEmargements.append(e.date_emargement)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})       
            #On verifie si cette classe existe déjà
            if date_emargement in tabEmargements:
                return JsonResponse({
                    "status": "error",
                    "message": "Cet émargement existe déjà."})
            else:
                emargement.titre = titre
                emargement.seance = seance
                emargement.heure_debut = heure_debut
                emargement.heure_fin = heure_fin
                emargement.month = month
                emargement.matiere = matiere
                emargement.date_emargement = date_emargement
                emargement.user_id = user_id
                emargement.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Emargement enregistré avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etude)
def del_emargement(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        try:
            emargement_id = int(dechiffrer_param(str(id)))
            emargement = Emargement.objects.get(id=emargement_id)
        except:
            emargement = None
            
        if emargement:
            # Nombre d'émargements avant la suppression
            count0 = Emargement.objects.all().count()
            emargement.delete()
            # Nombre d'émargements après la suppression
            count1 = Emargement.objects.all().count()
            if count1 < count0: 
                messages.success(request, "ELément supprimé avec succès.")
            else:
                messages.error(request, "La suppression a échouée.")
        return redirect("detail_emargements", emargement.salle.id, emargement.matiere.id, emargement.month)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def mes_emargements(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_emargements = (Emargement.objects.values("salle_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("salle_id")))
    
    tabEmargements = []
    for se in salles_emargements:
        dic = {}
        salle = Salle.objects.get(id=se["salle_id"])
        dic["salle"] = salle
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            # Recuperer les matières auxquelles l'enseignants a été enumerées pour cette salle
            matieres_emargements = (Emargement.objects.values("matiere_id")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=se["salle_id"])
                                    .annotate(nb_matieres=Count("matiere_id")))
            
            matieres = []
            for me in matieres_emargements:
                dic_matiere = {}
                matiere = Matiere.objects.get(id=me["matiere_id"])
                dic_matiere["matiere"] = matiere
                
                # Recuperer les mois auxquelles l'enseignants a été enumerées pour cette salle
                months_emargements = (Emargement.objects.values("month")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=se["salle_id"], matiere_id=me["matiere_id"])
                                    .annotate(nb_months=Count("month")))
                
                months = []
                for month_emargement in months_emargements:
                    dic_month = {}
                    month = month_emargement["month"]
                    dic_month["month"] = month
                    # Récuperer tous les emargements de ce mois
                    emargements = Emargement.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=se["salle_id"], matiere_id=me["matiere_id"], month=month_emargement["month"])
                    dic_month["liste_emargements"] = emargements
                    
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
                    
                    dic_month["total_time"] = formatted_time
                    
                    # Recuperer le cout par heure de la matière
                    enseignement = Enseigner.objects.filter(
                        salle_id=se["salle_id"],
                        matiere_id=me["matiere_id"],
                        anneeacademique_id=anneeacademique_id).first()
                    
                    dic_month["cout_heure"] = enseignement.cout_heure
                    dic_month["montant_payer"] = calculer_montant(enseignement.cout_heure, formatted_time)
                    
                    months.append(dic_month)
                    
                dic_matiere["months"] = months
                matieres.append(dic_matiere)
                
            dic["matieres"] = matieres  
            tabEmargements.append(dic)
        else:
            # Recuperer les mois auxquelles l'enseignants a été enumerées pour cette salle
            months_emargements = (Emargement.objects.values("month")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=salle.id)
                                    .annotate(nb_months=Count("month")))
            
            months = []
            for me in months_emargements:    
                dic_month = {}
                month = me["month"]
                dic_month["month"] = month          
                emargements = Emargement.objects.filter(enseignant_id=user_id, salle_id=salle.id, month=month, anneeacademique_id=anneeacademique_id)        
                # Initialisation avec une durée nulle
                total_delta = timedelta(0)
                tabEmargement = []
                for emarg in emargements:
                    dic_emarg_enseignant_fondament = {}
                    dic_emarg_enseignant_fondament["emargement"] = emarg
                    # Convertir les objets time en timedelta 
                    # Heure total que l'enseignant a fait 
                    start_delta_emargement = timedelta(hours=emarg.heure_debut.hour, minutes=emarg.heure_debut.minute)
                    end_delta_emargement = timedelta(hours=emarg.heure_fin.hour, minutes=emarg.heure_fin.minute)
                    # Calculer la somme des deux
                    heure_faite =  end_delta_emargement - start_delta_emargement
                    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                    heure_faite_seconds = heure_faite.total_seconds()
                    heure_faite_hours = int(heure_faite_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                    heure_faite_minutes = int((heure_faite_seconds % 3600) // 60)

                    # Afficher le résultat au format HH:MM
                    formatted_time_heure_faite = f"{heure_faite_hours:02}:{heure_faite_minutes:02}"
                    dic_emarg_enseignant_fondament["heure_faite"] = formatted_time_heure_faite
                    # Heure totale que l'enseignant est censé faire par jour
                    emploistemps = EmploiTemps.objects.filter(jour=emarg.jour, enseignant_id=emarg.enseignant.id, anneeacademique_id=anneeacademique_id).first()
                    start_delta_emploitemps = timedelta(hours=emploistemps.heure_debut.hour, minutes=emarg.heure_debut.minute)
                    end_delta_emploitemps = timedelta(hours=emploistemps.heure_fin.hour, minutes=emarg.heure_fin.minute)
                    heure_faire =  end_delta_emploitemps - start_delta_emploitemps
                    
                    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                    heure_faire_seconds = heure_faire.total_seconds()
                    heure_faire_hours = int(heure_faire_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                    heure_faire_minutes = int((heure_faire_seconds % 3600) // 60)

                    # Afficher le résultat au format HH:MM
                    formatted_time_heure_faire = f"{heure_faire_hours:02}:{heure_faire_minutes:02}"
                    dic_emarg_enseignant_fondament["heure_faire"] = formatted_time_heure_faire
                    
                    total_heure = heure_faire - heure_faite # Heure total du retard de l'enseignant 
                    
                    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                    total_heure_seconds = total_heure.total_seconds()
                    total_heure_hours = int(total_heure_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                    total_heure_minutes = int((total_heure_seconds % 3600) // 60)

                    # Afficher le résultat au format HH:MM
                    formatted_time_total_heure = f"{total_heure_hours:02}:{total_heure_minutes:02}"
                    dic_emarg_enseignant_fondament["total_heure"] = formatted_time_total_heure
                    
                    total_delta += total_heure
                    tabEmargement.append(dic_emarg_enseignant_fondament)
                    
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                total_seconds = total_delta.total_seconds()
                total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                total_minutes = int((total_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time = f"{total_hours:02}:{total_minutes:02}"
                        
                dic_month["total_time"] = formatted_time                
                dic_month["emargements"] = tabEmargement  
                
                contrat = Contrat.objects.filter(user_id=user_id, type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).first()
                cout_jour = contrat.amount/20 
                # Cout par heure
                moyenne = heure_par_jour_et_moyenne(user_id, salle.id, anneeacademique_id)[1]
                cout_heure = 0
                if moyenne > 0:
                    cout_heure = float(cout_jour) / float(moyenne)
                # Coût par jour
                dic_month["cout_jour"] = cout_jour
                # Cout par heure
                dic_month["cout_heure"] = cout_heure
                # Nombre d'absences par mois de l'enseignant
                dic_month["nombre_absences"] = nombre_absence_enseignant(month, user_id, salle.id, anneeacademique_id)
                # Montant brute à payer
                dic_month["montant_payer"] = salaire_enseignant_cycle_fondament_avec_absence(month, user_id, salle.id, anneeacademique_id)    
                    
                months.append(dic_month)
            dic["months"] = months
            tabEmargements.append(dic)
    tabMonths = []    
    emargements_groupes = (Emargement.objects.values("month")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("month"))
    )
    
    for emargement in emargements_groupes:
        tabMonths.append(emargement["month"])
    
    # Récuperer tous les émargements de l'enseignants     
    emargements_enseignants = Emargement.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
    for emargement in emargements_enseignants:
        # Mise à jour du statut pour marquer la lecture
        emargement.status = True
        emargement.save()
        
    
    context = {
        "setting": setting,
        "emargements": tabEmargements,
        "months": tabMonths
    }
    
    return render(request, "mes_emargements.html", context=context)


@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_directeur_etude)
def heures_emargements(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
        
    months_emargements = (Emargement.objects.values("month")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nb_emargements=Count("month")))
        
    months = []
    for me in months_emargements:
        months.append(me["month"])
        
    context = {
        "setting": setting,
        "months": months
    }
    
    return render(request, "heures_emargements.html", context)


def ajax_heures_emargements(request, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle_id = request.session.get('cycle_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    salles_emargements = (Emargement.objects.values("salle_id")
                     .filter(month=month, anneeacademique_id=anneeacademique_id)
                     .annotate(nb_emargements = Sum("salle_id")))
    
    tabEmargementEnseignant = []
    for se in salles_emargements:
        dic = {}
        salle = Salle.objects.get(id=se["salle_id"])
        dic["salle"] = salle
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            emargements = Emargement.objects.filter(month=month, anneeacademique_id=anneeacademique_id, salle_id=salle.id)
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
                    
            dic["total_time"] = formatted_time
            
            # Calculer le nombre d'heure par matière de la salle
            matieres_emargements = (Emargement.objects.values("matiere_id")
                                    .filter(month=month, anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                                    .annotate(nb_emargements=Count("matiere_id")))
            tabMatieres = []
            for me in matieres_emargements:
                dic_matiere = {}
                matiere = Matiere.objects.get(id=me["matiere_id"])
                dic_matiere["matiere"] = matiere
                liste_emargements_matieres = Emargement.objects.filter(month=month, anneeacademique_id=anneeacademique_id, salle_id=salle.id, matiere_id=matiere.id)
                # Initialisation avec une durée nulle
                total_delta_matiere = timedelta(0)
                for lem in liste_emargements_matieres:
                    # Convertir les objets time en timedelta
                    start_delta_matiere = timedelta(hours=lem.heure_debut.hour, minutes=lem.heure_debut.minute)
                    end_delta_matiere = timedelta(hours=lem.heure_fin.hour, minutes=lem.heure_fin.minute)
                    # Calculer la somme des deux
                    total_delta_matiere +=  end_delta_matiere - start_delta_matiere
                            
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                total_seconds_matiere = total_delta_matiere.total_seconds()
                total_hours_matiere = int(total_seconds_matiere // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                total_minutes_matiere = int((total_seconds_matiere % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_matiere = f"{total_hours_matiere:02}:{total_minutes_matiere:02}"
                        
                dic_matiere["total_time_matiere"] = formatted_time_matiere
                tabMatieres.append(dic_matiere)
            
            dic["matieres"] = tabMatieres 
            tabEmargementEnseignant.append(dic)
            
        else:
            
            emargements = Emargement.objects.filter(month=month, anneeacademique_id=anneeacademique_id, salle_id=salle.id)        
            # Initialisation avec une durée nulle
            total_delta = timedelta(0)
            tabEmargement = []
            for emarg in emargements:
                dic_emarg_enseignant_fondament = {}
                dic_emarg_enseignant_fondament["emargement"] = emarg
                # Convertir les objets time en timedelta 
                # Heure total que l'enseignant a fait 
                start_delta_emargement = timedelta(hours=emarg.heure_debut.hour, minutes=emarg.heure_debut.minute)
                end_delta_emargement = timedelta(hours=emarg.heure_fin.hour, minutes=emarg.heure_fin.minute)
                # Calculer la somme des deux
                heure_faite =  end_delta_emargement - start_delta_emargement
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                heure_faite_seconds = heure_faite.total_seconds()
                heure_faite_hours = int(heure_faite_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                heure_faite_minutes = int((heure_faite_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_heure_faite = f"{heure_faite_hours:02}:{heure_faite_minutes:02}"
                dic_emarg_enseignant_fondament["heure_faite"] = formatted_time_heure_faite
                # Heure totale que l'enseignant est censé faire par jour
                emploistemps = EmploiTemps.objects.filter(jour=emarg.jour, enseignant_id=emarg.enseignant.id, anneeacademique_id=anneeacademique_id).first()
                start_delta_emploitemps = timedelta(hours=emploistemps.heure_debut.hour, minutes=emarg.heure_debut.minute)
                end_delta_emploitemps = timedelta(hours=emploistemps.heure_fin.hour, minutes=emarg.heure_fin.minute)
                heure_faire =  end_delta_emploitemps - start_delta_emploitemps
                
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                heure_faire_seconds = heure_faire.total_seconds()
                heure_faire_hours = int(heure_faire_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                heure_faire_minutes = int((heure_faire_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_heure_faire = f"{heure_faire_hours:02}:{heure_faire_minutes:02}"
                dic_emarg_enseignant_fondament["heure_faire"] = formatted_time_heure_faire
                
                total_heure = heure_faire - heure_faite # Heure total du retard de l'enseignant 
                
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                total_heure_seconds = total_heure.total_seconds()
                total_heure_hours = int(total_heure_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                total_heure_minutes = int((total_heure_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_total_heure = f"{total_heure_hours:02}:{total_heure_minutes:02}"
                dic_emarg_enseignant_fondament["total_heure"] = formatted_time_total_heure
                
                total_delta += total_heure
                tabEmargement.append(dic_emarg_enseignant_fondament)
                
            # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
            total_seconds = total_delta.total_seconds()
            total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
            total_minutes = int((total_seconds % 3600) // 60)

            # Afficher le résultat au format HH:MM
            formatted_time = f"{total_hours:02}:{total_minutes:02}"
                    
            dic["total_time"] = formatted_time                
            dic["emargements"] = tabEmargement   
            tabEmargementEnseignant.append(dic)
            
    # Récuperer le cycle
    cycle = None
    if cycle_id:
        cycle = Cycle.objects.get(id=cycle_id)         
    context = {
        "month": month,
        "emargementEnseignant": tabEmargementEnseignant,
        "cycle": cycle,
        "setting": setting
    }       
    return render(request, "ajax_heures_emargements.html", context)

def ajax_emargements_ens(request, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    enseignant_id = request.user.id
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
                matiere = Matiere.objects.get(id=matiere_id)
                dic_matiere["matiere"] = matiere    
                
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
                        
                    dic_em["hour"] = format_time(total_delta)
                    
                    list_emargements.append(dic_em)     
                
                dic_matiere["emargements"] = list_emargements        
                
                dic_matiere["total_time"] = format_time(total_delta)
                
                # Calculer le montant à payer pour cette matière
                dic_matiere["montant_total_matiere"] = calculer_montant(enseignement.cout_heure, format_time(total_delta))
                
                total_matiere_delta += total_delta
                
                matieres.append(dic_matiere)
            
            dic["total_matiere_time"] = format_time(total_matiere_delta)
            dic["matieres"] = matieres
            
            montant_total = calculer_montant(somme_cout_heure, format_time(total_matiere_delta))
            dic["montant_total_salle"] = montant_total
            tabEmargements.append(dic)
            total_salle_delta += total_matiere_delta
            
            montant_payer += montant_total
        else:
            emargements = Emargement.objects.filter(month=month, anneeacademique_id=anneeacademique_id, salle_id=salle.id)        
            # Initialisation avec une durée nulle
            total_delta = timedelta(0)
            tabEmargement = []
            for emarg in emargements:
                dic_emarg_enseignant_fondament = {}
                dic_emarg_enseignant_fondament["emargement"] = emarg
                # Convertir les objets time en timedelta 
                # Heure total que l'enseignant a fait 
                start_delta_emargement = timedelta(hours=emarg.heure_debut.hour, minutes=emarg.heure_debut.minute)
                end_delta_emargement = timedelta(hours=emarg.heure_fin.hour, minutes=emarg.heure_fin.minute)
                # Calculer la somme des deux
                heure_faite =  end_delta_emargement - start_delta_emargement
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                heure_faite_seconds = heure_faite.total_seconds()
                heure_faite_hours = int(heure_faite_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                heure_faite_minutes = int((heure_faite_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_heure_faite = f"{heure_faite_hours:02}:{heure_faite_minutes:02}"
                dic_emarg_enseignant_fondament["heure_faite"] = formatted_time_heure_faite
                # Heure totale que l'enseignant est censé faire par jour
                emploistemps = EmploiTemps.objects.filter(jour=emarg.jour, enseignant_id=emarg.enseignant.id, anneeacademique_id=anneeacademique_id).first()
                start_delta_emploitemps = timedelta(hours=emploistemps.heure_debut.hour, minutes=emarg.heure_debut.minute)
                end_delta_emploitemps = timedelta(hours=emploistemps.heure_fin.hour, minutes=emarg.heure_fin.minute)
                heure_faire =  end_delta_emploitemps - start_delta_emploitemps
                
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                heure_faire_seconds = heure_faire.total_seconds()
                heure_faire_hours = int(heure_faire_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                heure_faire_minutes = int((heure_faire_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_heure_faire = f"{heure_faire_hours:02}:{heure_faire_minutes:02}"
                dic_emarg_enseignant_fondament["heure_faire"] = formatted_time_heure_faire
                
                total_heure = heure_faire - heure_faite # Heure total du retard de l'enseignant 
                
                # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
                total_heure_seconds = total_heure.total_seconds()
                total_heure_hours = int(total_heure_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
                total_heure_minutes = int((total_heure_seconds % 3600) // 60)

                # Afficher le résultat au format HH:MM
                formatted_time_total_heure = f"{total_heure_hours:02}:{total_heure_minutes:02}"
                dic_emarg_enseignant_fondament["total_heure"] = formatted_time_total_heure
                
                total_delta += total_heure
                tabEmargement.append(dic_emarg_enseignant_fondament)
                
            # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
            total_seconds = total_delta.total_seconds()
            total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
            total_minutes = int((total_seconds % 3600) // 60)

            # Afficher le résultat au format HH:MM
            formatted_time = f"{total_hours:02}:{total_minutes:02}"
                    
            dic["total_time"] = formatted_time
            montant_payer += salaire_enseignant_cycle_fondament_avec_absence(month, enseignant_id, salle.id, anneeacademique_id)    
            
    # Verifier si l'enseignant a déjà été rénuméré ou pas
    query = Renumeration.objects.filter(user_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
    status_paye = "Impayé"
    if query.exists():
        status_paye = "Payé"
    else:
        month_actuel = datetime.now()
        if month == month_actuel:
            status_paye = "Mois en cours"
    context = {
        "setting": get_setting(anneeacademique_id),
        "status_paye": status_paye,
        "montant_paye": montant_payer
    }       
    return render(request, "ajax_emargements_ens.html", context)
