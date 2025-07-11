import bleach
import re
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
# Importation des modules locaux
from .models import Depense
from school.views import get_setting
from app_auth.decorator import allowed_users
from anneeacademique.models import AnneeCademique
from scolarite.utils.crypto import dechiffrer_param

permission_gestionnaire = ['Promoteur', 'Directeur Général', 'Gestionnaire']

#================== Gestion de contrats =================================
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def depenses(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    depenses_mois = Depense.objects.values("month").filter(anneeacademique_id=anneeacademique_id).annotate(nb_depenses=Count("month"))
    tabdepenses = []
    for dm in depenses_mois:
        dic = {}
        dic["month"] = dm["month"]
        list_depenses = []
        depenses = Depense.objects.filter(month=dm["month"], anneeacademique_id=anneeacademique_id) 
        for depense in depenses:
            new_dic = {}
            new_dic["depense"] = depense
            history = depense.history.all()
            new_dic["nombre_histoires"] = len(history)
            list_histories = []

            for i, record in enumerate(history):
                dic_history = {}
                dic_history["date"] = record.history_date
                dic_history["action"] = record.get_history_type_display()
                dic_history["user"] = record.history_user or "Utilisateur inconnu"
                
                if record.history_type == '+':
                    #Création de l'objet avec les champs suivants
                    tab_add = []
                    for field in record.instance._meta.fields:
                        dic_add = {}
                        dic_add["field_name"] = field.name
                        dic_add["value"] = getattr(record, field.name, None)
                        tab_add.append(dic_add)
                    dic_history["tab_add"] = tab_add

                elif record.history_type == '-':
                    # Objet supprimé, dernière valeur connue
                    tab_delete = []
                    for field in record.instance._meta.fields:
                        dic_del = {}
                        dic_del["field_name"] = field.name
                        dic_del["value"] = getattr(record, field.name, None)
                        tab_delete.append(dic_del)
                    dic_history["tab_delete"] = tab_delete
                    
                elif record.history_type == '~' and i + 1 < len(history):
                    diff = record.diff_against(history[i + 1])
                    tab_update = []
                    for change in diff.changes:
                        dic_update = {}
                        dic_update["field"] = change.field
                        dic_update["old"] = change.old
                        dic_update["new"] = change.new
                        tab_update.append(dic_update)
                    dic_history["tab_update"] = tab_update
                       
                list_histories.append(dic_history)
                
            new_dic["histories"] = list_histories
            
            list_depenses.append(new_dic)
               
        dic["depenses"] =  list_depenses             
        dic["nb_depenses"] = dm["nb_depenses"]
        tabdepenses.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "depenses": tabdepenses,
        "anneeacademique": anneeacademique
    }
    return render(request, "depenses.html", context)    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
@transaction.atomic
def add_depense(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    if request.method == "POST":

        month = request.POST["month"]
        signe = request.POST["signe"]
        type_depense = request.POST["type_depense"]
        if type_depense == "Autre":
            type_depense = bleach.clean(request.POST["autre"].strip())
            
        description = bleach.clean(request.POST["description"].strip())
        amount = bleach.clean(request.POST["amount"].strip())
        
        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)   
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
                 
        query = Depense.objects.filter(month=month, type_depense__in=["Frais du loyer", "Frais de l'électricité", "Frais de l'internet", "Frais du téléphone"], anneeacademique_id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce contrat existe déjà."})
        else:
            depense = Depense(
                month=month,
                signe=signe,
                type_depense=type_depense, 
                description=description,
                amount=amount,
                anneeacademique_id=anneeacademique_id,
                user_id=request.user.id)
            # Nombre de dépenses avant l'ajout
            count0 = Depense.objects.all().count()
            depense.save()
            # Nombre de dépenses après l'ajout
            count1 = Depense.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Dépense enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Insertion a échouée."}) 
                
    months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    type_depenses = ["Frais du loyer", "Frais de l'électricité", "Frais de l'internet", "Frais du téléphone", "Travaux", "Don", "Autre"]
    context = {
        "setting": setting,
        "months": months,
        "type_depenses": type_depenses
    }
    return render(request, "add_depense.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_depense(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    depense_id = int(dechiffrer_param(str(id)))
    depense = Depense.objects.get(id=depense_id)
        
    tab_months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    months = [month for month in tab_months if month != depense.month]
            
    tab_type_depenses = type_depenses = ["Frais du loyer", "Frais de l'électricité", "Frais de l'internet", "Frais du téléphone", "Travaux", "Don", "Autre"]
    type_depenses = [type_depense for type_depense in tab_type_depenses if type_depense != depense.type_depense]
            
    context = {
        "setting": setting,
        "depense": depense,
        "months": months,
        "type_depenses": type_depenses
    }
    return render(request, "edit_depense.html", context)
   

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_dp(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            depense = Depense.objects.get(id=id)
        except:
            depense = None

        if depense is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            month = request.POST["month"]
            signe = request.POST["signe"]
            type_depense = request.POST["type_depense"]
            description = bleach.clean(request.POST["description"].strip())
            amount = bleach.clean(request.POST["amount"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            
            if type_depense == "Autre":
                type_depense = bleach.clean(request.POST["autre"].strip())
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
            depenses = Depense.objects.filter(month=month, type_depense__in=["Frais du loyer", "Frais de l'électricité", "Frais de l'internet", "Frais du téléphone"], anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabDepense = []
            for d in depenses:   
                dic = {}
                dic["month"] = d.month
                dic["anneeacademique_id"] = d.anneeacademique.id
                tabDepense.append(dic)            
                
            new_dic = {}
            new_dic["month"] = month
            new_dic["anneeacademique_id"] = int(anneeacademique_id)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if new_dic in tabDepense: # Vérifier l'existence du programme
                return JsonResponse({
                    "status": "error",
                    "message": "Cette dépense existe déjà."})
            else:
                depense.month = month
                depense.signe = signe
                depense.type_depense = type_depense
                depense.description = description
                depense.amount = amount
                depense.save()
                
                return JsonResponse({
                    "status": "success",
                    "message": "Dépense modifié avec succès."})

def ajax_delete_depense(request, id):
    depense = Depense.objects.get(id=id)
    context = {
        "depense": depense
    }
    return render(request, "ajax_delete_depense.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_depense(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    depense_id = int(dechiffrer_param(str(id)))
    depense = Depense.objects.get(id=depense_id)
    # Nombre de dépenses avant la suppression
    count0 = Depense.objects.all().count()
    depense.delete()
    # Nombre de dépenses après la suppression
    count1 = Depense.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Une dépense a été supprimée avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("depenses")


def type_depense(request, type_depense):
    context = {"type_depense": type_depense}
    return render(request, "type_depense.html", context)
