# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from django.contrib import messages
# Importation locaux
from .models import*
from school.views import get_setting
from scolarite.utils.crypto import dechiffrer_param

@login_required(login_url='connection/login')
def programmes(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    classe_id = request.session.get('classe_id')
    salles = Programme.objects.values("salle_id").filter(anneeacademique_id=anneeacademique_id).annotate(effectif=Count("salle_id"))
    tabProgramme = []
    for salle in salles:
        s = Salle.objects.get(id=salle["salle_id"])   
        if s.classe.id == classe_id:
            dic = {}
            dic["salle"] = s
            dic["effectif"] = salle["effectif"]
            tabProgramme.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "programmes": tabProgramme,
        "anneeacademique": anneeacademique
    }
    return render(request, "programmes.html", context)


@login_required(login_url='connection/login')
def detail_programme(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle_id = int(dechiffrer_param(str(id)))  
    salle = Salle.objects.get(id=salle_id)
    programmes = Programme.objects.filter(salle_id=salle_id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)    
    context = {
        "setting": setting,
        "programmes": programmes,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_programme.html", context)
    

@login_required(login_url='connection/login')
def add_programme(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle_id = request.session.get('cycle_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    
    if request.method == "POST":

        salle_id = request.POST["salle"]
        matiere_id = request.POST["matiere"]
        coefficient = bleach.clean(request.POST["coefficient"].strip())
        # Récuperer l'année académique pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
           
        query = Programme.objects.filter(salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
        if query.exists():
            return JsonResponse({
                "status": "error",
                "message": "Ce programme existe déjà."})
        else:
            programme = Programme(salle_id=salle_id, matiere_id=matiere_id, coefficient=coefficient, anneeacademique_id=anneeacademique_id)
            # Nombre de programmes avant l'ajout
            count0 = Programme.objects.all().count()
            programme.save()
            # Nombre de programmes après l'ajout
            count1 = Programme.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Programme enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."}) 

    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    matieres = Matiere.objects.filter(cycle_id=cycle_id, anneeacademique_id=anneeacademique_id)

    context={
        "setting": setting,
        "salles": salles,
        "matieres":matieres
    }
    return render(request, "add_programme.html", context)


@login_required(login_url='connection/login')
def edit_programme(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle_id = request.session.get('cycle_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    programme_id = int(dechiffrer_param(str(id)))
    programme = Programme.objects.get(id=programme_id)
        
    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id).exclude(id=programme.salle.id)
    matieres = Matiere.objects.filter(cycle_id=cycle_id, anneeacademique_id=anneeacademique_id).exclude(id=programme.matiere.id)

    context = {
        "setting": setting,
        "programme": programme,
        "salles": salles,
        "matieres": matieres
    }
    return render(request, "edit_programme.html", context)
   

@login_required(login_url='connection/login')
def edit_pg(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            programme = Programme.objects.get(id=id)
        except:
            programme = None

        if programme is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            salle_id = request.POST["salle"]
            matiere_id = request.POST["matiere"]
            coefficient = bleach.clean(request.POST["coefficient"].strip())
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            # Vérifier l'existence du programme
            programmes = Programme.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabProgramme = []
            for p in programmes:   
                dic = {}
                dic["salle_id"] = p.salle.id
                dic["matiere_id"] = p.matiere.id
                tabProgramme.append(dic)
                
            
                
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["matiere_id"] = int(matiere_id)
            
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
             # Vérifier l'existence du programme
            if new_dic in tabProgramme:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce programme existe déjà."})
            else:
                programme.salle_id = salle_id
                programme.matiere_id = matiere_id
                programme.coefficient = coefficient
                programme.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Programme modifié avec succès."})


@login_required(login_url='connection/login')
def del_programme(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    programme_id = int(dechiffrer_param(str(id)))
    programme = Programme.objects.get(id=programme_id)
    # Nombre de programmes avant la suppression
    count0 = Programme.objects.all().count()
    programme.delete()
    # Nombre de programmes après la suppression
    count1 = Programme.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Elément supprimé avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("detail_programme", programme.salle.id)
