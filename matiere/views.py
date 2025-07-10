# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count
# Importation des modules locaux
from .models import*
from programme.models import Programme
from enseignement.models import Enseigner
from composition.models import Composer
from emploi_temps.models import EmploiTemps
from emargement.models import Emargement
from cycle.models import Cycle
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def matieres(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    matieres_groupes = (Matiere.objects.values("cycle_id")
                .filter(anneeacademique_id=anneeacademique_id)
                .annotate(nombre_matieres=Count("cycle_id")))
    matieres = []
    for mg in matieres_groupes:
        dic = {}
        cycle = Cycle.objects.get(id=mg["cycle_id"])
        dic["cycle"] = cycle
        dic["nombre_matieres"] = mg["nombre_matieres"]
        dic["matieres"] = cycle.matieres.all()
        matieres.append(dic)
        
    context = {
        "setting": setting,
        "matieres": matieres,
        "anneeacademique": anneeacademique
    }
    return render(request, "matieres.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_admin)
def matieres_admin(request):
    cycle_id = request.session.get('cycle_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    matieres = Matiere.objects.filter(cycle_id=cycle_id, anneeacademique_id=anneeacademique_id)
    context = {
        "setting": setting,
        "matieres": matieres
    }
    return render(request, "matieres_admin.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_matiere(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        cycle_id = request.POST["cycle"]
        libelle = bleach.clean(request.POST["libelle"].strip())
        abreviation = bleach.clean(request.POST["abreviation"].strip())
        theme = bleach.clean(request.POST["theme"].strip())
        text_color = bleach.clean(request.POST["text_color"].strip())

        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        
        query = Matiere.objects.filter(libelle=libelle, cycle_id=cycle_id, anneeacademique_id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette matière existe déjà."})
        else:
            matiere = Matiere(
                cycle_id = cycle_id,
                libelle=libelle, 
                abreviation=abreviation, 
                theme=theme, 
                text_color=text_color,
                anneeacademique_id=anneeacademique_id)
           # Nombre de matières avant l'ajout
            count0 = Matiere.objects.all().count()
            matiere.save()
            # Nombre de matieres après l'ajout
            count1 = Matiere.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Matière enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})
            
    themes = ['bg-primary', 'bg-info', 'bg-success', 'bg-danger', 'bg-secondary', 'bg-dark', 'bg-light']        
    textcolors = ['text-primary', 'text-info', 'text-success', 'text-danger', 'text-secondary','text-dark', 'text-light']
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id) 
    context = {
        "setting": setting,
        "themes": themes,
        "colors": textcolors,
        "cycles": cycles
    }
    return render(request, "add_matiere.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_matiere(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    matiere_id = int(dechiffrer_param(str(id)))
    matiere = Matiere.objects.get(id=matiere_id)
    themes = ['bg-primary', 'bg-info', 'bg-success', 'bg-danger', 'bg-secondary', 'bg-dark', 'bg-light']  
    tabThemes = []
    for theme in themes:
        if matiere.theme != theme:
            tabThemes.append(theme)
                   
    colors = ['text-primary', 'text-info', 'text-success', 'text-danger', 'text-secondary','text-dark', 'text-light']
    tabColors = []
    for color in colors:
        if matiere.text_color != color:
            tabColors.append(color)
    
    cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=matiere.cycle.id)       
    context = {
        "setting": setting,
        "matiere": matiere,
        "themes": tabThemes,
        "colors": tabColors,
        "cycles": cycles
    }
    return render(request, "edit_matiere.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_mt(request):
    anneeacademique_id=request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            matiere = Matiere.objects.get(id=id)
        except:
            matiere = None

        if matiere == None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            libelle = bleach.clean(request.POST["libelle"].strip())
            abreviation = bleach.clean(request.POST["abreviation"].strip())
            theme = bleach.clean(request.POST["theme"].strip())
            text_color = bleach.clean(request.POST["text_color"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            #On verifie si cette matière a déjà été enregistrée
            matieres = Matiere.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabMatiere = []
            for m in matieres:          
                tabMatiere.append(m.libelle)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
            #On verifie si cette matière existe déjà
            if libelle in tabMatiere:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette matière existe déjà."})
            else:
                matiere.libelle = libelle
                matiere.abreviation = abreviation
                matiere.theme = theme
                matiere.text_color = text_color
                matiere.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Matière modifiée avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_matiere(request, id):
    try:
        matiere_id = int(dechiffrer_param(str(id)))
        matiere = Matiere.objects.get(id=matiere_id)
    except:
        matiere = None
        
    if matiere:
        # Nombre de matières avant la suppression
        count0 = Matiere.objects.all().count()
        matiere.delete()
        # Nombre de matières après la suppression
        count1 = Matiere.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("matieres")

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_matiere(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    matiere_id = int(dechiffrer_param(str(id)))
    matiere = Matiere.objects.get(id=matiere_id)
    nombre = {}
    nombre["nombre_programmes"] = Programme.objects.filter(matiere_id=matiere.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_enseignements"] = Enseigner.objects.filter(matiere_id=matiere.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_emargements"] = Emargement.objects.filter(matiere_id=matiere.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_emploitemps"] = EmploiTemps.objects.filter(matiere_id=matiere.id, anneeacademique_id=anneeacademique_id).count()
    nombre["nombre_compositions"] = Composer.objects.filter(matiere_id=matiere.id, anneeacademique_id=anneeacademique_id).count()
    
    nombre_total = len(nombre)
    context = {
        "setting": setting,
        "matiere": matiere,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_matiere.html", context)
