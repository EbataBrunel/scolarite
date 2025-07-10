# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from django.views import View
from django.db.models import Min
from django.contrib import messages 
# Importation locaux
from .models import *
from programme.models import Programme
from inscription.models import Inscription
from enseignement.models import Enseigner
from app_auth.models import Student, Profile
from etablissement.models import Etablissement
from school.views import get_setting
from app_auth.decorator import unauthenticated_customer, allowed_users
from scolarite.utils.crypto import dechiffrer_param

permission_directeur_etudes = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Super user']
permission_directeur_etudes_enseignant = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Enseignant', 'Super user',]
permission_enseignant = ['Enseignant', 'Super user']


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes_enseignant)
def emploitemps(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    classe_id = request.session.get('classe_id')
    tabSalles = []
    if request.user.is_superuser:   
        salles_enseignements = (Enseigner.objects.values("salle_id")
                         .filter(anneeacademique_id=anneeacademique_id)    
                         .annotate(nb_salles=Count("salle_id")))
        for se in salles_enseignements:
            salle = Salle.objects.get(id=se["salle_id"])
            if salle.classe.id == classe_id:
                tabSalles.append(salle)
    else:
        # Recuperer toutes les salles de l'enseignant
        salles_enseignements = (Enseigner.objects.values('salle_id')
                         .filter(enseignant_id=request.user.id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_salles=Count("salle_id")))

        for se in salles_enseignements:
            salle = Salle.objects.get(id=se["salle_id"])
            tabSalles.append(salle)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)      
    context = {
        "salles": tabSalles,
        "anneeacademique": anneeacademique,
        "permission": permission_directeur_etudes,
        "setting": setting
    }
    return render(request, "emploitemps.html", context)

unauthenticated_customer
def emploitemps_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    parent_id = request.session.get('parent_id')
    # Récuperer les enfants du parent
    students = Student.objects.filter(parent_id=parent_id) 
    # Selectionner les enfants du parent qui sont inscris cette année
    tabinscription = []
    for student in students:
        query = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id)
        if query.exists():
            # Récuperer l'inscription
            inscription = query.first()
            dic = {}
            dic["inscription"] = inscription
            tabinscription.append(dic)
    
    context = {
        "inscriptions": tabinscription,
        "setting": setting
    }
    return render(request, "emploitemps_parent.html", context)

@unauthenticated_customer
def emploitemps_student(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = request.session.get('student_id')
    inscription = Inscription.objects.filter(student_id=student_id).first()
    heures_emploitemps = (EmploiTemps.objects.values('heure_debut','heure_fin').filter(salle_id=inscription.salle.id, anneeacademique_id=anneeacademique_id)
                        .annotate(heure_debut_min=Min('heure_debut'))
                        .order_by('heure_debut'))
        
    tabHeure_emploitemps = []
    for heure in heures_emploitemps:
            dic = {}
            emploitemps = EmploiTemps.objects.filter(heure_debut = heure["heure_debut"], heure_fin=heure["heure_fin"]).select_related("enseignant")
            for emploi in emploitemps:
                dic["horaire"] = f"{emploi.heure_debut.strftime('%H:%M')} - {emploi.heure_fin.strftime('%H:%M')}"
                if emploi.jour == "Lundi":
                    dic["lundi"] = emploi
                elif emploi.jour == "Mardi":
                    dic["mardi"] = emploi
                elif emploi.jour == "Mercredi":
                    dic["mercredi"] = emploi
                elif emploi.jour == "Jeudi":
                    dic["jeudi"] = emploi
                elif emploi.jour == "Vendredi":
                    dic["vendredi"] = emploi
                elif emploi.jour == "Samedi":
                    dic["samedi"] = emploi
                else:
                    dic["dimanche"] = emploi
                    
            tabHeure_emploitemps.append(dic)  
            
    count_emploi_samedi = EmploiTemps.objects.filter(salle_id=inscription.salle.id, anneeacademique_id=anneeacademique_id, jour="Samedi").count()
    count_emploi_dimanche = EmploiTemps.objects.filter(salle_id=inscription.salle.id, anneeacademique_id=anneeacademique_id, jour="Dimanche").count() 
                
    context = {
        "emploitemps": tabHeure_emploitemps,
        "count_emploi_samedi": count_emploi_samedi,
        "count_emploi_dimanche": count_emploi_dimanche,
        "setting": setting
    }
        
    return render(request, "emploitemps_student.html", context=context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def add_emploitemps(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    
    if request.method == "POST":

        salle_id = request.POST["salle"]
        matiere_id = request.POST["matiere"]
        enseignant_id = request.POST["enseignant"]
        jour = request.POST["jour"]
        heure_debut = request.POST["heure_debut"]
        heure_fin = request.POST["heure_fin"]
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
           
        query = EmploiTemps.objects.filter(
            salle_id=salle_id, 
            matiere_id=matiere_id, 
            anneeacademique_id=anneeacademique_id,
            jour=jour, 
            heure_debut=heure_debut, 
            heure_fin=heure_fin
        )
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet emploi du temps existe déjà."})
        else:
            emploitemps = EmploiTemps(
                salle_id=salle_id, 
                matiere_id=matiere_id, 
                anneeacademique_id=anneeacademique_id,
                enseignant_id=enseignant_id,
                jour=jour,
                heure_debut=heure_debut,
                heure_fin=heure_fin
            )
            # Nombre de programmes avant l'ajout
            count0 = EmploiTemps.objects.all().count()
            emploitemps.save()
            # Nombre de programmes après l'ajout
            count1 = EmploiTemps.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                        "status": "success",
                        "message": "Emploi du temps enregistré avec succès."})
            else:
                return JsonResponse({
                        "status": "error",
                        "message": "L'opération a échouée."}) 

    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    salles = Salle.objects.filter(classe_id=classe_id)

    context = {
        "setting": setting,
        "salles": salles,
        "jours": jours
    }
    return render(request, "add_emploitemps.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_emploitemps(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    etablissement_id = request.session.get('etablissement_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    emploitemps_id = int(dechiffrer_param(str(id)))
    emploitemps = EmploiTemps.objects.get(id=emploitemps_id)
        
    salles = Salle.objects.filter(classe_id=classe_id).exclude(id=emploitemps.salle.id)
    enseignements = Enseigner.objects.filter(enseignant_id=emploitemps.enseignant.id, salle_id=emploitemps.salle.id).exclude(id=emploitemps.matiere.id)
    matieres = []
    for enseignement in enseignements:
        matieres.append(enseignement.matiere)
        
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    tabJours = []
    for jour in jours:
        if jour != emploitemps.jour:
            tabJours.append(jour)

    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    enseignants = []
                   
    users = User.objects.all()                
    for user in users:
        if emploitemps.enseignant != user:
            groups = etablissement.groups.filter(user=user)
            for group in groups:
                if group.name == "Enseignant":
                    enseignants.append(user)
                    break
           
    context = {
        "setting": setting,
        "emploitemps": emploitemps,
        "salles": salles,
        "matieres": matieres,
        "enseignants": enseignants,
        "jours": tabJours
    }
    return render(request, "edit_emploitemps.html", context)
   
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_emp(request):
   
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            emploitemps = EmploiTemps.objects.get(id=id)
        except:
            emploitemps = None

        if emploitemps is None:
            return JsonResponse({'status':1})
        else: 
            salle_id = request.POST["salle"]
            matiere_id = request.POST["matiere"]
            enseignant_id = request.POST["enseignant"]
            jour = request.POST["jour"]
            heure_debut = request.POST["heure_debut"]
            heure_fin = request.POST["heure_fin"]

            anneeacademique_id = request.session.get('anneeacademique_id')
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            # Vérifier l'existence du programme
            list_emploitemps = EmploiTemps.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabEmploitemps = []
            for emp in list_emploitemps:   
                dic = {}
                dic["salle_id"] = emp.salle.id
                dic["matiere_id"] = emp.matiere.id
                dic["enseignant_id"] = emp.enseignant.id
                dic["jour"] = emp.jour
                dic["heure_debut"] = emp.heure_debut
                dic["heure_fin"] = emp.heure_fin
                tabEmploitemps.append(dic)
                
            
                
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["matiere_id"] = int(matiere_id)
            new_dic["enseignant_id"] = int(enseignant_id)
            new_dic["jour"] = jour
            new_dic["heure_debut"] = heure_debut
            new_dic["heure_fin"] = heure_fin

            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
            if new_dic in tabEmploitemps: # Vérifier l'existence de l'emploi du temps
                return JsonResponse({
                        "status": "error",
                        "message": "Cet emploi du temps existe déjà."})
            else:
                emploitemps.salle_id = salle_id
                emploitemps.matiere_id = matiere_id
                emploitemps.enseignant_id = enseignant_id
                emploitemps.jour = jour
                emploitemps.heure_debut = heure_debut
                emploitemps.heure_fin = heure_fin
                emploitemps.save()
                return JsonResponse({
                        "status": "success",
                        "message": "Emploi du temps enregistrée avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def del_emploitemps(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        emploitemps_id = int(dechiffrer_param(str(id)))
        emploitemps = EmploiTemps.objects.get(id=emploitemps_id)
    except:
        emploitemps = None
        
    if emploitemps:
        # Nombre d'emploi de temps avant la suppression
        count0 = EmploiTemps.objects.all().count()
        emploitemps.delete()
        # Nombre d'emploi de temps après la suppression
        count1 = EmploiTemps.objects.all().count()
        if count1 < count0: 
            messages.success(request, "ELément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("emploitemps")

    
class get_enseignant_salle_emploi(View):
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        enseignements = Enseigner.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id)
        enseignants = []
        for enseignement in enseignements:
            if enseignement.enseignant not in enseignants:
                enseignants.append(enseignement.enseignant)

        context={
            "enseignants": enseignants
        }
        return render(request, "ajax_enseignant.html", context)
    
class get_matiere_enseignant_salle_emploi(View):
    def get(self, request, salle_id, enseignant_id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        enseignements = Enseigner.objects.filter(salle_id=salle_id, enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id)
        matieres = []
        for enseignement in enseignements:
            matieres.append(enseignement.matiere)

        context = {
            "matieres": matieres
        }
        return render(request, "ajax_matiere_enseignant.html", context)

class content_emploitemps(View):  
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        setting = get_setting(anneeacademique_id)
        heures_emploitemps = (EmploiTemps.objects.values('heure_debut','heure_fin').filter(salle_id=id, anneeacademique_id=anneeacademique_id)
                        .annotate(heure_debut_min=Min('heure_debut'))
                        .order_by('heure_debut'))
        
        tabHeure_emploitemps = []
        for heure in heures_emploitemps:
            dic = {}
            emploitemps = EmploiTemps.objects.filter(heure_debut = heure["heure_debut"], heure_fin=heure["heure_fin"]).select_related("enseignant")
            for emploi in emploitemps:
                dic["horaire"] = f"{emploi.heure_debut.strftime('%H:%M')}-{emploi.heure_fin.strftime('%H:%M')}"
                if emploi.jour == "Lundi":
                    dic["lundi"] = emploi
                elif emploi.jour == "Mardi":
                    dic["mardi"] = emploi
                elif emploi.jour == "Mercredi":
                    dic["mercredi"] = emploi
                elif emploi.jour == "Jeudi":
                    dic["jeudi"] = emploi
                elif emploi.jour == "Vendredi":
                    dic["vendredi"] = emploi
                elif emploi.jour == "Samedi":
                    dic["samedi"] = emploi
                else:
                    dic["dimanche"] = emploi
                    
            tabHeure_emploitemps.append(dic)  
            
        count_emploi_samedi = EmploiTemps.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id, jour="Samedi").count()
        count_emploi_dimanche = EmploiTemps.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id, jour="Dimanche").count() 
         
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
        context = {
            "emploitemps": tabHeure_emploitemps,
            "count_emploi_samedi": count_emploi_samedi,
            "count_emploi_dimanche": count_emploi_dimanche,
            "permission_directeur_etudes": permission_directeur_etudes,
            "anneeacademique": anneeacademique,
            "setting": setting
        }
        
        return render(request, "content_emploitemps.html", context)
    
    
class content_emploitemps_parent(View):  
    def get(self, request, id, *args, **kwargs):       
        
        anneeacademique_id = request.session.get('anneeacademique_id')
    
        heures_emploitemps = (EmploiTemps.objects.values('heure_debut','heure_fin').filter(salle_id=id, anneeacademique_id=anneeacademique_id)
                            .annotate(heure_debut_min=Min('heure_debut'))
                            .order_by('heure_debut'))
            
        tabHeure_emploitemps = []
        for heure in heures_emploitemps:
                dic = {}
                emploitemps = EmploiTemps.objects.filter(heure_debut = heure["heure_debut"], heure_fin=heure["heure_fin"]).select_related("enseignant")
                for emploi in emploitemps:
                    dic["horaire"] = f"{emploi.heure_debut.strftime('%H:%M')}-{emploi.heure_fin.strftime('%H:%M')}"
                    if emploi.jour == "Lundi":
                        dic["lundi"] = emploi
                    elif emploi.jour == "Mardi":
                        dic["mardi"] = emploi
                    elif emploi.jour == "Mercredi":
                        dic["mercredi"] = emploi
                    elif emploi.jour == "Jeudi":
                        dic["jeudi"] = emploi
                    elif emploi.jour == "Vendredi":
                        dic["vendredi"] = emploi
                    elif emploi.jour == "Samedi":
                        dic["samedi"] = emploi
                    else:
                        dic["dimanche"] = emploi
                        
                tabHeure_emploitemps.append(dic)  
                
        count_emploi_samedi = EmploiTemps.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id, jour="Samedi").count()
        count_emploi_dimanche = EmploiTemps.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id, jour="Dimanche").count() 
                    
        context = {
            "emploitemps": tabHeure_emploitemps,
            "count_emploi_samedi": count_emploi_samedi,
            "count_emploi_dimanche": count_emploi_dimanche
        }
        
        return render(request, "content_emploitemps_parent.html", context)
         
