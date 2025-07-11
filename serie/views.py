# Importation des models standards
import bleach
# Importation des models tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
# Importation des models locaux
from .models import Serie
from salle.models import Salle
from anneeacademique.models import AnneeCademique
from paiement.models import ContratEtablissement
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def series(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    series = Serie.objects.filter(anneeacademique_id=anneeacademique_id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "series":series,
        "anneeacademique": anneeacademique
    }
    return render(request, "series.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def series_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    series = Serie.objects.filter(anneeacademique_id=anneeacademique_id)
    context = {
        "setting": setting,
        "series":series
    }
    return render(request, "series_admin.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_serie(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        name = bleach.clean(request.POST["name"].strip())

        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            
        query = Serie.objects.filter(name=name, anneeacademique_id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette série existe déjà."})
        else:
            serie = Serie(name=name, anneeacademique_id=anneeacademique_id)
            # Nombre de séries avant l'ajout
            count0 = Serie.objects.all().count()
            serie.save()
            # Nombre de séries après l'ajout
            count1 = Serie.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Série enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                  "message": "L'insertion a échouée."}) 
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                    
    context = {
        "setting": setting,
        "contrat": contrat
    }
    return render(request, "add_serie.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_serie(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    serie_id = int(dechiffrer_param(id))
    serie = Serie.objects.get(id=serie_id)
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                    
    context = {
        "setting": setting,
        "serie":serie,
        "contrat": contrat
    }
    return render(request, "edit_serie.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_sr(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id=int(request.POST["id"])
        try:
            serie = Serie.objects.get(id=id)
        except:
            serie = None

        if serie is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Idenfifiant inexistant."})
        else: 
            name = bleach.clean(request.POST["name"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            #On verifie si cette série a déjà été enregistrée
            series = Serie.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabSerie = []
            for s in series:          
                tabSerie.append(s.name)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if name in tabSerie: #On verifie si cette série existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Cette série existe déjà."})
            else:
                serie.name = name
                serie.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Série modifiée avec succès."})


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_serie(request, id):
    try:
        serie_id = int(dechiffrer_param(id))
        serie = Serie.objects.get(id=serie_id)
    except:
        serie = None
        
    if serie:
        # Nombre de séries avant la suppression
        count0 = Serie.objects.all().count()
        serie.delete()
        # Nombre de séries après la suppression
        count1 = Serie.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("series")

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_serie(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    serie_id = int(dechiffrer_param(id))
    serie = Serie.objects.get(id=serie_id)
    nombre = {}
    nombre["nombre_salles"] = Salle.objects.filter(serie_id=serie.id, anneeacademique_id=anneeacademique_id).count()
    
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
    context = {
        "setting": setting,
        "serie": serie,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_serie.html", context)
