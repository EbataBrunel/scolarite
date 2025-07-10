# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from datetime import datetime
from django.contrib import messages
# Importation des modules locaux
from .models import*
from school.views import get_setting
from scolarite.utils.crypto import dechiffrer_param

@login_required(login_url='connection/connexion')
def trimestres(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        liste_trimestres = Trimestre.objects.filter(anneeacademique_id=anneeacademique_id)
        trimestres = []
        for trimestre in liste_trimestres:
            dic = {}
            dic["trimestre"] = trimestre
            dic["evenements"] = trimestre.evenementscolaires.all()            
            trimestres.append(dic)
        
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)    
        context = {
            "trimestres": trimestres,
            "anneeacademique": anneeacademique,
            "setting": setting
        }
        return render(request, "trimestre/trimestres.html", context=context)

@login_required(login_url='connection/connexion')
def add_trimestre(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        
            name = bleach.clean(request.POST["name"].strip())
            start_date = request.POST["start_date"]
            end_date = request.POST["end_date"]
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)        
            query = Trimestre.objects.filter(name=name, anneeacademique_id=anneeacademique_id)
            # Recuperer l'année academique
            anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
            date_d = datetime.strptime(start_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            date_f = datetime.strptime(end_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if anneeacademique.start_date <= date_d and date_f <= anneeacademique.end_date:
                if start_date > end_date:
                    return JsonResponse({
                        "status": "error",
                        "message": "La date du début doit être inférieure à la date de fin."})
                if query.exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce trimestre existe déjà."})
                else:
                        
                    trimestre = Trimestre(
                        name=name, 
                        start_date=start_date, 
                        end_date=end_date, 
                        anneeacademique_id=anneeacademique_id
                    )
                    # Nombre de trimestre avant l'ajout
                    count0 = Trimestre.objects.all().count()
                    trimestre.save()
                    # Nombre de trimestre après l'ajout
                    count1 = Trimestre.objects.all().count()
                    # On verifie si l'insertion a eu lieu ou pas.
                    if count0 < count1:
                        return JsonResponse({
                            "status": "success",
                            "message": "Trimestre enregistré avec succès."})
                    else:
                        return JsonResponse({
                            "status": "error",
                            "message": "L'insertion a échoué."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin du trimestre doivent situer dans la date du début et de fin de l'année scolaire ."})
            
    names = ["Trimestre 1", "Trimestre 2", "Trimestre 3"]           
    context = {
        "setting": setting,
        "names": names
    }
    return render(request, "trimestre/add_trimestre.html", context)

@login_required(login_url='connection/connexion')
def edit_trimestre(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    trimestre = Trimestre.objects.get(id=user_id)
    names = ["Trimestre 1", "Trimestre 2", "Trimestre 3"] 
    tabnames = []
    for name in names:
        if name != trimestre.name:
            tabnames.append(name)
        
    context = {
        "trimestre": trimestre,
        "names": tabnames,
        "setting": setting
    }
    return render(request, "trimestre/edit_trimestre.html", context)

@login_required(login_url='connection/connexion')
def edit_tr(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            trimestre = Trimestre.objects.get(id=id)
        except:
            trimestre = None

        if trimestre is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            
            name = bleach.clean(request.POST["name"].strip())
            start_date = request.POST["start_date"]
            end_date = request.POST["end_date"]
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)  
            # Recuperer l'année academique
            anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
            date_d = datetime.strptime(start_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            date_f = datetime.strptime(end_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if anneeacademique.start_date <= date_d and date_f <= anneeacademique.end_date:
                #On verifie l'exitence du trimestre
                trimestres = Trimestre.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
                tabTrimestre = []
                for t in trimestres:          
                    tabTrimestre.append(t.name)
                    
                if start_date > end_date:
                    return JsonResponse({
                        "status": "error",
                        "message": "La date du début doit être inférieure à la date de fin."})

                if name in tabTrimestre: #On verifie si ce trimestre existe déjà
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce trimestre existe déjà."})
                else:
                    trimestre.name = name
                    trimestre.start_date = start_date
                    trimestre.end_date = end_date
                    trimestre.save()
                    return JsonResponse({
                        "status": "success",
                        "message": "Trimestre modifié avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin du trimestre doivent situer entre la date du début et de fin de l'année scolaire ."})

@login_required(login_url='connection/connexion')
def del_trimestre(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        try:
            user_id = int(dechiffrer_param(str(id)))
            trimestre = Trimestre.objects.get(id=user_id)
        except:
            trimestre = None
            
        if trimestre:
            # Nombre de trimestres avant la suppression
            count0 = Trimestre.objects.all().count()
            trimestre.delete()
            # Nombre de trimestres après la suppression
            count1 = Trimestre.objects.all().count()
            if count1 < count0: 
                messages.success(request, "ELément supprimé avec succès.")
            else:
                messages.error(request, "La suppression a échouée.")
        return redirect("trimestre/trimestres")
    
#================================== Gestion des evenements ==================================   
@login_required(login_url='connection/connexion')
def evenements(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    evenements_groupes = (EvenementScolaire.objects.values("trimestre_id")
                        .annotate(nombre_evenements=Count("trimestre_id"))
    )
    evenements = []
    for eg in evenements_groupes:        
        trimestre = Trimestre.objects.get(id=eg["trimestre_id"])
        if trimestre.anneeacademique.id == anneeacademique_id:
            dic = {}
            dic["trimestre"] = trimestre
            dic["nombre_evenements"] = eg["nombre_evenements"]   
            dic["evenements"] = trimestre.evenementscolaires.all()         
            evenements.append(dic)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)   
    context = {
        "evenements": evenements,
        "anneeacademique": anneeacademique,
        "setting": setting
    }
    return render(request, "evenement/evenements.html", context=context)

@login_required(login_url='connection/connexion')
def add_evenement(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        try:
            trimestre_id = request.POST["trimestre"]
            name = bleach.clean(request.POST["name"].strip())
            description = bleach.clean(request.POST["description"].strip())
            start_date = request.POST["start_date"]
            end_date = request.POST["end_date"]
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
            # Recuperer le trimestre
            trimestre = Trimestre.objects.get(id=trimestre_id)
            date_d = datetime.strptime(start_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            date_f = datetime.strptime(end_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont sdéjà été clôturées."})
            if trimestre.start_date <= date_d and date_f <= trimestre.end_date:
                query = EvenementScolaire.objects.filter(name=name, trimestre_id=trimestre_id)
                if query.exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce évènement existe déjà."})
                else:
                        
                    evenement = EvenementScolaire(
                        trimestre_id=trimestre_id,
                        name=name, 
                        description=description, 
                        start_date=start_date, 
                        end_date=end_date
                    )
                    # Nombre de trimestre avant l'ajout
                    count0 = EvenementScolaire.objects.all().count()
                    evenement.save()
                    # Nombre de trimestre après l'ajout
                    count1 = EvenementScolaire.objects.all().count()
                    # On verifie si l'insertion a eu lieu ou pas.
                    if count0 < count1:
                        return JsonResponse({
                            "status": "success",
                            "message": "Evènement enregistré avec succès."})
                    else:
                        return JsonResponse({
                            "status": "error",
                            "message": "L'insertion à échouée."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin de l'évènement doivent situer entre la date du début et de fin du trimestre ."})
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
    trimestres = Trimestre.objects.filter(anneeacademique_id=anneeacademique_id)        
    context = {
        "setting": setting,
        "trimestres": trimestres
    }
    return render(request, "evenement/add_evenement.html", context)

@login_required(login_url='connection/connexion')
def edit_evenement(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = int(dechiffrer_param(str(id)))
    evenement = EvenementScolaire.objects.get(id=user_id)
    
    trimestres = Trimestre.objects.filter(anneeacademique_id=anneeacademique_id)
    tabTrimestre = []
    for trimestre in trimestres:
        if trimestre != evenement.trimestre:
            tabTrimestre.append(trimestre)
            
    context = {
        "evenement": evenement,
        "trimestres": tabTrimestre,
        "setting": setting
    }
    return render(request, "evenement/edit_evenement.html", context)

@login_required(login_url='connection/connexion')
def edit_ev(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            evenement = EvenementScolaire.objects.get(id=id)
        except:
            evenement = None

        if evenement is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            trimestre_id = request.POST["trimestre"]
            name = bleach.clean(request.POST["name"].strip())
            start_date = request.POST["start_date"]
            end_date = request.POST["end_date"]
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
            # Recuperer le trimestre
            trimestre = Trimestre.objects.get(id=trimestre_id)
            date_d = datetime.strptime(start_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            date_f = datetime.strptime(end_date, "%Y-%m-%d").date() # Conversion de la date début (str) en date
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})
            if trimestre.start_date <= date_d and date_f <= trimestre.end_date:
                #On verifie l'exitence de l'evenement
                evenements = EvenementScolaire.objects.exclude(id=id)
                tabEvenement = []
                for e in evenements: 
                    if e.trimestre.anneeacademique.id == anneeacademique_id:
                        dic = {}
                        dic["name"] = e.name
                        dic["trimestre_id"] = e.trimestre.id         
                        tabEvenement.append(dic)
                    
                new_dic = {}
                new_dic["name"] = name
                new_dic["trimestre_id"] = trimestre_id
                #On verifie si cet evenement existe déjà
                if new_dic in tabEvenement:
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce évènement existe déjà."})
                else:
                    evenement.trimestre_id = trimestre_id
                    evenement.name = name
                    evenement.start_date = start_date
                    evenement.end_date = end_date
                    evenement.save()
                    return JsonResponse({
                        "status": "success",
                        "message": "Evènement modifié avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "La date du début et de fin de l'évènement doivent situer entre la date du début et de fin du trimestre ."})

@login_required(login_url='connection/connexion')
def del_evenement(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        try:
            user_id = int(dechiffrer_param(str(id)))
            evenement = EvenementScolaire.objects.get(id=user_id)
        except:
            evenement = None
            
        if evenement:
            # Nombre d'evènements avant la suppression
            count0 = EvenementScolaire.objects.all().count()
            evenement.delete()
            # Nombre d'evènements après la suppression
            count1 = EvenementScolaire.objects.all().count()
            if count1 < count0: 
                messages.success(request, "ELément supprimé avec succès.")
            else:
                messages.error(request, "La suppression a échouée.")
            return redirect("evenement/evenements")
        
def ajax_delete_evenement(request, id):
    evenement = EvenementScolaire.objects.get(id=id)
    context = {
        "evenement": evenement
    }
    return render(request, "ajax_delete_evenement.html", context)
    

