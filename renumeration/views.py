# Importation des modules standards
import bleach
import re
import base64
import pdfkit
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.http.response import HttpResponse
from django.template.loader import get_template
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
# Importation des modules locaux
from .models import Renumeration, Contrat
from emargement.models import Emargement
from salle.models import Salle
from matiere.models import Matiere
from enseignement.models import Enseigner
from paiement.models import Payment
from depense.models import Depense
from anneeacademique.models import AnneeCademique
from inscription.models import Inscription
from etablissement.models import Etablissement
from app_auth.models import EtablissementUser
from emploi_temps.models import EmploiTemps
from school.views import get_setting
from app_auth.decorator import allowed_users
from school.methods import periode_annee_scolaire, month_contrat_user, heure_par_jour_et_moyenne, nombre_absence_enseignant, salaire_enseignant_cycle_fondament_avec_absence
from scolarite.utils.crypto import dechiffrer_param

permission_gestionnaire = ['Promoteur', 'Directeur Général', 'Gestionnaire']
permission_Promoteur_DG_DE = ['Promoteur', 'Directeur Général', 'Gestionnaire']
permission_gestionnaire_enseignant = ['Promoteur', 'Directeur Général', 'Gestionnaire', 'Enseignant']
permission_enseignant = ['Enseignant']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire', 'Surveillant Général']
permission_users = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire', 'Surveillant Général', 'Enseignant']

# determiner la somme totale de la caisse
def somme_totale_caisse(anneeacademique_id):
    months = month_actifs(anneeacademique_id)
    recette_totale = 0
    for month in months:
        total_renum_enseignant = 0        
        # Somme totale payée par les étudiants
        total_paiement_student = (Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
            
        months_emargements = (Emargement.objects.values("salle_id")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(nb_emargements=Count("salle_id")))
        
        for me in months_emargements:
            # Somme totale qu'on a payé les enseignants
            sum_renum = total_renum_salle(me["salle_id"], anneeacademique_id, month)
            total_renum_enseignant += sum_renum
            
        # Calculer toutes les indemnités des enseignants du secondaire d'un mois
        sum_indemnite = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
        
        # Calucler le montant total de renumeration des administarteurs
        total_amount = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
        total_renum_admin = float(total_amount) + float(sum_indemnite)
        
        
        # Recupérer les dépenses d'un mois
        total_depense = 0
        type_depenses = (Depense.objects.values("signe")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(sum_depense=Sum("amount")))
        for tp in type_depenses:
            if tp["signe"] == "Entrée":
                total_depense += float(tp["sum_depense"])
            else:
                total_depense = total_depense - float(tp["sum_depense"]) 
        
        recette_month = float(total_paiement_student) - float(total_renum_enseignant) - float(sum_indemnite) - total_renum_admin + total_depense
        
        recette_totale += recette_month
        
    # somme total des inscription
    total_inscription = (Inscription.objects.filter(anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))['amount__sum'] or 0)
   
    total = float(recette_totale) + float(total_inscription)

    return total

# Récuperer le mois et l'année de la période scolaire
def month_year_periode_annee_scolaire_remuneration(anneeacademique_id):
    try:
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    except ObjectDoesNotExist:
        return []  # Retourne une liste vide si l'année académique n'existe pas

    start_date = anneeacademique.start_date
    end_date = anneeacademique.end_date

    # Génération des mois dans l'intervalle
    months = []
    current_date = start_date.replace(day=1)  # S'assurer de commencer au début du mois

    while current_date <= end_date:
        dic = {} 
        dic["month"] = current_date.strftime("%m")
        dic["year"] = current_date.strftime("%Y")
        months.append(dic)
        # Passer au mois suivant
        next_month = current_date.month % 12 + 1
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        current_date = current_date.replace(month=next_month, year=next_year)

    month_format = []
    for month in months:
        if month["month"] == '01':
            dic = {}
            dic["month"] = "Janvier"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '02':
            dic = {}
            dic["month"] = "Février"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '03':
            dic = {}
            dic["month"] = "Mars"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '04':
            dic = {}
            dic["month"] = "Avril"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '05':
            dic = {}
            dic["month"] = "Mai"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '06':
            dic = {}
            dic["month"] = "Juin"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '07':
            dic = {}
            dic["month"] = "Juillet"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month == '08':
            dic = {}
            dic["month"] = "Août"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '09':
            dic = {}
            dic["month"] = "Septembre"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '10':
            dic = {}
            dic["month"] = "Octobre"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '11':
            dic = {}
            dic["month"] = "Novembre"
            dic["year"] = month["year"]
            month_format.append(dic)
        else:
            dic = {}
            dic["month"] = "Décembre"
            dic["year"] = month["year"]
            month_format.append(dic)
    return month_format  # Retourne la liste des mois

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)
def remunerations_enseignants(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    remunerations_enseignants_fondamental_group = (Renumeration.objects.values("user_id")
                           .filter(anneeacademique_id=anneeacademique_id)
                           .annotate(nombre_renumerations=Count("user_id"))
                           .exclude(type_renumeration="Administrateur scolaire")
                           .exclude(type_renumeration="Enseignant du cycle secondaire")
    )
    remunerations_enseignants_fondamental = []
    for re in remunerations_enseignants_fondamental_group:
        user = User.objects.get(id=re["user_id"])   
        dic = {}
        dic["user"] = user
        renums = (
            Renumeration.objects.filter(user_id=re["user_id"], anneeacademique_id=anneeacademique_id)
                                .exclude(type_renumeration="Administrateur scolaire")
                                .exclude(type_renumeration="Enseignant du cycle secondaire")
        )
        dic["remunerations"] = renums
        dic["nombre_renumerations"] = renums.count()
        remunerations_enseignants_fondamental.append(dic)
        
    remunerations_enseignants_secondaire_group = (Renumeration.objects.values("user_id")
                           .filter(anneeacademique_id=anneeacademique_id)
                           .annotate(nombre_renumerations=Count("user_id"))
                           .exclude(type_renumeration="Administrateur scolaire")
                           .exclude(type_renumeration="Enseignant du cycle fondamental")
    )
    remunerations_enseignants_secondaire = []
    for re in remunerations_enseignants_secondaire_group:
        user = User.objects.get(id=re["user_id"])   
        dic = {}
        dic["user"] = user
        renums = (
            Renumeration.objects.filter(user_id=re["user_id"], anneeacademique_id=anneeacademique_id)
                                .exclude(type_renumeration="Administrateur scolaire")
                                .exclude(type_renumeration="Enseignant du cycle fondamental")
        )
        dic["remunerations"] = renums
        dic["nombre_renumerations"] = renums.count()
        remunerations_enseignants_secondaire.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "remunerations_enseignants_fondamental": remunerations_enseignants_fondamental,
        "remunerations_enseignants_secondaire": remunerations_enseignants_secondaire,
        "anneeacademique": anneeacademique
    }
    
    return render(request, "remun_enseignant/remunerations_enseignants.html", context)

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)
def resume_remu_enseignant_seondaire(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer les mois émargés
    months_emargements = (Emargement.objects.values("month")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nombre_emargements=Count("month"))
    )
        
    emargements = []
    for me in months_emargements:
        dic = {}
        dic["month"] = me["month"]
        # Récuperer les enseignant qui ont été émargé pour ce mois
        enseignants_emargements = (Emargement.objects.values("enseignant_id")
                                   .filter(anneeacademique_id=anneeacademique_id, month=me["month"])
                                   .annotate(nombre_emargements=Count("enseignant_id"))
        ) 
        nombre_enseignants_impayes = 0
        enseignants = []
        for ee in enseignants_emargements:
            enseignant = User.objects.get(id=ee["enseignant_id"])
            # Contrat de l'enseignant 
            contrat = Contrat.objects.filter(user=enseignant, anneeacademique=anneeacademique, type_contrat="Enseignant du cycle secondaire")
            if contrat.exists() and not Renumeration.objects.filter(user_id=enseignant.id, anneeacademique_id=anneeacademique_id, type_renumeration="Enseignant du cycle secondaire").exists():
                nombre_enseignants_impayes += 1
                enseignants.append(enseignant)
                
        dic["nombre_enseignants_impayes"] = nombre_enseignants_impayes 
        dic["enseignants"] = enseignants
        
        emargements.append(dic)  
    
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()        
    context = {
        "setting": setting,
        "emargements": emargements,
        "anneeacademique": anneeacademique,
        "contrat": contrat
    }
    return render(request, "remun_enseignant/resume_remu_enseignant_seondaire.html", context)

def ajax_detail_teacher_emargement(request, enseignant_id, month, type_contrat):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    if type_contrat == "Secondaire":
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
            
        time_total = format_time(total_salle_delta)
            
        enseignant = User.objects.get(id=enseignant_id)
            
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()      
        context = {
            "setting": setting,
            "emargements": tabEmargements,
            "enseignant": enseignant,
            "month": month,
            "time_total": time_total,
            "montant_payer": montant_payer,
            "anneeacademique": anneeacademique,
            "contrat": contrat,
            "type_contrat": type_contrat
        }
        return render(request, "ajax_detail_teacher_emargement.html", context)
    else:
        salles_emargements = (Emargement.objects.values("salle_id")
                              .filter(enseignant_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
                              .annotate(nb_salles=Count("salle_id"))
        )  
        
        tabEmargements = []
        total_salle_delta = timedelta(0)
        montant_payer = 0
        for se in salles_emargements:
            dic = {}
            salle_id = se["salle_id"]
            salle = Salle.objects.get(id=salle_id)
            dic["salle"] = salle  
             
            # Initialisation avec une durée nulle
            total_delta = timedelta(0)
            liste_emargements = []
            emargements = Emargement.objects.filter(enseignant_id=enseignant_id, salle_id=salle.id, month=month, anneeacademique_id=anneeacademique_id)        
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
                    liste_emargements.append(dic_emarg_enseignant_fondament)
            
            # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
            total_seconds = total_delta.total_seconds()
            total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
            total_minutes = int((total_seconds % 3600) // 60)

            # Afficher le résultat au format HH:MM
            formatted_time = f"{total_hours:02}:{total_minutes:02}"
                        
            dic["total_time"] = formatted_time                
            dic["emargements"] = liste_emargements  
                
            contrat = Contrat.objects.filter(user_id=enseignant_id, type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).first()
            cout_jour = contrat.amount/20 
            # Cout par heure
            moyenne = heure_par_jour_et_moyenne(enseignant_id, salle.id, anneeacademique_id)[1]
            cout_heure = 0
            if moyenne > 0:
                    cout_heure = float(cout_jour) / float(moyenne)
            # Coût par jour
            dic["cout_jour"] = cout_jour
            # Cout par heure
            dic["cout_heure"] = cout_heure
            # Nombre d'absences par mois de l'enseignant
            dic["nombre_absences"] = nombre_absence_enseignant(month, enseignant_id, salle.id, anneeacademique_id)
            # Montant brute à payer
            montant = salaire_enseignant_cycle_fondament_avec_absence(month, enseignant_id, salle.id, anneeacademique_id)
            dic["montant_payer"] =  montant 
            
            tabEmargements.append(dic)
            
            montant_payer += montant   
            total_salle_delta += total_delta
        
        time_total = format_time(total_salle_delta)
            
        enseignant = User.objects.get(id=enseignant_id)
            
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()      
        context = {
            "setting": setting,
            "emargements": tabEmargements,
            "enseignant": enseignant,
            "month": month,
            "time_total": time_total,
            "montant_payer": montant_payer,
            "anneeacademique": anneeacademique,
            "contrat": contrat,
            "type_contrat": type_contrat
        }
        return render(request, "ajax_detail_teacher_emargement.html", context)
    
@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)
def comptabilite_remuneration(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer les mois émargés
    months_emargements = (Emargement.objects.values("month")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nb_emargements=Count("month"))
    )
        
    months = []
    for me in months_emargements:
        months.append(me["month"])
    # Récuperer les mois rénumérés    
    months_renumerations = (Renumeration.objects.values("month")
                       .filter(type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
                       .annotate(nb_emargements=Count("month"))
    )
    for mr in months_renumerations:
        if mr["month"] not in months:
            months.append(mr["month"])
            
    tabcontrats = []
    nombre_tolal_personnels = 0 
    for type_contrat in {"Enseignant du cycle fondamental", "Enseignant du cycle secondaire", "Administrateur scolaire"}:       
        dic = {}
        # Nombre d'enseignants et d'administrateur
        nombre_personnels = Contrat.objects.filter(type_contrat=type_contrat, anneeacademique_id=anneeacademique_id).count()
        dic["type_contrat"] = type_contrat
        dic["nombre_personnels"] = nombre_personnels
        if type_contrat == "Enseignant du cycle fondamental":
            total_paiments = []
            total_paye = 0
            total_impaye = 0
            for month in months:
                dic_payment = {}
                nombre_personnels_a_paye = 0 
                nombre_personnels_paye = 0
                nombre_personnels_impaye = 0
                montant_paye = 0
                montant_impaye = 0
                contrats = Contrat.objects.filter(type_contrat=type_contrat, anneeacademique_id=anneeacademique_id)
                for contrat in contrats:
                    nombre_personnels_a_paye += 1
                    if month in month_contrat_user(contrat):
                        if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).exists():
                            montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                            nombre_personnels_paye += 1
                        else:
                            montant_impaye += float(contrat.amount)
                            nombre_personnels_impaye += 1
                dic_payment["nombre_personnels_a_paye"] = nombre_personnels_a_paye
                dic_payment["nombre_personnels_paye"] = nombre_personnels_paye
                dic_payment["nombre_personnels_impaye"] = nombre_personnels_impaye
                dic_payment["montant_paye"] = montant_paye
                dic_payment["montant_impaye"] = montant_impaye
                
                total_paiments.append(dic_payment)
                total_paye += montant_paye
                total_impaye += montant_impaye
                
            dic["total_paye"] = total_paye
            dic["total_impaye"] = total_impaye
            dic["resumes"] = total_paiments  
            
        elif type_contrat == "Enseignant du cycle secondaire":
            total_paiments = []
            total_paye = 0
            total_impaye = 0
            for month in months:
                dic_payment = {}
                nombre_personnels_a_paye = 0 
                nombre_personnels_paye = 0
                nombre_personnels_impaye = 0
                montant_paye = 0
                montant_impaye = 0
                contrats = Contrat.objects.filter(type_contrat=type_contrat, anneeacademique_id=anneeacademique_id)
                for contrat in contrats:
                    nombre_personnels_a_paye += 1
                    if Emargement.objects.filter(enseignant_id=contrat.user.id, month=month, anneeacademique_id=anneeacademique_id).exists():
                        if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).exists():
                            montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                            nombre_personnels_paye += 1
                        else:
                            montant_impaye += float(montant_total_emargement(contrat.user.id, month, anneeacademique_id))
                            nombre_personnels_impaye += 1
                dic_payment["nombre_personnels_a_paye"] = nombre_personnels_a_paye
                dic_payment["nombre_personnels_paye"] = nombre_personnels_paye
                dic_payment["nombre_personnels_impaye"] = nombre_personnels_impaye
                dic_payment["montant_paye"] = montant_paye
                dic_payment["montant_impaye"] = montant_impaye
                total_paiments.append(dic_payment)
                
                total_paye += montant_paye
                total_impaye += montant_impaye
            dic["total_paye"] = total_paye
            dic["total_impaye"] = total_impaye
            dic["resumes"] = total_paiments
        else:
            total_paiments = []
            total_paye = 0
            total_impaye = 0
            for month in months:
                dic_payment = {}
                nombre_personnels_a_paye = 0 
                nombre_personnels_paye = 0
                nombre_personnels_impaye = 0
                montant_paye = 0
                montant_impaye = 0
                contrats = Contrat.objects.filter(type_contrat=type_contrat, anneeacademique_id=anneeacademique_id)
                for contrat in contrats:
                    nombre_personnels_a_paye += 1
                    if month in month_contrat_user(contrat):
                        if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).exists():
                            montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration=type_contrat, month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                            nombre_personnels_paye += 1
                        else:
                            montant_impaye += float(contrat.amount)
                            nombre_personnels_impaye += 1
                dic_payment["nombre_personnels_a_paye"] = nombre_personnels_a_paye
                dic_payment["nombre_personnels_paye"] = nombre_personnels_paye
                dic_payment["nombre_personnels_impaye"] = nombre_personnels_impaye
                dic_payment["montant_paye"] = montant_paye
                dic_payment["montant_impaye"] = montant_impaye
                
                total_paiments.append(dic_payment)
                total_paye += montant_paye
                total_impaye += montant_impaye
                
            dic["total_paye"] = total_paye
            dic["total_impaye"] = total_impaye
            dic["resumes"] = total_paiments
            
        tabcontrats.append(dic)
        nombre_tolal_personnels += nombre_personnels  
        
    # Somme totale par mois de toutes les salles 
    total_paye_impaye = [] 
    total_paye = 0
    total_impaye = 0 
    total_personnel = 0
    for month in months:   
        dic = {} 
        montant_paye = 0 
        montant_impaye = 0
        nombre_personnels_a_paye = 0
        nombre_personnels_paye = 0  
        nombre_personnels_impaye = 0 
        contrats_enseignants_cycle_secondaire = Contrat.objects.filter(type_contrat="Enseignant du cycle secondaire", anneeacademique_id=anneeacademique_id)
        total_personnel += contrats_enseignants_cycle_secondaire.count()
        for contrat in contrats_enseignants_cycle_secondaire:
            nombre_personnels_a_paye += 1
            if Emargement.objects.filter(enseignant_id=contrat.user.id, month=month, anneeacademique_id=anneeacademique_id).exists():
                if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Enseignant du cycle secondaire", month=month, anneeacademique_id=anneeacademique_id).exists():
                    montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Enseignant du cycle secondaire", month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                    nombre_personnels_paye += 1
                else:
                    montant_impaye += float(montant_total_emargement(contrat.user.id, month, anneeacademique_id))
                    nombre_personnels_impaye += 1
                            
        contrats_enseignants_cycle_fondamental = Contrat.objects.filter(type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id)
        total_personnel += contrats_enseignants_cycle_fondamental.count()
        for contrat in contrats_enseignants_cycle_fondamental:
            nombre_personnels_a_paye += 1
            if month in month_contrat_user(contrat):
                if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Enseignant du cycle fondamental", month=month, anneeacademique_id=anneeacademique_id).exists():
                    montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Enseignant du cycle fondamental", month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                    nombre_personnels_paye += 1
                else:
                    montant_impaye += float(contrat.amount)
                    nombre_personnels_impaye += 1
                            
        contrats_administrateurs = Contrat.objects.filter(type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
        total_personnel += contrats_administrateurs.count()
        for contrat in contrats_administrateurs:
            nombre_personnels_a_paye += 1
            if month in month_contrat_user(contrat):
                if Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Administrateur scolaire", month=month, anneeacademique_id=anneeacademique_id).exists():
                    montant_paye += float(Renumeration.objects.filter(user_id=contrat.user.id, type_renumeration="Administrateur scolaire", month=month, anneeacademique_id=anneeacademique_id).first().total_amount)
                    nombre_personnels_paye += 1
                else:
                    montant_impaye += float(contrat.amount)
                    nombre_personnels_impaye += 1
                    
        dic["montant_paye"] = montant_paye
        dic["montant_impaye"] = montant_impaye
        dic["nombre_personnels_paye"] = nombre_personnels_paye
        dic["nombre_personnels_impaye"] = nombre_personnels_impaye
        
        total_paye_impaye.append(dic)
        total_paye += montant_paye
        total_impaye += montant_impaye
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)       
    context = {
        "setting": setting,
        "months": months,
        "contrats": tabcontrats,
        "total_payments": total_paiments,
        "total_paye_impaye": total_paye_impaye,
        "total_paye": total_paye,
        "total_impaye": total_impaye,
        "total_personnel": total_personnel,
        "anneeacademique": anneeacademique
    }
    
    return render(request, "comptabilite_remuneration.html", context)

# Verifier si le mois renseignant fait parti des mois du contrat
def validite_contrat(user_id, month, anneeacademique_id):
    contrats = Contrat.objects.filter(user_id=user_id, anneeacademique_id=anneeacademique_id).order_by("id")
    status = False
    for contrat in contrats:
        months = month_contrat_user(contrat) # Récuperer tous les mois de ce contrat
        if month in months: # Verifier si ce mois fait parti des mois de ce contrat
            status = True
    return status

# Méthode determinant le montant total d'émargement de l'enseignant
def montant_total_emargement(enseignant_id, month, anneeacademique_id):
    
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
        
        matieres_emargements = (Emargement.objects.values("matiere_id")
                   .filter(enseignant_id=enseignant_id, salle_id=salle_id, month=month, anneeacademique_id=anneeacademique_id)
                   .annotate(nb_emargements=Count("matiere_id")))
        
        matieres = []
        total_matiere_delta = timedelta(0)
        for me in matieres_emargements:
            if me["matiere_id"]:
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
    
    return montant_payer

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)
def ajax_comptabilite_remuneration(request, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    renumerations_enseignants_fondamental = Renumeration.objects.filter(month=month,type_renumeration="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id)
    tabRenumerationsEnseignantsFondamental= []
    somme_totale_enseignant_fondamental = 0
    for renumeration in renumerations_enseignants_fondamental:
        dic = {}
        dic["renumeration"] = renumeration
        dic["net_payer"] = float(renumeration.amount) + float(renumeration.indemnite)   
        tabRenumerationsEnseignantsFondamental.append(dic)
        
        somme_totale_enseignant_fondamental += float(renumeration.amount) + float(renumeration.indemnite)
        
    renumerations_enseignants_secondaire = Renumeration.objects.filter(month=month,type_renumeration="Enseignant du cycle secondaire", anneeacademique_id=anneeacademique_id)
    tabRenumerationsEnseignantsSecondaire= []
    somme_totale_enseignant_secondaire = 0
    for renumeration in renumerations_enseignants_secondaire:
        dic = {}
        dic["renumeration"] = renumeration
        dic["net_payer"] = float(renumeration.amount) + float(renumeration.indemnite)   
        tabRenumerationsEnseignantsSecondaire.append(dic)
        
        somme_totale_enseignant_secondaire += float(renumeration.amount) + float(renumeration.indemnite)
        
    renumerations_admin = Renumeration.objects.filter(month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
    tabRenumerations_admin= []
    somme_totale_admin = 0
    for renumeration in renumerations_admin:
        dic = {}
        dic["renumeration"] = renumeration
        dic["net_payer"] = float(renumeration.amount) + float(renumeration.indemnite)   
        tabRenumerations_admin.append(dic)
        
        somme_totale_admin += float(renumeration.amount) + float(renumeration.indemnite)
    
    total = somme_totale_enseignant_fondamental + somme_totale_enseignant_secondaire + somme_totale_admin    
    context = {
        "month": month,
        "renumerations_enseignants_fondamental": tabRenumerationsEnseignantsFondamental,
        "renumerations_enseignants_secondaire": tabRenumerationsEnseignantsSecondaire,
        "somme_totale_enseignant_fondamental": somme_totale_enseignant_fondamental,
        "somme_totale_enseignant_secondaire": somme_totale_enseignant_secondaire,
        "renumerations_admin": tabRenumerations_admin,
        "sum_total_admin" : somme_totale_admin,
        "total": total,
        "setting": setting
    }       
    return render(request, "ajax_comptabilite_remuneration.html", context)

# Formatter le temps  
def format_time(time):
    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
    total_matiere_seconds = time.total_seconds()
    total_matiere_hours = int(total_matiere_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
    total_matiere_minutes = int((total_matiere_seconds % 3600) // 60)

    # Afficher le résultat au format HH:MM
    formatted_time = f"{total_matiere_hours:02}:{total_matiere_minutes:02}"   
    return formatted_time

# Calculer le salaire
def calculer_montant(cout_heure, heure_totale):
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

# Calculer de l'enseignant le montant à payer 
def montant_payer(anneeacademique_id, enseignant_id, month, type_contrat):
    
    if type_contrat == "Secondaire":
    
        salles_emargements = (Emargement.objects.values("salle_id")
                    .filter(enseignant_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
                    .annotate(nb_emargements=Count("salle_id")))
        
        tabEmargements = []
        total_salle_delta = timedelta(0)
        montant_payer = 0
        for se in salles_emargements:
            dic = {}
            salle_id = se["salle_id"]
            salle = Salle.objects.get(id=salle_id)
            dic["salle"] = salle
            
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
                enseignement = Enseigner.objects.filter(enseignant_id=enseignant_id, salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id).first()
                dic_matiere["cout_heure"] = enseignement.cout_heure
                
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
            
            montant_total = calculer_montant(enseignement.cout_heure, format_time(total_matiere_delta))
            dic["montant_total_salle"] = montant_total
            tabEmargements.append(dic)
            total_salle_delta += total_matiere_delta
            
            montant_payer += montant_total
            
        time_total = format_time(total_salle_delta)
        
        return time_total, montant_payer
    else:
        salles_emargements = (Emargement.objects.values("salle_id")
                              .filter(enseignant_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
                              .annotate(nb_salles=Count("salle_id"))
        )  
        
        tabEmargements = []
        total_salle_delta = timedelta(0)
        montant_payer = 0
        for se in salles_emargements:
            dic = {}
            salle_id = se["salle_id"]
            salle = Salle.objects.get(id=salle_id)
            dic["salle"] = salle  
             
            # Initialisation avec une durée nulle
            total_delta = timedelta(0)
            liste_emargements = []
            emargements = Emargement.objects.filter(enseignant_id=enseignant_id, salle_id=salle.id, month=month, anneeacademique_id=anneeacademique_id)        
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
                    liste_emargements.append(dic_emarg_enseignant_fondament)
            
            # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
            total_seconds = total_delta.total_seconds()
            total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
            total_minutes = int((total_seconds % 3600) // 60)

            # Afficher le résultat au format HH:MM
            formatted_time = f"{total_hours:02}:{total_minutes:02}"
                        
            dic["total_time"] = formatted_time                
            dic["emargements"] = liste_emargements  
                
            contrat = Contrat.objects.filter(user_id=enseignant_id, type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).first()
            cout_jour = contrat.amount/20 
            # Cout par heure
            moyenne = heure_par_jour_et_moyenne(enseignant_id, salle.id, anneeacademique_id)[1]
            cout_heure = 0
            if moyenne > 0:
                    cout_heure = float(cout_jour) / float(moyenne)
            # Coût par jour
            dic["cout_jour"] = cout_jour
            # Cout par heure
            dic["cout_heure"] = cout_heure
            # Nombre d'absences par mois de l'enseignant
            dic["nombre_absences"] = nombre_absence_enseignant(month, enseignant_id, salle.id, anneeacademique_id)
            # Montant brute à payer
            montant = salaire_enseignant_cycle_fondament_avec_absence(month, enseignant_id, salle.id, anneeacademique_id)
            dic["montant_payer"] =  montant 
            
            tabEmargements.append(dic)
            
            montant_payer += montant   
            total_salle_delta += total_delta
            
        time_total = format_time(total_salle_delta)
        
        return time_total, montant_payer    
            
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_remun_teacher(request, enseignant_id, month, type_contrat):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    en_id = int(dechiffrer_param(str(enseignant_id)))
    month_cry = dechiffrer_param(month)
    type_cont = dechiffrer_param(type_contrat)
    
    enseignant = User.objects.get(id=en_id)
    total_time, mont_payer = montant_payer(anneeacademique_id, en_id, month_cry, type_cont)
    
    mode_payments = ["Espèce", "Virement", "Mobile"]
    context = {
        "setting": setting,
        "enseignant": enseignant,
        "month": month_cry,
        "montant": mont_payer,
        "total_time": total_time,
        "mode_payments": mode_payments,
        "type_contrat": type_cont
    }
    return render(request, "remun_enseignant/add_remun_teacher.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_renum(request):
    user_id = request.user.id
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        enseignant_id = int(request.POST["enseignant"])
        month = request.POST["month"]
        amount = bleach.clean(request.POST["amount"].strip())
        indemnite = bleach.clean(request.POST["indemnite"].strip())
        mode_payment = bleach.clean(request.POST["mode_payment"].strip())
        password = bleach.clean(request.POST["password"].strip())
        
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = float(amount.replace(',', '.'))
        
        indemnite = re.sub(r'\xa0', '', indemnite)  # Supprime les espaces insécables
        indemnite = float(indemnite.replace(',', '.'))
        
        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
            
        try:
            indemnite = Decimal(indemnite)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "L'indemnité doit être un nombre valide."})
        
        reste = (somme_totale_caisse(anneeacademique_id) + float(indemnite)) - float(amount)
        
        query = Renumeration.objects.filter(user_id=enseignant_id, month=month, anneeacademique_id=anneeacademique_id)
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
        user = User.objects.get(id=user_id)
        if user.check_password(password) == False:
            return JsonResponse({
                "status": "error",
                "message": "Mot de passe incorrect."})
        if reste < 0:
            return JsonResponse({
                    "status": "error",
                    "message": "Le solde de la caisse est insufisant."}) 
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."}) 
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette rémunération existe déjà."})
        else:
            amount_total = float(amount) + float(indemnite)
            renumeration = Renumeration(
                anneeacademique_id=anneeacademique_id,
                user_id=enseignant_id,
                month=month,
                amount=amount,
                indemnite=indemnite,
                total_amount=amount_total,
                mode_payment=mode_payment,
                type_renumeration="Enseignant du cycle secondaire",
                responsable_id=user_id 
            )
            count0 = Renumeration.objects.all().count()
            renumeration.save()
            count1 = Renumeration.objects.all().count()
            # Verifier si l'ajout a été bien effectué ou pas
            if count0 < count1:
                return JsonResponse({
                        "status": "success",
                        "message": "Rénumération effectuée avec succès."})
            else:   
                return JsonResponse({
                        "status": "error",
                        "message": "L'opérations a échouée."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_remun_teacher(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    renumeration_id = int(dechiffrer_param(str(id)))
    renumeration = Renumeration.objects.get(id=renumeration_id)
    # Répuerer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)  
    #Récuperer les utilisateurs qui ont signé un contrat
    users_contrats = (Contrat.objects.values("user_id")
                      .filter(anneeacademique_id=anneeacademique_id)
                      .annotate(nb_contrats=Count("user_id")))
    
    users = []
    for uc in users_contrats:
        user = User.objects.get(id=uc["user_id"])
        if user.id != renumeration.user.id:
            # Recuperer les groupes de l'utilisateurs
            groups = etablissement.groups.filter(user=user)
            for group in groups:
                if group.name in permission_admin:
                    users.append(user)
                    break
        
    tab_months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mode_payments = ["Espèce", "Virement", "Mobile"]
    tab_mode_payment = []
    for mode_payment in mode_payments:
        if renumeration.mode_payment != mode_payment:
            tab_mode_payment.append(mode_payment)
            
    months = []
    for month in tab_months:
        if month != renumeration.month:
            months.append(month)
    context = {
        "setting": setting,
        "renumeration": renumeration,
        "users": users,
        "months": months,
        "mode_payments": mode_payments
    }
    return render(request, "remun_enseignant/edit_remun_teacher.html", context)
   

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_re(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            renumeration = Renumeration.objects.get(id=id)
        except:
            renumeration = None

        if renumeration is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            user_id = request.POST["user"]
            month = request.POST["month"]
            amount = bleach.clean(request.POST["amount"].strip())
            indemnite = bleach.clean(request.POST["indemnite"].strip())
            mode_payment = bleach.clean(request.POST["mode_payment"].strip())
            password = bleach.clean(request.POST["password"].strip())
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)    
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")
            
            indemnite = re.sub(r'\xa0', '', indemnite)  # Supprime les espaces insécables
            indemnite = indemnite.replace(" ", "").replace(",", ".")

            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
                
            try:
                indemnite = Decimal(indemnite)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "L'indemnité doit être un nombre valide."})
                
            reste = (somme_totale_caisse(anneeacademique_id) + float(indemnite)) - float(amount)            
            # Vérifier l'existence de la rénumeration
            renumerations = Renumeration.objects.filter(month=month, user_id=user_id, type_renumeration__in="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabRenumeration = []
            for r in renumerations:   
                dic = {}
                dic["user_id"] = r.user.id
                dic["month"] = r.month
                dic["anneeacademique_id"] = r.anneeacademique.id
                tabRenumeration.append(dic)            
                
            new_dic = {}
            new_dic["user_id"] = int(user_id)
            new_dic["month"] = month
            new_dic["anneeacademique_id"] = int(anneeacademique_id)
            user = User.objects.get(id=request.user.id)
            if user.check_password(password) == False:
                return JsonResponse({
                    "status": "error",
                    "message": "Mot de passe incorrect."})
            if reste < 0: # Verifier la recette 
                return JsonResponse({
                    "status": "error",
                    "message": "Le solde de la caisse est insufisant."}) 
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})            
            if new_dic in tabRenumeration: # Vérifier l'existence de la rénumeration
                return JsonResponse({
                    "status": "error",
                    "message": "Cette rénumeration existe déjà."})
            else:
                amount_total = float(amount) + float(indemnite)
                renumeration.user_id = user_id
                renumeration.month = month
                renumeration.amount = amount
                renumeration.indemnite = indemnite
                renumeration.total_amount = amount_total
                renumeration.mode_payment = mode_payment
                renumeration.save()
                
                return JsonResponse({
                    "status": "success",
                    "message": "Rénumeration modifiée avec succès."})  
                
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_renum(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    renumeration_id = int(dechiffrer_param(str(id)))
    
    renumeration = Renumeration.objects.get(id=renumeration_id)
    # Nombre de contrats avant la suppression
    count0 = Renumeration.objects.all().count()
    renumeration.delete()
    # Nombre de contrats après la suppression
    count1 = Renumeration.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Elément supprimé avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("remun_enseignant/remunerations_enseignants")

def ajax_delete_renum(request, id):
    renumeration = Renumeration.objects.get(id=id)
    context = {
        "renumeration": renumeration
    }
    return render(request, "ajax_delete_renum.html", context) 

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_gestionnaire)
def resume_remu_enseignant_fondamental(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Determiner tous les mois de l'année académique 
    months = periode_annee_scolaire(anneeacademique_id)
        
    emargements = []
    for month in months:   

        dic = {}
        dic["month"] = month
        # Récuperer les contrats des enseignants du cycle fondamental
        contrats = Contrat.objects.filter(type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id)

        nombre_enseignants_impayes = 0
        enseignants = []
        for contrat in contrats:
            # Determiner les mois du contrat de l'utilisateur
            months_contrat = month_contrat_user(contrat)
            if month in months_contrat:
                if not Renumeration.objects.filter(user_id=contrat.user.id, anneeacademique_id=anneeacademique_id, type_renumeration="Enseignant du cycle fondamental").exists():
                    nombre_enseignants_impayes += 1
                    enseignants.append(contrat.user)
                
        dic["nombre_enseignants_impayes"] = nombre_enseignants_impayes 
        dic["enseignants"] = enseignants
        
        emargements.append(dic)  
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()        
    context = {
        "setting": setting,
        "emargements": emargements,
        "anneeacademique": anneeacademique,
        "contrat": contrat
    }
    return render(request, "remun_enseignant/resume_remu_enseignant_fondamental.html", context)            

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def mes_renumerations(request):
    user_id = request.user.id
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    renumerations = Renumeration.objects.filter(user_id=user_id, anneeacademique_id=anneeacademique_id)
    
    tabrenumerations = []
    for renumeration in renumerations:
        dic_renum = {}
        dic_renum["renumeration"] = renumeration
        salles_emargements = (Emargement.objects.values("salle_id")
                    .filter(enseignant_id=user_id, month=renumeration.month, anneeacademique_id=anneeacademique_id)
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
            
            matieres_emargements = (Emargement.objects.values("matiere_id")
                    .filter(enseignant_id=user_id, salle_id=salle_id, month=renumeration.month, anneeacademique_id=anneeacademique_id)
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
                    enseignant_id=user_id, 
                    salle_id=salle_id, 
                    matiere_id=matiere_id, 
                    anneeacademique_id=anneeacademique_id).first()
                dic_matiere["cout_heure"] = enseignement.cout_heure
                
                somme_cout_heure += enseignement.cout_heure
                
                emargements = Emargement.objects.filter(enseignant_id=user_id, month=renumeration.month, salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id)
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
            
            montant_total 
            
            tabEmargements.append(dic)
            
            total_salle_delta += total_matiere_delta
            
            montant_payer += montant_total
            
        dic_renum["emargements"] = tabEmargements
        dic_renum["time_total"] = format_time(total_salle_delta)
        dic_renum["montant_total"] = montant_payer
        dic_renum["net_payer"] = float(renumeration.amount) + float(renumeration.indemnite) 
        
        tabrenumerations.append(dic_renum)
        
        # Mise à jour du status de paiement de l'enseignant pour marquer la lecture
        renumeration.status = True
        renumeration.save()
       
    context = {
        "renumerations": tabrenumerations,
        "setting": setting
    }       
    return render(request, "mes_renumerations.html", context)     
        
#================== Gestion de contrats =================================
def status_contrat(contrat):
    # Date actuelle
    date_actuelle = date.today()
    status = "En attente"
    if contrat:
        if date_actuelle < contrat.date_debut:
            status = "En attente"
        elif contrat.date_debut <= date_actuelle and  date_actuelle <= contrat.date_fin:
            status = "En cours"
        if contrat.date_fin < date_actuelle:
            status = "Terminé"
    return status

# Statut du contrat
def status_contrat_user(user_id, anneeacademique_id):
    contrat = Contrat.objects.filter(user_id=user_id, anneeacademique_id=anneeacademique_id).order_by("-id").first()
    return status_contrat(contrat)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def contrats(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
        contrats_users = (Contrat.objects.values("user_id")
                        .filter(type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
                        .annotate(nb_contrats=Count("user_id"))
        )
        tabcontrats = []
        for cu in contrats_users:
            user = User.objects.get(id=cu["user_id"])   
            dic = {}
            dic["user"] = user
            liste_contrats = Contrat.objects.filter(user_id=user.id, anneeacademique_id=anneeacademique_id).order_by("-date_fin")
            contrats = []
            for contrat in liste_contrats:
                new_dic = {}
                new_dic["contrat"] = contrat
                new_dic["status"] = status_contrat(contrat)
                contrats.append(new_dic)
                
            dic["contrats"] = contrats
            dic["nb_contrats"] = cu["nb_contrats"]
            # Récuperer le dernier contrat de l'utilisateur pour determiner son statut
            dernier_contrat = Contrat.objects.filter(user_id=user.id, anneeacademique_id=anneeacademique_id).order_by("-date_fin").first()
            dic["status"] = status_contrat(dernier_contrat)
            tabcontrats.append(dic)

        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique)
        context = {
            "setting": setting,
            "contrats": tabcontrats,
            "anneeacademique": anneeacademique,
            "contrat": contrat
        }
        return render(request, "contrat/contrats.html", context) 
    else:
        contrats_users = (Contrat.objects.values("user_id")
                      .filter(type_contrat__in=["Enseignant du cycle fondamental", "Enseignant du cycle secondaire"], anneeacademique_id=anneeacademique_id)
                      .annotate(nb_contrats=Count("user_id"))
        )
        tabcontrats = []
        for cu in contrats_users:
            user = User.objects.get(id=cu["user_id"])   
            dic = {}
            dic["user"] = user
            liste_contrats = Contrat.objects.filter(user_id=user.id, anneeacademique_id=anneeacademique_id).order_by("-date_fin")
            contrats = []
            for contrat in liste_contrats:
                new_dic = {}
                new_dic["contrat"] = contrat
                new_dic["status"] = status_contrat(contrat)
                contrats.append(new_dic)
                
            dic["contrats"] = contrats
            dic["nb_contrats"] = cu["nb_contrats"]
            # Récuperer le dernier contrat de l'utilisateur pour determiner son statut
            dernier_contrat = Contrat.objects.filter(user_id=user.id, anneeacademique_id=anneeacademique_id).order_by("-date_fin").first()
            dic["status"] = status_contrat(dernier_contrat)
            tabcontrats.append(dic)

        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        context = {
            "setting": setting,
            "contrats": tabcontrats,
            "anneeacademique": anneeacademique
        }
        return render(request, "contrat/contrats.html", context)   

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_Promoteur_DG_DE)
@transaction.atomic
def add_contrat(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'année académique 
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    if request.method == "POST":

        user_id = request.POST["user"]
        type_contrat = request.POST["type_contrat"]
        poste = bleach.clean(request.POST["poste"].strip())
        description = bleach.clean(request.POST["description"].strip())
        date_debut = request.POST["date_debut"]
        date_fin = request.POST["date_fin"]
        amount = bleach.clean(request.POST["amount"].strip())
        
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)          
        query = Contrat.objects.filter(user_id=user_id, date_debut=date_debut, date_fin=date_fin, type_contrat=type_contrat, anneeacademique_id=anneeacademique_id)
        # Récuperer le dernier contrat de cette année scolaire de l'utilisateur pour verifier si la date de fin du dernier est inférieure à la date de debut du nouveau contrata
        dernier_contrat = Contrat.objects.filter(user_id=user_id, type_contrat=type_contrat, anneeacademique_id=anneeacademique_id).order_by("-id").first() 
        if anneeacademique.start_date <= datetime.strptime(date_debut, "%Y-%m-%d").date() and datetime.strptime(date_fin, "%Y-%m-%d").date() <= anneeacademique.end_date:
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont été déjà clôturées."})  
            if dernier_contrat: # Récuperer le statut du dernier contrat s'il existe pour vérifier s'il est déjà terminé pour enregistrer un nouveau
                status_contrat = status_contrat_user(user_id, anneeacademique_id)
                if status_contrat not in ["Terminé"]:
                    return JsonResponse({
                        "status": "error",
                        "message": "Le dernier contrat de cet utilisateur doit d'abord terminer pour enrgistrer un nouveau contrat."})
                if dernier_contrat.date_fin > datetime.strptime(date_debut, "%Y-%m-%d").date(): # Conversion de la date début (str) en date
                    return JsonResponse({
                        "status": "error",
                        "message": "La date de fin du dernier contrat de cet utilisateur doit être inférieure à la date de début du nouvaeu contrat."})
                if date_debut > date_fin:
                    return JsonResponse({
                        "status": "error",
                        "message": "La date du début doit être inférieure ou égale à la date de fin."})
                if query.exists():
                    return JsonResponse({
                            "status": "error",
                            "message": "Ce contrat existe déjà."})
                else:
                    contrat = Contrat(
                        user_id=user_id, 
                        type_contrat=type_contrat, 
                        poste=poste,
                        description=description,
                        date_debut=date_debut,
                        date_fin=date_fin, 
                        amount=amount,
                        anneeacademique_id=anneeacademique_id,
                        admin_id=request.user.id)
                    # Nombre de contrats avant l'ajout
                    count0 = Contrat.objects.all().count()
                    contrat.save()
                    # Nombre de contrats après l'ajout
                    count1 = Contrat.objects.all().count()
                    # On verifie si l'insertion a eu lieu ou pas.
                    if count0 < count1:
                        return JsonResponse({
                                "status": "success",
                                "message": "Contrat et la signature enregistrés avec succès."})
                    else:
                        return JsonResponse({
                                "status": "error",
                                "message": "Insertion a échouée."})
            else:
                if date_debut > date_fin:
                    return JsonResponse({
                        "status": "error",
                        "message": "La date du début doit être inférieure ou égale à la date de fin."})
                if query.exists():
                    return JsonResponse({
                            "status": "error",
                            "message": "Ce contrat existe déjà."})
                else:
                    contrat = Contrat(
                        user_id=user_id, 
                        type_contrat=type_contrat, 
                        poste=poste,
                        description=description,
                        date_debut=date_debut,
                        date_fin=date_fin, 
                        amount=amount,
                        anneeacademique_id=anneeacademique_id,
                        admin_id=request.user.id)
                    # Nombre de contrats avant l'ajout
                    count0 = Contrat.objects.all().count()
                    contrat.save()
                    # Nombre de contrats après l'ajout
                    count1 = Contrat.objects.all().count()
                    # On verifie si l'insertion a eu lieu ou pas.
                    if count0 < count1:
                        return JsonResponse({
                                "status": "success",
                                "message": "Contrat enregistré avec succès."})
                    else:
                        return JsonResponse({
                                "status": "error",
                                "message": "Insertion a échouée."})
        else:
            return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin du contrat doivent situer entre la date du début et de fin de l'année académique."})         
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    if request.session.get('group_name') in ["Promoteur", "Directeur Général"]:
        users = []
        for role in EtablissementUser.objects.filter(etablissement=etablissement):
            if role.user not in users and role.group.name in ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Surveillant Général"]:
                users.append(role.user)
                
        types_contrat = ['Administrateur scolaire'] 
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
        context = {
            "setting": setting,
            "users": users,
            "types_contrat": types_contrat,
            "contrat": contrat
        }
        return render(request, "contrat/add_contrat.html", context)
    else:
        users = []
        for role in EtablissementUser.objects.filter(etablissement=etablissement):
            if role.user not in users and role.group.name == "Enseignant":
                users.append(role.user)
                
        types_contrat = ['Enseignant du cycle fondamental', 'Enseignant du cycle secondaire'] 
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
        context = {
            "setting": setting,
            "users": users,
            "types_contrat": types_contrat,
            "contrat": contrat
        }
        return render(request, "contrat/add_contrat.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_Promoteur_DG_DE)
def edit_contrat(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    contrat_id = int(dechiffrer_param(str(id)))
    contrat = Contrat.objects.get(id=contrat_id)
    # Récuperer l'année academique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    if request.session.get('group_name') in ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire", "Surveillant Général"]:
        users = []
        for role in EtablissementUser.objects.filter(etablissement=etablissement):
            if role.user !=contrat.user and role.user not in users:
                users.append(role.user)
        
        types_contrat = ['Administrateur scolaire']   
        tab_types_contrat = []
        for type_contrat in types_contrat:
            if contrat.type_contrat != type_contrat:
                tab_types_contrat.append(type_contrat)
        
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()        
        context = {
            "setting": setting,
            "users": users,
            "contrat": contrat,
            "types_contrat": tab_types_contrat,
            "contrat": contrat
        }
        return render(request, "contrat/edit_contrat.html", context)
    else:
        users = []
        for role in EtablissementUser.objects.filter(etablissement=etablissement):
            if role.user !=contrat.user and role.user not in users and role.group.name == "Enseignant":
                users.append(role.user)
        
        types_contrat = ['Enseignant du cycle fondamental', 'Enseignant du cycle secondaire']   
        tab_types_contrat = []
        for type_contrat in types_contrat:
            if contrat.type_contrat != type_contrat:
                tab_types_contrat.append(type_contrat)
       
        contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()         
        context = {
            "setting": setting,
            "users": users,
            "contrat": contrat,
            "types_contrat": tab_types_contrat,
            "contrat": contrat
        }
        return render(request, "contrat/edit_contrat.html", context)
   

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_ct(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            contrat = Contrat.objects.get(id=id)
        except:
            contrat = None

        if contrat is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            user_id = request.POST["user"]
            type_contrat = request.POST["type_contrat"]
            poste = bleach.clean(request.POST["poste"].strip())
            description = bleach.clean(request.POST["description"].strip())
            date_debut = request.POST["date_debut"]
            date_fin = request.POST["date_fin"]
            amount = bleach.clean(request.POST["amount"].strip())
            
             # Récuperer l'année académique
            anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
            if anneeacademique.start_date <= datetime.strptime(date_debut, "%Y-%m-%d").date() and datetime.strptime(date_fin, "%Y-%m-%d").date() <= anneeacademique.end_date:
                # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
                anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
                # Recuperer tous contrats existants pour verifier s'il existe déjà un contrat à ces dates
                contrats = Contrat.objects.filter(user_id=user_id).exclude(id=id)
                status_date = False # Indique s'il existe déjà un contrat avec la date renseignée
                for contrat in contrats:
                    date_d = datetime.strptime(date_debut, "%Y-%m-%d").date() # Conversion de la date début (str) en date  
                    date_f = datetime.strptime(date_fin, "%Y-%m-%d").date() # Conversion de la date fin (str) en date  
                    if (contrat.date_debut <= date_d and date_d <= contrat.date_fin) or (contrat.date_debut <= date_f and date_f <= contrat.date_fin):
                        status_date = True
                        break           
                
                # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
                amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
                amount = amount.replace(" ", "").replace(",", ".")

                try:
                    amount = Decimal(amount)  # Convertir en Decimal
                except:
                    return JsonResponse({
                        "status": "error",
                        "message": "Le montant doit être un nombre valide."})
                # Vérifier l'existence du contrat
                contrats = Contrat.objects.filter(date_debut=date_debut, date_fin=date_fin, user_id=user_id, type_contrat=type_contrat, anneeacademique_id=anneeacademique_id).exclude(id=id)
                tabContrat = []
                for c in contrats:   
                    dic = {}
                    dic["user_id"] = c.user.id
                    dic["date_debut"] = c.date_debut
                    dic["date_fin"] = c.date_fin
                    dic["anneeacademique_id"] = c.anneeacademique.id
                    tabContrat.append(dic)            
                    
                new_dic = {}
                new_dic["user_id"] = int(user_id)
                new_dic["date_debut"] = date_debut
                new_dic["date_fin"] = date_fin
                new_dic["anneeacademique_id"] = int(anneeacademique_id)
                if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont été déjà clôturées."})  
                if status_date :
                    return JsonResponse({
                        "status": "error",
                        "message": "Un autre contrat existe déjà avec les dates renseignées."})
                if new_dic in tabContrat: # Vérifier l'existence du programme
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce contrat existe déjà."})
                if date_debut > date_fin:
                    return JsonResponse({
                        "status": "error",
                        "message": "La date du début doit être inférieure ou égale à la date de fin."})
                else:
                    contrat.user_id = user_id
                    contrat.type_contrat = type_contrat
                    contrat.poste = poste
                    contrat.description = description
                    contrat.date_debut = date_debut
                    contrat.date_fin = date_fin
                    contrat.amount = amount
                    contrat.admin_id=request.user.id
                    contrat.save()
                    
                    return JsonResponse({
                        "status": "success",
                        "message": "Contrat modifié avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin du contrat doivent situer entre la date du début et de fin de l'année académique."})         


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_contrat(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    contrat_id = int(dechiffrer_param(str(id)))
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    if contrat:
        contrat = Contrat.objects.get(id=contrat_id)
        # Nombre de contrats avant la suppression
        count0 = Contrat.objects.all().count()
        contrat.delete()
        # Nombre de contrats après la suppression
        count1 = Contrat.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        return redirect("contrat/contrats")
    else:
        messages.error(request, "Veuillez signer votre contrat avant de procéder à la suppression d’un contrat.")
        return redirect("contrat/contrats")

def ajax_type_contrat(request, type_contrat):
    anneeacademique_id = request.session.get('anneeacademique_id')
    context = {
        "type_contrat": type_contrat,
        "setting": get_setting(anneeacademique_id)
    }
    return render(request, "ajax_type_contrat.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_users)
def contrats_user(request):
    user_id = request.user.id
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    contrats = Contrat.objects.filter(user_id=user_id, anneeacademique_id=anneeacademique_id).order_by("-date_fin")
    tabcontrats = []
    for contrat in contrats:  
        dic = {}
        dic["contrat"] = contrat
        dic["status"] = status_contrat(contrat)
        tabcontrats.append(dic)

    context = {
        "setting": setting,
        "contrats": tabcontrats
    }
    return render(request, "contrat/contrats_user.html", context) 

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_users)
def signer_contrat(request, contrat_id):
    contrat = Contrat.objects.get(id=contrat_id)
    contrat.status_signature = True
    contrat.date_signature = date.today()
    contrat.save()
    
    context = {
        "contrat": contrat
    }
    return render(request, "signer_contrat.html", context)

def ajax_delete_contrat(request, id):
    contrat = Contrat.objects.get(id=id)
    context = {
        "contrat": contrat
    }
    return render(request, "ajax_delete_contrat.html", context)


#================== Gestion de rénumeration =================================

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def renum_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    renumerations_users = (
        Renumeration.objects
        .values("user_id")
        .filter(
            anneeacademique_id=anneeacademique_id,
            type_renumeration="Administrateur scolaire"
        )
        .annotate(nb_renumerations=Count("user_id"))
    )
    
    tabrenumerations = []
    for ru in renumerations_users:
        user = User.objects.get(id=ru["user_id"])   
        dic = {}
        dic["user"] = user
        dic["renumerations"] = Renumeration.objects.filter(user_id=user.id, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
        dic["nb_renumerations"] = ru["nb_renumerations"]
        tabrenumerations.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "renumerations": tabrenumerations,
        "anneeacademique": anneeacademique
    }
    return render(request, "renum/renum_admin.html", context)    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
@transaction.atomic
def add_renum_admin(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    if request.method == "POST":
        user_id = request.POST["user"]
        month = request.POST["month"]
        amount = bleach.clean(request.POST["amount"].strip())
        indemnite = bleach.clean(request.POST["indemnite"].strip())
        mode_payment = bleach.clean(request.POST["mode_payment"].strip())
        password = bleach.clean(request.POST["password"].strip())
        
        type_renum = request.POST.get("type_renumeration")
        if type_renum is None:
            type_renum = "Administrateur scolaire"
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)     
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")
        
        indemnite = re.sub(r'\xa0', '', indemnite)  # Supprime les espaces insécables
        indemnite = indemnite.replace(" ", "").replace(",", ".")
        
        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
            
        try:
            indemnite = Decimal(indemnite)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "L'indemnité' doit être un nombre valide."})
                
        reste = (somme_totale_caisse(anneeacademique_id) + float(indemnite)) - float(amount)
                 
        query = Renumeration.objects.filter(user_id=user_id, month=month, type_renumeration=type_renum, anneeacademique_id=anneeacademique_id)
        user = User.objects.get(id=request.user.id)
        if user.check_password(password) == False:
            return JsonResponse({
                "status": "error",
                "message": "Mot de passe incorrect."})
        if reste < 0:
            return JsonResponse({
                    "status": "error",
                    "message": "Le solde de la caisse est insufisant."}) 
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})   
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette rénumeration existe déjà."})
        else:
            total_amount = float(amount) + float(indemnite)
            renumeration = Renumeration(
                user_id=user_id, 
                month=month, 
                amount=amount,
                indemnite=indemnite,
                total_amount=total_amount,
                anneeacademique_id=anneeacademique_id,
                mode_payment=mode_payment,
                type_renumeration=type_renum,
                responsable_id=request.user.id)
            # Nombre de contrats avant l'ajout
            count0 = Renumeration.objects.all().count()
            renumeration.save()
            # Nombre de contrats après l'ajout
            count1 = Renumeration.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                        "status": "success",
                        "message": "Rénumeration admin enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Insertion a échouée."}) 

    months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    # Récuperer les administrateurs
    users_contrats = (Contrat.objects.values("user_id")
                      .filter(type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
                      .annotate(nb_contrats=Count("user_id")))
    users = []
    for uc in users_contrats:
        user = User.objects.get(id=uc["user_id"])
        # Recuperer les groupes de l'utilisateurs
        roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
        for role in roles:
            if role.user not in users and role.group.name in permission_admin:
                users.append(role.user)
    
    mode_payments = ["Espèce", "Virement", "Mobile"]
    context = {
        "setting": setting,
        "months": months,
        "users": users,
        "mode_payments": mode_payments
    }
    return render(request, "renum/add_renum_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_renum_ad(request, id, month, type_renumeration):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    mont = dechiffrer_param(month)
    type_renum = dechiffrer_param(type_renumeration)
    anneeacademique_id = request.session.get('anneeacademique_id')
    amount = 0
    if type_renum == "Administrateur scolaire":
        contrats = Contrat.objects.filter(user_id=user_id, type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id).order_by("id")    
        for contrat in contrats:
            months = month_contrat_user(contrat) # Récuperer tous les mois de ce contrat
            if mont in months: # Verifier si ce mois fait parti des mois de ce contrat
                amount = contrat.amount
                break
            
    if type_renum == "Enseignant du cycle fondamental":
        contrats = Contrat.objects.filter(user_id=user_id, type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).order_by("id")    
        for contrat in contrats:
            months = month_contrat_user(contrat) # Récuperer tous les mois de ce contrat
            if mont in months: # Verifier si ce mois fait parti des mois de ce contrat
                amount = contrat.amount
                break
    
    user = User.objects.get(id=user_id)     
    mode_payments = ["Espèce", "Virement", "Mobile"]  
    context = {
        "setting": setting,
        "user": user,
        "amount": amount,
        "month": mont,
        "mode_payments": mode_payments,
        "type_renumeration": type_renum
    }
    return render(request, "renum/add_renum_ad.html", context)
    
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_renum_admin(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    renumeration_id = int(dechiffrer_param(str(id)))
    renumeration = Renumeration.objects.get(id=renumeration_id)
    # Répuerer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)  
    #Récuperer les utilisateurs qui ont signé un contrat
    users_contrats = (Contrat.objects.values("user_id")
                      .filter(anneeacademique_id=anneeacademique_id, type_contrat="Administrateur scolaire")
                      .annotate(nb_contrats=Count("user_id")))
    
    users = []
    for uc in users_contrats:
        user = User.objects.get(id=uc["user_id"])
        if user.id != renumeration.user.id:
            # Recuperer les groupes de l'utilisateurs
            roles = EtablissementUser.objects.filter(user=user, etablissement=etablissement)
            for role in roles:
                if role.user not in users and role.group.name in permission_admin:
                    users.append(role.user)
        
    tab_months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mode_payments = ["Espèce", "Virement", "Mobile"]
    tab_mode_payment = []
    for mode_payment in mode_payments:
        if renumeration.mode_payment != mode_payment:
            tab_mode_payment.append(mode_payment)
            
    months = []
    for month in tab_months:
        if month != renumeration.month:
            months.append(month)
    context = {
        "setting": setting,
        "renumeration": renumeration,
        "users": users,
        "months": months,
        "mode_payments": mode_payments
    }
    return render(request, "renum/edit_renum_admin.html", context)
   

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_ra(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            renumeration = Renumeration.objects.get(id=id)
        except:
            renumeration = None

        if renumeration is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            user_id = request.POST["user"]
            month = request.POST["month"]
            amount = bleach.clean(request.POST["amount"].strip())
            indemnite = bleach.clean(request.POST["indemnite"].strip())
            mode_payment = bleach.clean(request.POST["mode_payment"].strip())
            password = bleach.clean(request.POST["password"].strip())
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)    
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")
            
            indemnite = re.sub(r'\xa0', '', indemnite)  # Supprime les espaces insécables
            indemnite = indemnite.replace(" ", "").replace(",", ".")

            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
            try:
                indemnite = Decimal(indemnite)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "L'indemnité' doit être un nombre valide."})
            
            # Vérifier l'existence de la rénumeration
            renumerations = Renumeration.objects.filter(month=month, user_id=user_id, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabRenumeration = []
            for r in renumerations:   
                dic = {}
                dic["user_id"] = r.user.id
                dic["month"] = r.month
                dic["anneeacademique_id"] = r.anneeacademique.id
                tabRenumeration.append(dic)            
                
            new_dic = {}
            new_dic["user_id"] = int(user_id)
            new_dic["month"] = month
            new_dic["anneeacademique_id"] = int(anneeacademique_id)
            
            reste = (somme_totale_caisse(anneeacademique_id) + float(indemnite)) - float(amount)
            
            user = User.objects.get(id=request.user.id)
            if user.check_password(password) == False:
                return JsonResponse({
                    "status": "error",
                    "message": "Mot de passe incorrect."})
            if reste < 0:
                return JsonResponse({
                    "status": "error",
                    "message": "Le solde de la caisse est insufisant."}) 
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})            
            if new_dic in tabRenumeration: # Vérifier l'existence de la rénumeration
                return JsonResponse({
                    "status": "error",
                    "message": "Cette rénumeration existe déjà."})
            else:
                total_amount = float(amount) + float(indemnite)
                renumeration.user_id = user_id
                renumeration.month = month
                renumeration.amount = amount
                renumeration.indemnite = indemnite
                renumeration.total_amount = total_amount
                renumeration.mode_payment = mode_payment
                renumeration.save()
                
                return JsonResponse({
                    "status": "success",
                    "message": "Rénumeration modifiée avec succès."})


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_renum_admin(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    renumeration_id = int(dechiffrer_param(str(id)))
    
    renumeration = Renumeration.objects.get(id=renumeration_id)
    # Nombre de contrats avant la suppression
    count0 = Renumeration.objects.all().count()
    renumeration.delete()
    # Nombre de contrats après la suppression
    count1 = Renumeration.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Elément supprimé avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("renum/renum_admin")

def ajax_delete_renum_admin(request, id):
    renumeration = Renumeration.objects.get(id=id)
    context = {
        "renumeration": renumeration
    }
    return render(request, "ajax_delete_renum_admin.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def mes_renum_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    renumerations = Renumeration.objects.filter(anneeacademique_id=anneeacademique_id, user_id=request.user.id)
    context = {
        "setting": setting,
        "renumerations": renumerations
    }
    return render(request, "renum/mes_renum_admin.html", context)  

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def recapitulatif(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    months = month_actifs(anneeacademique_id)
    context = {
        "months": months,
        "setting": setting
    }
    return render(request, "recapitulatif.html", context)

def ajax_type_contrat(request, type_contrat):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    context = {
        "type_contrat": type_contrat,
        "setting": setting
    }
    return render(request, "ajax_type_contrat.html", context)

# Selectionner les mois du contrat de l'utilisateur
def ajax_user_month_contrat(request, user_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    contrats = Contrat.objects.filter(user_id=user_id, type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id,).order_by("id")
    months = []
    for contrat in contrats:
        months += month_contrat_user(contrat)
    context = {
        "months": months
    }
    return render(request, "ajax_user_month_contrat.html", context)

def ajax_user_amount(request, user_id, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    contrats = Contrat.objects.filter(user_id=user_id, type_contrat="Administrateur scolaire", anneeacademique_id=anneeacademique_id).order_by("id")
    amount = 0
    for contrat in contrats:
        months = month_contrat_user(contrat) # Récuperer tous les mois de ce contrat
        if month in months: # Verifier si ce mois fait parti des mois de ce contrat
            amount = contrat.amount
    context = {
        "amount": amount,
        "setting": get_setting(anneeacademique_id)
    }
    return render(request, "ajax_user_amount.html", context)


def total_renum_salle(salle_id, anneeacademique_id, month):
    
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
                
            total_renum += calculer_montant(enseignement.cout_heure, formatted_time)
                
        return total_renum    
    
# Recuperer les salles ou les élèves ont payé, ou encore les enseignants ont été rénumeré  
def get_salles(month, anneeacademique_id):
    #Récuperer les salles
    salles = Salle.objects.all()
    tabSalles = []
    tabSallePay = []    
    salles_payments = (Payment.objects.values("salle_id")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(nb_payments=Count("salle_id")))
    for sp in salles_payments:
        tabSallePay.append(Salle.objects.get(id=sp["salle_id"]))
        
    tabSalleEmar = []    
    salles_emargements = (Emargement.objects.values("salle_id")
                       .filter(month=month, anneeacademique_id=anneeacademique_id)
                       .annotate(nb_emargements=Count("salle_id")))
    for sp in salles_emargements:
        tabSalleEmar.append(Salle.objects.get(id=sp["salle_id"]))
        
    for salle in salles:
        if (salle in tabSallePay) or (salle in tabSalleEmar):
            if salle not in tabSalles:
                tabSalles.append(salle)
                
    return tabSalles 
      
    
def ajax_recapitulatif(request, month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    salles = []
    position = 0 # Position de la salle
    recette_college_lycee = 0
    total_paiement_student = 0
    total_renum_enseignant = 0
    total_paiement_student_fondamental = 0
    liste_salles = get_salles(month, anneeacademique_id)
    salles_secondaire = []
    for salle in liste_salles:
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            dic = {}
            # Recuperer la salle
            dic["salle"] = salle
            # Somme totale payée par les étudiants
            sum_payment = (Payment.objects.filter( salle_id=salle.id, month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
            dic["sum_payment"] = sum_payment
            # Somme totale qu'on a payé les enseignants
            sum_renum = total_renum_salle(salle.id, anneeacademique_id, month)
            dic["sum_renum"] = float(sum_renum)
            dic["reste"] = float(sum_payment) - float(sum_renum)
        
            total_paiement_student += sum_payment
            total_renum_enseignant += sum_renum
            salles_secondaire.append(dic)
        else:
            position += 1
            dic = {}
            # Recuperer la salle
            dic["salle"] = salle
            # Somme totale payée par les étudiants
            sum_payment = (Payment.objects.filter( salle_id=salle.id, month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
            dic["sum_payment"] = sum_payment
            dic["position"] = position
            total_paiement_student_fondamental += sum_payment
            salles.append(dic)
    
    # Recette du collège et du lycée
    recette_college_lycee = float( total_paiement_student) - float(total_renum_enseignant)
    # Total des renumerations des enseignants du fondamental
    total_renumeration_enseignants_fondamental = (Renumeration.objects.filter(month=month, type_renumeration="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
    # Recette du cycle prescolaire et primaire      
    recette_prescolaire_primaire = float(total_paiement_student_fondamental) - float(total_renumeration_enseignants_fondamental)
    # Calculer toutes les indemnités des enseignant d'un mois
    sum_indemnite = (Renumeration.objects.filter(month=month, type_renumeration__in=["Enseignant du cycle fondamental", "Enseignant du cycle secondaire"], anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
    # Récuperer les renumérations avec indemnités
    renumerations = Renumeration.objects.filter(month=month, type_renumeration__in=["Enseignant du cycle fondamental", "Enseignant du cycle secondaire"], anneeacademique_id=anneeacademique_id).exclude(indemnite=0)
    
    # Calucler le montant total de renumeration des administrateurs
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
    
    recette_month = recette_prescolaire_primaire + recette_college_lycee - float(sum_indemnite) - total_renum_admin + total_depense
    
    context = {
        "setting": get_setting(anneeacademique_id),
        "position_milieu": round(position/2),
        "position": position,
        "salles": salles,
        "salles_secondaire": salles_secondaire,
        "recette_prescolaire_primaire": recette_prescolaire_primaire,
        "recette_college_lycee": recette_college_lycee,
        "total_paiement_student": total_paiement_student,
        "total_renum_enseignant": total_renum_enseignant,
        "total_paiement_student_fondamental": total_paiement_student_fondamental,
        "total_renumeration_enseignants_fondamental": total_renumeration_enseignants_fondamental,
        "sum_indemnite": sum_indemnite,
        "renumerations": renumerations,
        "month": month,
        "total_renum_admin": total_renum_admin,
        "depenses": tabdepenses,
        "recette_month": recette_month
    }
    return render(request, "ajax_recapitulatif.html", context)


def month_actifs(anneeacademique_id):
    months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    tabMonths = []
    
    tabMonthRenumEns = []
    months_renum_ens = (Renumeration.objects.values("month")
                        .filter(anneeacademique_id=anneeacademique_id)
                        .annotate(nb_emargements=Count("month")))
    for me in months_renum_ens:
        tabMonthRenumEns.append(me["month"])
    
    tabMonthPay = []    
    months_payments = (Payment.objects.values("month")
                        .filter(anneeacademique_id=anneeacademique_id)
                        .annotate(nb_payments=Count("month")))
    for mp in months_payments:
        tabMonthPay.append(mp["month"])
        
    tabMonthRenum = []    
    months_renumerations = (Renumeration.objects.values("month")
                        .filter(type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id)
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
        if (month in tabMonthRenumEns) or (month in tabMonthPay) or (month in tabMonthRenum) or (month in tabMonthDepense):
            if month not in tabMonths:
                tabMonths.append(month) 
    
    return tabMonths
 
@login_required(login_url='connection/account')           
@allowed_users(allowed_roles=permission_gestionnaire)       
def caisse(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    months = month_actifs(anneeacademique_id)
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
            sum_renum = total_renum_salle(me["salle_id"], anneeacademique_id, month)
            total_renum_enseignant += sum_renum
            
        # Calculer toutes les indemnités des enseignant d'un mois
        total_indemnite = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
        
        # Calucler le montant total de renumeration des administarteurs
        total_amount = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
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
        
        recette_month = float(total_paiement_student) - float(total_renum_enseignant) - float(total_indemnite) - total_renum_admin + total_depense
        
        dic_caisse["recette_month"] = recette_month
        
        recette_totale += recette_month
        
        caisses.append(dic_caisse)
        
    # somme total des inscription
    salles_inscriptions = Inscription.objects.values("salle_id").filter(anneeacademique_id=anneeacademique_id).annotate(nb_inscriptions=Count("salle_id"))
    tabSalles = []
    total_inscription = 0
    for si in salles_inscriptions:
        dic = {}
        salle = Salle.objects.get(id=si["salle_id"])
        dic["salle"] = salle
        total_inscription_salle = Inscription.objects.filter(salle_id=si["salle_id"], anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0
        dic["total_inscription_salle"] = total_inscription_salle
        
        total_inscription += total_inscription_salle
        tabSalles.append(dic)
    total = float(recette_totale) + float(total_inscription)
    context = {
        "setting": get_setting(anneeacademique_id),
        "caisses": caisses,
        "recette_totale": recette_totale,
        "totale": total,
        "total_inscription": total_inscription,
        "salles": tabSalles
        
    }
    return render(request, "caisse.html", context) 

def comparaison_recette_par_annee_scolaire(id):
    annees_academiques = AnneeCademique.objects.filter(id__lte=id).order_by('-id')[:3]
    recettes_globales = []
    months_globales = []
    for annee_academique in annees_academiques:
        dic_globle = {}
        dic_globle["anneeacademique"] = annee_academique
        anneeacademique_id = annee_academique.id
        months = month_actifs(anneeacademique_id)
        caisses = []
        recette_totale = 0
        for month in months:
            dic_caisse = {}
            dic_caisse["month"] = month
            # Somme totale payée par les étudiants
            total_paiement_student = (Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
            total_renum_enseignant = 0
            months_emargements = (Emargement.objects.values("salle_id")
                            .filter(month=month, anneeacademique_id=anneeacademique_id)
                            .annotate(nb_emargements=Count("salle_id")))
            
            for me in months_emargements:
                # Somme totale qu'on a payé les enseignants
                sum_renum = total_renum_salle(me["salle_id"], anneeacademique_id, month)
                total_renum_enseignant += sum_renum
                
            # Calculer toutes les indemnités des enseignant d'un mois
            sum_indemnite = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
            
            # Calucler le montant total de renumeration des enseignants
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
            
            dic_caisse["recette_month"] = int(recette_month)
            
            recette_totale += recette_month
            
            caisses.append(dic_caisse)
            
            # Récuperer les mois actifs dans au moins une année scolaire
            if month not in months_globales:
                months_globales.append(month)
            
        dic_globle["caisses"] = caisses 
        
        recettes_globales.append(dic_globle)
    return recettes_globales, months_globales

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def apercu_global(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    months = month_actifs(anneeacademique_id)
    caisses = []
    recette_totale = 0
    for month in months:
        dic_caisse = {}
        dic_caisse["month"] = month
        # Somme totale payée par les étudiants
        total_paiement_student = (Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
        total_renum_enseignant = 0
        months_emargements = (Emargement.objects.values("salle_id")
                        .filter(month=month, anneeacademique_id=anneeacademique_id)
                        .annotate(nb_emargements=Count("salle_id")))
        
        for me in months_emargements:
            # Somme totale qu'on a payé les enseignants
            sum_renum = total_renum_salle(me["salle_id"], anneeacademique_id, month)
            total_renum_enseignant += sum_renum
            
        # Calculer toutes les indemnités des enseignant d'un mois
        sum_indemnite = (Renumeration.objects.filter(month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
        
        # Calucler le montant total de renumeration des enseignants
        total_amount = (Renumeration.objects.filter(month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).aggregate(Sum('amount'))['amount__sum'] or 0)
        total_indemnite = (Renumeration.objects.filter(month=month, anneeacademique_id=anneeacademique_id).aggregate(Sum('indemnite'))['indemnite__sum'] or 0)
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
        
        dic_caisse["recette_month"] = int(recette_month)
        
        recette_totale += recette_month
        
        caisses.append(dic_caisse)
        
    recettes_globales, months_globales = comparaison_recette_par_annee_scolaire(anneeacademique_id)
    
    context = {
        "setting": get_setting(anneeacademique_id),
        "caisses": caisses,
        "recette_totale": int(recette_totale),
        "recettes_globales":  recettes_globales,
        "months_globales": months_globales
        
    }
    return render(request, "apercu_global.html", context) 


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire_enseignant)
def bulletin_paie_enseignant(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    renumeration_id = int(dechiffrer_param(str(id)))
    
    renumeration = Renumeration.objects.get(id=renumeration_id)
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo

    # Lire l'image en mode binaire et encoder en Base64
    base64_string = None
    if image_path:  
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    # Récuperer le mois et l'année rémunéré
    months_years = month_year_periode_annee_scolaire_remuneration(anneeacademique_id)
    periode = ""
    for month_year in months_years:
        if month_year["month"] == renumeration.month:
            periode = f'{month_year["month"]} { month_year["year"]}'
    # Récuperer le poste
    contrat = Contrat.objects.filter(user_id=renumeration.user.id, anneeacademique_id=anneeacademique_id).order_by("-id").first()
    poste = contrat.poste
    context = {
        "renumeration": renumeration,   
        "poste": poste,   
        "base64_image": base64_string, 
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle,
        "periode": periode
    }
    template = get_template("bulletin_paie_enseignant.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Bulletin_paie_{ renumeration.user.last_name }_{ renumeration.user.first_name }.pdf"
    return reponse

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire_enseignant)
def bulletin_paie_admin(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    renumeration_id = int(dechiffrer_param(str(id)))
    
    renumeration = Renumeration.objects.get(id=renumeration_id)
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo

    # Lire l'image en mode binaire et encoder en Base64
    base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    # Récuperer le poste
    contrat = Contrat.objects.filter(user_id=renumeration.user.id, anneeacademique_id=anneeacademique_id).order_by("-id").first()
    poste = contrat.poste
    context = {
        "renumeration": renumeration,   
        "poste": poste,   
        "base64_image": base64_string, 
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle
    }
    template = get_template("bulletin_paie_admin.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Bulletin_paie_{ renumeration.user.last_name }_{ renumeration.user.first_name }.pdf"
    return reponse      
        
