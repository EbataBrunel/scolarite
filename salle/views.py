# Importation des modules standards
import bleach
import re
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from decimal import Decimal
from django.contrib import messages
# Importation des modules locaux
from .models import *
from classe.models import Classe
from programme.models import Programme
from enseignement.models import Enseigner
from paiement.models import Payment, AutorisationPayment, AutorisationPaymentSalle, ContratEtablissement
from inscription.models import Inscription
from emploi_temps.models import EmploiTemps
from composition.models import Composer, Deliberation
from emargement.models import Emargement
from publication.models import Publication
from absence.models import Absence
from cycle.models import Cycle
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def salles(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    salles_groupes = (Salle.objects.values('cycle_id')
                      .filter(anneeacademique_id=anneeacademique_id)
                      .annotate(nombre_cycles=Count('number'))
    )
    tabSalle = []
    for sg in salles_groupes:
        cycle = Cycle.objects.get(id=sg["cycle_id"])
        dic = {}
        dic["cycle"] = cycle
        classes = Classe.objects.filter(cycle_id=cycle.id, anneeacademique_id=anneeacademique_id)
        dic["nombre_classes"] = classes.count()
        tabclasses = []
        for classe in classes:
            dic_class = {}
            dic_class["classe"] = classe
            dic_class["nombre_salles"] = Salle.objects.filter(cycle_id=cycle.id, classe_id=classe.id, anneeacademique_id=anneeacademique_id).count()            
            tabclasses.append(dic_class)
    
        dic["classes"] = tabclasses
        
        tabSalle.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "salles": tabSalle,
        "anneeacademique": anneeacademique
    }
    return render(request, "salles.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def salles_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle_id = request.session.get('cycle_id')
    classe_id = request.session.get('classe_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles = Salle.objects.filter(cycle_id=cycle_id, classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "salles":salles,
        "anneeacademique": anneeacademique
    }
    return render(request, "salles_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def detail_salle(request, classe_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(classe_id)))
    salles = Salle.objects.filter(classe_id=id)
    classe = Classe.objects.get(id=id)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)     
    context = {
        "classe": classe,
        "salles": salles,
        "anneeacademique": anneeacademique,
        "setting": setting,
    }
    return render(request, "detail_salle.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_salle(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        cycle_id = request.POST["cycle"]
        classe_id = request.POST["classe"]
        number = request.POST["number"]
        max_student = request.POST["max_student"]
        price = bleach.clean(request.POST["price"].strip())
        price_inscription = bleach.clean(request.POST["price_inscription"].strip())
        # Recuperer le cycle
        cycle = Cycle.objects.get(id=cycle_id)
        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        price = re.sub(r'\xa0', '', price)  # Supprime les espaces insécables
        price = price.replace(" ", "").replace(",", ".")
        
        price_inscription = re.sub(r'\xa0', '', price_inscription)  # Supprime les espaces insécables
        price_inscription = price_inscription.replace(" ", "").replace(",", ".")

        try:
            price = Decimal(price)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le frais mensuel doit être un nombre valide."})
            
        try:
            price_inscription = Decimal(price_inscription)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le frais de l'inscription doit être un nombre valide."})

        if cycle.libelle == "Lycée":
            serie_id = request.POST["serie"]
            query = Salle.objects.filter(classe_id=classe_id, serie_id=serie_id, number=number, anneeacademique_id=anneeacademique_id)
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if query.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Cette salle existe déjà."})
            else:
                salle = Salle(
                    cycle_id=cycle_id,
                    classe_id=classe_id, 
                    serie_id=serie_id, 
                    number=number, 
                    max_student=max_student,
                    price=price,
                    price_inscription=price_inscription,
                    anneeacademique_id=anneeacademique_id)
                
                # Nombre de salles avant l'ajout
                count0 = Salle.objects.all().count()
                salle.save()
                # Nombre de classes après l'ajout
                count1 = Salle.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Salle enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a echouée."})
        else:
            query = Salle.objects.filter(classe_id=classe_id, number=number, anneeacademique_id=anneeacademique_id)
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if query.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Cette salle existe déjà."})
            else:
                salle = Salle(
                    cycle_id=cycle_id,
                    classe_id=classe_id, 
                    number=number, 
                    max_student=max_student,
                    price=price,
                    price_inscription=price_inscription,
                    anneeacademique_id=anneeacademique_id)
                
                # Nombre de salles avant l'ajout
                count0 = Salle.objects.all().count()
                salle.save()
                # Nombre de classes après l'ajout
                count1 = Salle.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Salle enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a echouée."})
    
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id)
    numbers = ["", "1","2","3","4","5","6","7","8","10","11","12","13","14","15","16","17","19","20","21","22","23","24","25","26","27","28","29","30"]
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                    
    context = {
        "setting": setting,
        "cycles": cycles,
        "numbers": numbers,
        "contrat": contrat
    }
    return render(request, "add_salle.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_salle(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle_id = int(dechiffrer_param(str(id)))
    salle = Salle.objects.get(id=salle_id)
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=salle.classe.cycle.id)   
    classes = Classe.objects.filter(cycle_id=salle.classe.cycle.id, anneeacademique_id=anneeacademique_id).exclude(id=salle.classe.id)
    numbers = ["","1","2","3","4","5","6","7","8","10","11","12","13","14","15","16","17","19","20","21","22","23","24","25","26","27","28","29","30"]
    tabNumeber = [number for number in numbers if number != salle.number]
    
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                           
    if salle.cycle.libelle == "Lycée":
        series = Serie.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=salle.serie.id)
        context = {
            "setting": setting,
            "cycles": cycles,
            "salle": salle,
            "series": series,
            "classes": classes,
            "numbers": tabNumeber,
            "contrat": contrat
        }
    else:
        context = {
            "setting": setting,
            "cycles": cycles,
            "salle": salle,
            "classes": classes,
            "numbers": tabNumeber,
            "contrat": contrat
        }
    return render(request, "edit_salle.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_sl(request):
    anneeacademique_id = request.session.get('anneeacademique_id') 
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            salle = Salle.objects.get(id=id)
        except:
            salle = None

        if salle is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else:
            cycle_id = request.POST["cycle"] 
            classe_id = request.POST["classe"]
            number = request.POST["number"]
            max_student = bleach.clean(request.POST["max_student"].strip())
            price = bleach.clean(request.POST["price"].strip())
            price_inscription = bleach.clean(request.POST["price_inscription"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)        
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            price = re.sub(r'\xa0', '', price)  # Supprime les espaces insécables
            price = price.replace(" ", "").replace(",", ".")
            
            price_inscription = re.sub(r'\xa0', '', price_inscription)  # Supprime les espaces insécables
            price_inscription = price_inscription.replace(" ", "").replace(",", ".")
            # Recuperer le cycle
            cycle = Cycle.objects.get(id=cycle_id)
            try:
                price = Decimal(price)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le frais mensuel doit être un nombre valide."})
                
            try:
                price_inscription = Decimal(price_inscription)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le frais d'inscription doit être un nombre valide."})
                
            if cycle.libelle == "Lycée":
                serie_id = request.POST["serie"]
                #On verifie si cette classe a déjà été associée à une série
                salles = Salle.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
                tabSalle=[]
                for s in salles: 
                    if s.serie:
                        dic = {} 
                        dic["serie_id"] = int(s.serie.id)
                        dic["classe_id"] = int(s.classe.id)
                        dic["number"] = int(s.number)
                        tabSalle.append(dic)
                    
                new_dic = {}
                new_dic["serie_id"] = int(serie_id)
                new_dic["classe_id"] = int(classe_id)
                new_dic["number"] = int(number)
                
                if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont déjà été clôturées."})
                if new_dic in tabSalle: #On verifie si cette salle existe
                    return JsonResponse({
                        "status": "error",
                        "message": "Cette inscription existe déjà."})
                else:
                    salle.cycle_id = cycle_id
                    salle.classe_id = classe_id
                    salle.number = number
                    salle.max_student = max_student
                    salle.price = price
                    salle.price_inscription=price_inscription
                    salle.save()
                    return JsonResponse({
                        "status": "success",
                        "message": "Salle modifiée avec succès."})
            else:
                #On verifie si cette classe a déjà été associée à une série
                salles = Salle.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
                tabSalle=[]
                for s in salles: 
                    dic = {} 
                    dic["classe_id"] = int(s.classe.id)
                    dic["number"] = int(s.number)
                    tabSalle.append(dic)
                    
                new_dic = {}
                new_dic["classe_id"] = int(classe_id)
                new_dic["number"] = int(number)
                
                if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                    return JsonResponse({
                        "status": "error",
                        "message": "Les opérations de cette année académique ont déjà été clôturées."})
                if new_dic in tabSalle: #On verifie si cette salle existe
                    return JsonResponse({
                        "status": "error",
                        "message": "Cette inscription existe déjà."})
                else:
                    salle.cycle_id = cycle_id
                    salle.classe_id = classe_id
                    salle.number = number
                    salle.max_student = max_student
                    salle.price = price
                    salle.price_inscription=price_inscription
                    salle.save()
                    return JsonResponse({
                        "status": "success",
                        "message": "Salle modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_salle(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("gettings/maintenance")
    
    try:
        salle_id = int(dechiffrer_param(str(id)))
        salle = Salle.objects.get(id=salle_id)
    except:
        salle = None
        
    if salle:
        # Nombre de salles avant la suppression
        count0 = Salle.objects.all().count()
        salle.delete()
        # Nombre de salles après la suppression
        count1 = Salle.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("salles")


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_salle(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle_id = int(dechiffrer_param(str(id)))
    salle = Salle.objects.get(id=salle_id)
    nombre = {}
    nombre["nombre_programmes"] = Programme.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_enseignements"] = Enseigner.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_autorisation_payements_students"] = AutorisationPayment.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_autorisation_payements_salles"] = AutorisationPaymentSalle.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_payments"] = Payment.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_inscriptions"] = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_absences_enseignants"] = Absence.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_emargements"] = Emargement.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_publications"] = Publication.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_emploitemps"] = EmploiTemps.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_compositions"] = Composer.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_deliberations"] = Deliberation.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
        
    context = {
        "setting": setting,
        "salle": salle,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_salle.html", context)

def ajax_classe(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle = Cycle.objects.get(id=id)
    classes = Classe.objects.filter(cycle_id=id)
    series = Serie.objects.filter(anneeacademique_id=anneeacademique_id)
    context = {
        "cycle": cycle,
        "classes": classes,
        "series": series
    }
    return render(request, "ajax_classe.html", context)