# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Count
from django.contrib import messages
# Importation des modules locaux
from app_auth.decorator import unauthenticated_customer
from .models import Activity
from anneeacademique.models import AnneeCademique
from school.views import get_setting
from scolarite.utils.crypto import dechiffrer_param


@login_required(login_url='connection/connexion')
def activities(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")   
    
    types_activities = (Activity.objects.values('type')
                  .filter(anneeacademique_id=anneeacademique_id)
                  .annotate(nb_activities=Count('type')))
    
    activities= []
    for activity in types_activities:
        dic = {}
        dic["type"] = activity["type"]
        dic["nb_activities"] = activity["nb_activities"]
        activities.append(activity)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "activities": activities,
        "anneeacademique": anneeacademique
    }
    return render(request, "activities.html", context=context)
        
@login_required(login_url='connection/connexion')
def detail_activity(request, type):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    type_crypt = dechiffrer_param(type)
    activities = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type=type_crypt).order_by('-id')
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "activities": activities,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_activity.html", context=context)
    
@login_required(login_url='connection/connexion')
def add_activity(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        user_id = request.user.id
        
        type = bleach.clean(request.POST["type"].strip())
        content = bleach.clean(request.POST["content"].strip()) 
        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
        else:
            activity = Activity(
                type=type,
                content=content,
                anneeacademique_id=anneeacademique_id,
                user_id=user_id)
                    
            count0 = Activity.objects.all().count()
            activity.save()
            count1 = Activity.objects.all().count()
            # Verifier si l'ajout a été bien effectué ou pas
            if count0 < count1:
                return JsonResponse({
                        "status": "success",
                        "message": "Activité enregistrée avec succès."})
            else:
                return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
                
    context = {
        "setting": setting
    }
    return render(request, "add_activity.html", context)
                
                
@login_required(login_url='connection/connexion')
def edit_activity(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    activity_id = int(dechiffrer_param(str(id)))
    activity = Activity.objects.get(id=activity_id)   
    
    context = {
        "setting": setting,
        "activity": activity
    }
    return render(request, "edit_activity.html", context)


@login_required(login_url='connection/connexion')
def edit_ac(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            activity = Activity.objects.get(id=id)
        except:
            activity = None
        
        if activity:
            type = bleach.clean(request.POST["type"].strip())
            content = bleach.clean(request.POST["content"].strip())
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)   
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
            else:
                activity.type = type
                activity.content = content

                activity.save()
                return JsonResponse({
                        "status": "success",
                        "message": "Activité modifiée avec succès."})

@login_required(login_url='connection/connexion')     
def del_activity(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    activity_id = int(dechiffrer_param(str(id))) 
    activity = Activity.objects.get(id=activity_id)
    # Nombre d'activités avant la suppression
    count0 = Activity.objects.all().count()
    activity.delete()
    # Nombre d'activités après la suppression
    count1 = Activity.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Elément supprimé avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("activities")


@unauthenticated_customer
def activity_student(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    # Récuperer les activités
    activities = Activity.objects.filter(anneeacademique_id=anneeacademique_id, type="Publique").order_by('-id')[:6]
    tabActivities = []
    i = 0
    for activity in activities:
        i += 1
        dic = {}
        dic["activity"] = activity
        dic["i"] = i
        tabActivities.append(dic)
        
    context = {
        "setting": setting,
        "activities": tabActivities
    }
    return render(request, "activity_student.html", context)


