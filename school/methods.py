import hashlib
# Importation des modules tiers
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField
from django.core.exceptions import ObjectDoesNotExist
from datetime import date, timedelta
from anneeacademique.models import AnneeCademique
from emargement.models import Emargement
from emploi_temps.models import EmploiTemps
from absence.models import Absence
from renumeration.models import Contrat
from salle.models import Salle
from enseignement.models import Enseigner

# Annoter chaque session avec la durée (heure_fin - heure_debut)
# Durée par session
duration_expr = ExpressionWrapper(
    F('heure_fin') - F('heure_debut'),
    output_field=DurationField()
)

#=================================== Définition des mois ===================================== 
def get_file_hash(file):
    hash_md5 = hashlib.md5() # Cette objet de MD5 servira de stocker et calculer l'empreinte MD5.
    for chunk in file.chunks(): # Parcourir le fichier par morceau pour ne pas surcherger la memoire
        hash_md5.update(chunk) # Ajout de chaque morceau au calcul de hash et en mettant en même à jour le hash
    return hash_md5.hexdigest() # retourner l'empreinte MD5 sous forme de chaîne hexadécimale

def format_month(month):
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

# Determiner tous les mois de l'année académique   
def periode_annee_scolaire(anneeacademique_id):
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
        months.append(current_date.strftime("%m"))
        # Passer au mois suivant
        next_month = current_date.month % 12 + 1
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        current_date = current_date.replace(month=next_month, year=next_year)

    month_format = []
    for month in months:
        if month == '01':
            month_format.append("Janvier")
        elif month == '02':
            month_format.append("Février")
        elif month == '03':
            month_format.append("Mars")
        elif month == '04':
            month_format.append("Avril")
        elif month == '05':
            month_format.append("Mai")
        elif month == '06':
            month_format.append("Juin")
        elif month == '07':
            month_format.append("Juillet")
        elif month == '08':
            month_format.append("Août")
        elif month == '09':
            month_format.append("Septembre")
        elif month == '10':
            month_format.append("Octobre")
        elif month == '11':
            month_format.append("Novembre")
        else:
            month_format.append("Décembre")
    return month_format  # Retourne la liste des mois

def debut_month_actuel(anneeacademique_id): # Liste des mois du début de la période de l'année scolaire jusqu'au mois actuel
    # Récuperer tous les mois de l'année académique
    months = periode_annee_scolaire(anneeacademique_id)
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    # Récuperer les tous mois du début de la rentrée jusqu'au mois actuel
    tabMonths = []
    for month in months:
        if month == month_actuel:
            tabMonths.append(month)
            break
        else:
            tabMonths.append(month)
    return tabMonths


# Determiner les mois du contrat de l'utilisateur
def month_contrat_user(contrat):   

    start_date = contrat.date_debut
    end_date = contrat.date_fin 

    # Génération des mois dans l'intervalle
    months = []
    current_date = start_date.replace(day=1)  # S'assurer de commencer au début du mois

    while current_date <= end_date:
        months.append(current_date.strftime("%m"))
        # Passer au mois suivant
        next_month = current_date.month % 12 + 1
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        current_date = current_date.replace(month=next_month, year=next_year)

    month_format = []
    for month in months:
        if month == '01':
            month_format.append("Janvier")
        elif month == '02':
            month_format.append("Février")
        elif month == '03':
            month_format.append("Mars")
        elif month == '04':
            month_format.append("Avril")
        elif month == '05':
            month_format.append("Mai")
        elif month == '06':
            month_format.append("Juin")
        elif month == '07':
            month_format.append("Juillet")
        elif month == '08':
            month_format.append("Août")
        elif month == '09':
            month_format.append("Septembre")
        elif month == '10':
            month_format.append("Octobre")
        elif month == '11':
            month_format.append("Novembre")
        else:
            month_format.append("Décembre")
    return month_format  # Retourne la liste des mois



# Determiner le nombre d'heures par jour et leur moyenne
def heure_par_jour_et_moyenne(enseignant_id, salle_id, anneeacademique_id):
    # Grouper par jour, puis sommer les durées
    emplois_groups = (
        EmploiTemps.objects
        .filter(enseignant_id=enseignant_id, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
        .annotate(duree=duration_expr)
        .values('jour')
        .annotate(total_duree=Sum('duree'))
    )
    
   # Affichage du total d'heures par jour en entier
    heures_par_jour = {
        eg['jour']: int(eg['total_duree'].total_seconds() // 3600)
        for eg in emplois_groups
    } 
    values = []
    i = 0 # Nombre de jours
    for value in heures_par_jour.values():
        i += 1
        values.append(value)
    
    moyenne = 0
    if i > 0:
        moyenne = sum(values)/i
        
    return heures_par_jour, moyenne

# Determiner heure totale du retard
def retard_total(enseignant_id, month, salle_id, anneeacademique_id):
    emargements = Emargement.objects.filter(
        enseignant_id=enseignant_id, 
        month=month, 
        anneeacademique_id=anneeacademique_id, 
        salle_id=salle_id
    )        
    # Initialisation avec une durée nulle
    total_delta = timedelta(0)
    for emarg in emargements:
        # Convertir les objets time en timedelta 
        # Heure total que l'enseignant a fait 
        start_delta_emargement = timedelta(hours=emarg.heure_debut.hour, minutes=emarg.heure_debut.minute)
        end_delta_emargement = timedelta(hours=emarg.heure_fin.hour, minutes=emarg.heure_fin.minute)
        # Calculer les heures faites par l'enseignant
        heure_faite =  end_delta_emargement - start_delta_emargement

        # Heure totale que l'enseignant est censé faire par jour
        emploistemps = EmploiTemps.objects.filter(jour=emarg.jour, enseignant_id=emarg.enseignant.id, anneeacademique_id=anneeacademique_id).first()
        start_delta_emploitemps = timedelta(hours=emploistemps.heure_debut.hour, minutes=emarg.heure_debut.minute)
        end_delta_emploitemps = timedelta(hours=emploistemps.heure_fin.hour, minutes=emarg.heure_fin.minute)
        heure_faire =  end_delta_emploitemps - start_delta_emploitemps

        total_heure = heure_faire - heure_faite # Heure total du retard de l'enseignant 
                
        total_delta += total_heure
                
    # Extraire les heures et les minutes en normalisant (si la somme dépasse 24 heures)
    total_seconds = total_delta.total_seconds()
    total_hours = int(total_seconds // 3600) % 24  # Récupérer les heures (modulo 24 pour ne pas dépasser une journée)
    total_minutes = int((total_seconds % 3600) // 60)

    # Afficher le résultat au format HH:MM
    formatted_time = f"{total_hours:02}:{total_minutes:02}"              
    return formatted_time

# Récuperer le mois dans une date
def recuperer_mois_annee(annee):
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

# Determiner le nombre d'absence de l'enseignant 
def nombre_absence_enseignant(month, enseignant_id, salle_id, anneeacademique_id):
    absences = Absence.objects.filter(enseignant_id=enseignant_id, salle_id=salle_id, anneeacademique_id=anneeacademique_id, status_decision__in=[0,2])   
    nombre_absences = 0
    for absence in absences:
        if month == recuperer_mois_annee(absence.date_absence):
            if absence.status_decision == 0 and absence.motif == "" or absence.status_decision == 2:
                nombre_absences += 1
                
    return nombre_absences

# Calculer le cout total des heures
def cout_total_heures(cout_heure, heure_totale):
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

# Calculer le salaire de l'enseignant du cycle fondament en fonction de ses absences
def salaire_enseignant_cycle_fondament_avec_absence(month, enseignant_id, salle_id, anneeacademique_id):
    # Compter le nombre de salles que l'enseignant enseigne
    enseignements_group = (Enseigner.objects.values("salle_id")
                           .filter(enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id)
                           .annotate(nombre_salles=Count("salle_id")))
    nombre_salles = 0
    for eg in enseignements_group:
        salle = Salle.objects.get(id=eg["salle_id"])
        if salle.cycle.libelle in ["Prescolaire", "Primaire"]:
            nombre_salles += 1
    
    nombre_absences = nombre_absence_enseignant(month, enseignant_id, salle_id, anneeacademique_id)
    # Determiner la moyenne d'heures par jour de l'enseignant
    moyenne = heure_par_jour_et_moyenne(enseignant_id, salle_id, anneeacademique_id)[1]
    # Total du retard
    total_retard = retard_total(enseignant_id, month, salle_id, anneeacademique_id)
    contrat = Contrat.objects.filter(user_id=enseignant_id, type_contrat="Enseignant du cycle fondamental", anneeacademique_id=anneeacademique_id).first()
    cout_jour = contrat.amount/20 
    # Cout par heure
    cout_heure = 0
    if moyenne > 0:
        cout_heure = float(cout_jour) / float(moyenne)
    salaire = 0
    if nombre_salles >0:
        salaire = float(contrat.amount/nombre_salles) - float(nombre_absences * cout_jour) - cout_total_heures(cout_heure, total_retard)
    return salaire

