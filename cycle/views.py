# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
# Importation des modules locaux
from .models import*
from classe.models import Classe
from paiement.models import ContratEtablissement
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def cycles(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "cycles": cycles,
        "anneeacademique": anneeacademique
    }
    return render(request, "cycles.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def cycles_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id)
    context = {
        "setting": setting,
        "cycles": cycles
    }
    return render(request, "cycles_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_cycle(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        libelle = bleach.clean(request.POST["libelle"].strip())

        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        
        query = Cycle.objects.filter(libelle=libelle, etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce cycle existe déjà."})
        else:
            cycle = Cycle(
                libelle=libelle, 
                etablissement_id=etablissement_id,
                anneeacademique_id=anneeacademique_id)
           # Nombre de cycles avant l'ajout
            count0 = Cycle.objects.all().count()
            cycle.save()
            # Nombre de cycles après l'ajout
            count1 = Cycle.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Cycle enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})
    libelles = ['Prescolaire', 'Primaire', 'Collège', 'Lycée']   
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()    
    context = {
        "setting": setting,
        "libelles": libelles,
        "contrat": contrat
    }
    return render(request, "add_cycle.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_cycle(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cycle_id = int(dechiffrer_param(str(id)))
    cycle = Cycle.objects.get(id=cycle_id)
    libelles = ['Prescolaire', 'Primaire', 'Collège', 'Lycée']  
    tabLibelles = [libelle for libelle in libelles if libelle != cycle.libelle]
    
    # Récuperer l'année académique de l'établissement
    anneeacademique_etablissement = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique de l'année académique
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique_etablissement.annee_debut, annee_fin=anneeacademique_etablissement.annee_fin, etablissement=None).first()
    contrat = ContratEtablissement.objects.filter(anneeacademique=anneeacademique_group, etablissement=anneeacademique_etablissement.etablissement).first()                    
    context = {
        "setting": setting,
        "cycle": cycle,
        "libelles": tabLibelles,
        "contrat": contrat
    }
    return render(request, "edit_cycle.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_cy(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id=request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            cycle = Cycle.objects.get(id=id)
        except:
            cycle = None

        if cycle is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            libelle = bleach.clean(request.POST["libelle"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            #On verifie si ce cycle a déjà été enregistrée
            cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id, etablissement_id=etablissement_id).exclude(id=id)
            tabCycles = []
            for c in cycles:          
                tabCycles.append(c.libelle)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
            #On verifie si ce cycle existe déjà
            if cycle in tabCycles:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce cycle existe déjà."})
            else:
                cycle.libelle = libelle
                cycle.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Cycle modifié avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_cycle(request,id):
    try:
        cycle_id = int(dechiffrer_param(str(id)))
        cycle = Cycle.objects.get(id=cycle_id)
    except:
        cycle = None
        
    if cycle:
        # Nombre de cycles avant la suppression
        count0 = Cycle.objects.all().count()
        cycle.delete()
        # Nombre de cycles après la suppression
        count1 = Cycle.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("cycles")


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_cycle(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    cycle_id = int(dechiffrer_param(str(id)))
    cycle = Cycle.objects.get(id=cycle_id)
    nombre = {}
    nombre["nombre_classes"] = Classe.objects.filter(cycle_id=cycle.id, anneeacademique_id=anneeacademique_id).count()
    
    nombre_total = len(nombre)
    context = {
        "setting": setting,
        "cycle": cycle,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_cycle.html", context)
