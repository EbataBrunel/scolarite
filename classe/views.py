# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count
# Importation des modules locaux
from .models import Classe
from salle.models import Salle
from anneeacademique.models import AnneeCademique
from cycle.models import Cycle
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_promoteur_DG = ['Promoteur', 'Directeur Général']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def classes(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classes_groupes = (Classe.objects.values("cycle_id")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nombre_classes=Count("cycle_id"))
    )
    classes = []
    for cg in classes_groupes:
        dic = {}
        cycle = Cycle.objects.get(id=cg["cycle_id"])
        dic["cycle"] = cycle
        dic["nombre_classes"] = cg["nombre_classes"]
        dic["classes"] = cycle.classes.all()
        classes.append(dic)
        
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "classes": classes,
        "anneeacademique": anneeacademique,
        "setting": setting
    }
    return render(request, "classes.html", context=context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def add_class(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        if request.method == "POST":
            cycle_id = request.POST["cycle"]
            libelle = bleach.clean(request.POST["libelle"].strip())
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)           
            query = Classe.objects.filter(libelle=libelle, anneeacademique_id=anneeacademique_id)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if query.exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cette classe existe déjà."})
            else:
                
                classe = Classe(libelle=libelle, cycle_id=cycle_id, anneeacademique_id=anneeacademique_id)
                # Nombre de classes avant l'ajout
                count0 = Classe.objects.all().count()
                classe.save()
                # Nombre de classes après l'ajout
                count1 = Classe.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Classe ajoutée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
        
        cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id)    
        context = {
            "setting": setting,
            "cycles": cycles
        }
        return render(request, "add_class.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_class(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        classe_id = int(dechiffrer_param(str(id)))
        
        classe = Classe.objects.get(id=classe_id)
        
        cycles = Cycle.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=classe.cycle.id)       
        context = {
            "classe": classe,
            "cycles": cycles,
            "setting": setting
        }
        return render(request, "edit_class.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def edit_cl(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            classe = Classe.objects.get(id=id)
        except:
            classe = None

        if classe is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            libelle = bleach.clean(request.POST["libelle"].strip())
            
            # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            #On verifie si cette classe a été déjà enregistrée
            classes = Classe.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabClasse = []
            for c in classes:          
                tabClasse.append(c.libelle)
                
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if libelle in tabClasse: #On verifie si cette classe existe déjà
                return JsonResponse({
                    "status": "error",
                    "message": "Cette classe existe déjà."})
            else:
                classe.libelle = libelle
                classe.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Classe enregistrée avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def del_class(request, id):
    try:
        classe_id = int(dechiffrer_param(str(id)))
        classe = Classe.objects.get(id=classe_id)
    except:
        classe = None
           
    if classe:
        # Nombre de classes avant la suppression
        count0 = Classe.objects.all().count()
        classe.delete()
        # Nombre de classes après la suppression
        count1 = Classe.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("classes")

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def delete_classe(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = int(dechiffrer_param(str(id)))
    classe = Classe.objects.get(id=classe_id)  
    nombre = {}
    nombre["nombre_salles"] = Salle.objects.filter(classe_id=classe.id, anneeacademique_id=anneeacademique_id).count()
    nombre_total = 0
    for valeur in nombre.values():
        if valeur != 0:
            nombre_total += valeur
            
    context = {
        "setting": setting,
        "classe": classe,
        "nombre_total": nombre_total,
        "nombre": nombre
    }
    return render(request, "delete_classe.html", context)

