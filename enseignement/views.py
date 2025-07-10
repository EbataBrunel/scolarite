# Importation des modules standards
import bleach
import re
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.views import View
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from decimal import Decimal
from datetime import datetime, timezone
from django.contrib import messages
# Importation des modules locaux
from .models import*
from school.views import get_setting
from programme.models import Programme
from inscription.models import Inscription
from renumeration.models import Contrat
from etablissement.models import Etablissement
from app_auth.decorator import allowed_users, unauthenticated_customer
from scolarite.utils.crypto import dechiffrer_param

permission_directeur_etudes = ['Promoteur', 'Directeur Général', 'Directeur des Etudes']
permission_enseignant = ['Enseignant']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def enseignements(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    classes_enseignement = (Enseigner.objects.values("salle_id")
                     .filter(anneeacademique_id = anneeacademique_id)
                     .annotate(effectif=Count("salle_id")))
    
    tabEnseignement = []
    for enseignement in classes_enseignement:
        nombre_trimestre = (Enseigner.objects.values("trimestre")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=enseignement["salle_id"])
                     .annotate(nb_trimestre=Count("trimestre"))).count()
        
        salle = Salle.objects.get(id=enseignement["salle_id"])    
            
        if salle.classe.id == classe_id:
                dic = {}
                dic["salle"] = salle
                dic["effectif"] = nombre_trimestre
                tabEnseignement.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "enseignements": tabEnseignement,
        "anneeacademique": anneeacademique
    }
    return render(request, "enseignements.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def trim_enseignement(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    enseignements = (Enseigner.objects.values("trimestre")
                     .filter(anneeacademique_id = anneeacademique_id, salle_id=id)
                     .annotate(effectif=Count("trimestre")))

    salle = Salle.objects.get(id=id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "enseignements": enseignements,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "trim_enseignement.html", context)
   

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def detail_enseignement(request, salle_id, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    trim = dechiffrer_param(trimestre)
    salle = Salle.objects.get(id=id)
    enseignements = Enseigner.objects.filter(salle_id=id, trimestre=trim)
    tabEnseignements = []
    for enseignement in enseignements:
        dic = {}
        dic["enseignement"] = enseignement
        # Verifier si on a evalué l'enseignant ou pas
        if enseignement.eval:
            date_actuel = datetime.now(timezone.utc)
            if date_actuel <= enseignement.date_eval:
                dic["status"] = "En cours"
            else:
                dic["status"] = "Terminée"
                
            # Moyenne de l'enseignant
            moyenne_ens = EvaluationEnseignant.objects.filter(
                                anneeacademique_id=anneeacademique_id,
                                enseignant_id=enseignement.enseignant.id,
                                matiere_id=enseignement.matiere.id
                            ).aggregate(moyenne=Avg("note"))["moyenne"]   
            if moyenne_ens:
                if moyenne_ens >= 12:
                    dic["moyenne"] = "Admis(e)"
                else:
                    dic["moyenne"] = "Ajourné(e)"
            else:
                dic["moyenne"] = "Pas de note"
            
        else:
            dic["status"] = "En attente"
            dic["moyenne"] = ""
            
        tabEnseignements.append(dic)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "enseignements": tabEnseignements,
        "salle": salle,
        "trimestre": trim,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_enseignement.html", context)
    

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def add_enseignement(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    classe_id = request.session.get('classe_id')
    if request.method == "POST":

        salle_id = request.POST["salle"]
        matiere_id = request.POST["matiere"]
        enseignant_id = request.POST["enseignant"]
        volumehoraire = bleach.clean(request.POST["volumehoraire"].strip())
        cout_heure = bleach.clean(request.POST["cout_heure"].strip())
        trimestre = bleach.clean(request.POST["trimestre"].strip())
        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        cout_heure = re.sub(r'\xa0', '', cout_heure)  # Supprime les espaces insécables
        cout_heure = cout_heure.replace(" ", "").replace(",", ".")

        try:
            cout_heure = Decimal(cout_heure)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le coût doit être un nombre valide."})

        query = Enseigner.objects.filter(salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id, trimestre=trimestre)
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet enseignement existe déjà."})
        else:
            enseignement = Enseigner(
                salle_id=salle_id, 
                matiere_id=matiere_id, 
                enseignant_id=enseignant_id, 
                volumehoraire=volumehoraire, 
                cout_heure=cout_heure, 
                trimestre=trimestre,
                anneeacademique_id=anneeacademique_id)
            
            # Nombre d'enseignements' avant l'ajout
            count0 = Enseigner.objects.all().count()
            enseignement.save()
            # Nombre d'enseignements après l'ajout
            count1 = Enseigner.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Enseignement enreistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})

    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    trimestres = ["Trimestre 1", "Trimestre 2", "Trimestre 3"]
    #Récuperer les utilisateurs
    users_contrats = (Contrat.objects.values("user_id")
                      .filter(anneeacademique_id=anneeacademique_id)
                      .annotate(nb_contrats=Count("user_id"))
    ) 
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id) 
    users = []
    for uc in users_contrats:
        user = User.objects.get(id=uc["user_id"])
        # Recuperer les groupes de l'utilisateurs
        groups = etablissement.groups.filter(user=user)
        for group in groups:
            if group.name == "Enseignant":
                users.append(user)
                break            
                    
    context = {
        "setting": setting,
        "salles": salles,
        "enseignants": users,
        "trimestres": trimestres
    }
    return render(request, "add_enseignement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_enseignement(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    enseignement_id = int(dechiffrer_param(str(id)))
    enseignement = Enseigner.objects.get(id=enseignement_id)
        
    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id).exclude(id=enseignement.salle.id)
    # Recuperer toutes matières programmées pour une classe
    programmes = Programme.objects.filter(salle_id=enseignement.salle.id)
    matieres = []
    for programme in programmes:
        matieres.append(programme.matiere)
        
    trimestres = ["Trimestre 1", "Trimestre 2", "Trimestre 3"]
    tabTrimestre = []
    for trimestre in trimestres:
        if enseignement.trimestre != trimestre:
            tabTrimestre.append(trimestre)
            
    users_contrats = (Contrat.objects.values("user_id")
                      .filter(anneeacademique_id=anneeacademique_id)
                      .annotate(nb_contrats=Count("user_id")))
    
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id) 
    users = []
    for uc in users_contrats:
        user = User.objects.get(id=uc["user_id"])
        if user.id != enseignement.enseignant.id:
            # Recuperer les groupes de l'utilisateur
            groups = etablissement.groups.filter(user=user)
            for group in groups:
                if group.name in "Enseignant":
                    users.append(user)
                    break

    context = {
        "setting": setting,
        "enseignement": enseignement,
        "salles": salles,
        "matieres": matieres,
        "enseignants": users,
        "trimestres": tabTrimestre
    }
    return render(request, "edit_enseignement.html", context)


@login_required(login_url='connection/connexion')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_en(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            enseignement = Enseigner.objects.get(id=id)
        except:
            enseignement=None

        if enseignement == None:
            return JsonResponse({
                    "status": "error",
                    "message": "Enseignement inexistant."})
        else: 
            salle_id = request.POST["salle"]
            matiere_id = request.POST["matiere"]
            volumehoraire = bleach.clean(request.POST["volumehoraire"].strip())
            cout_heure = bleach.clean(request.POST["cout_heure"].strip())
            enseignant_id = request.POST["enseignant"]
            trimestre = request.POST["trimestre"]
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            cout_heure = re.sub(r'\xa0', '', cout_heure)  # Supprime les espaces insécables
            cout_heure = cout_heure.replace(" ", "").replace(",", ".")

            try:
                cout_heure = Decimal(cout_heure)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le coût doit être un nombre valide."})
                
            # Verifier l'existence de l'enseignement
            enseignements = Enseigner.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabSalle = []
            for p in enseignements:
                dic = {}
                dic["salle_id"] = p.salle.id
                dic["matiere_id"] = p.matiere.id
                dic["trimestre"] = p.trimestre 
                
                tabSalle.append(dic)
            
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["matiere_id"] = int(matiere_id)  
            new_dic["trimestre"] = trimestre      
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
            if new_dic in tabSalle:
                return JsonResponse({
                    "status": "error",
                    "message": "Cet enseignement existe déjà."})
            else:
                enseignement.salle_id = salle_id
                enseignement.matiere_id = matiere_id
                enseignement.volumehoraire = volumehoraire
                enseignement.cout_heure = cout_heure
                enseignement.enseignant_id = enseignant_id
                enseignement.trimestre = trimestre
                enseignement.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Enseignement modifié avec succès."})


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def del_enseignement(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        enseignement_id = int(dechiffrer_param(str(id)))
        enseignement = Enseigner.objects.get(id=enseignement_id)
    except:
        enseignement = None
        
    if enseignement:
        # Nombre d'enseignements avant la suppression
        count0 = Enseigner.objects.all().count()
        enseignement.delete()
        # Nombre d'enseignements après la suppression
        count1 = Enseigner.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("detail_enseignement", enseignement.salle.id)
   
    
class get_matiere_programmer_salle(View):
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        programmes = Programme.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id)
        matieres = []
        for programme in programmes:
            matieres.append(programme.matiere)
            
        context = {
            "matieres": matieres
        }
        return render(request, "ajax_matiere.html", context)
    
    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def droit_eval(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    date_actuelle = datetime.now(timezone.utc)
    
    # Ajouter une semaine
    date_plus_une_semaine = date_actuelle + timedelta(weeks=1)
    enseignement_id = int(dechiffrer_param(str(id)))
    enseignement = Enseigner.objects.get(id=enseignement_id)
    
    moyenne_enseignant = 0
    nb_students = 0
    nb_student_inscris = 0
    evaluations = []
    status = "En attente"
    if enseignement.eval:
        # Moyenne de l'enseignant
        moyenne_ens = EvaluationEnseignant.objects.filter(
                            anneeacademique_id=anneeacademique_id,
                            enseignant_id=enseignement.enseignant.id,
                            matiere_id=enseignement.matiere.id
                        ).aggregate(moyenne=Avg("note"))["moyenne"]   
        moyenne_enseignant = moyenne_ens
        # Compter le nombre d'étudiant inscris 
        nb_student_inscris = Inscription.objects.filter(
                            anneeacademique_id=anneeacademique_id,
                            salle_id=enseignement.salle.id
                        ).count()
        # Compter le nombre d'étudiant qui ont evalué l'enseignant
        nb_students = EvaluationEnseignant.objects.filter(
                            anneeacademique_id=anneeacademique_id,
                            enseignant_id=enseignement.enseignant.id,
                            matiere_id=enseignement.matiere.id
                        ).count()
        
        liste_evaluations = EvaluationEnseignant.objects.filter(
                            anneeacademique_id=anneeacademique_id,
                            enseignant_id=enseignement.enseignant.id,
                            matiere_id=enseignement.matiere.id
                        ).select_related("student")
        for evaluation in liste_evaluations:
            evaluations.append(evaluation)
            
        if date_actuelle <= enseignement.date_eval:
             status = "En cours"
        else:
            status = "Terminée"
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "enseignement": enseignement,
        "status": status,
        "date_plus_une_semaine": date_plus_une_semaine,
        "moyenne_enseignant": moyenne_enseignant,
        "nb_students": nb_students,
        "nb_student_inscris": nb_student_inscris,
        "evaluations": evaluations,
        "anneeacademique": anneeacademique
    }
    return render(request, "droit_eval.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def droit_evaluation(request, id):
    enseignement = Enseigner.objects.get(id=id)    
    date_actuelle = datetime.now()   
    # Ajouter une semaine
    date_plus_une_semaine = make_aware(date_actuelle) + timedelta(weeks=1)
    enseignement.eval = True
    enseignement.date_eval = date_plus_une_semaine
    
    enseignement.save()
    
    if enseignement.eval:
        return JsonResponse({"status": "success", "date_limit": date_plus_une_semaine})
    else:
        return JsonResponse({"status": 0})

@unauthenticated_customer    
def eval_enseignant(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id  = request.session.get('student_id')
    inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()
    enseignements = Enseigner.objects.filter(salle_id=inscription.salle.id, eval=True, anneeacademique_id=anneeacademique_id)
    tabEnseignement = []
    for enseignement in enseignements:
        query = EvaluationEnseignant.objects.filter(
            anneeacademique_id=anneeacademique_id, 
            student_id=student_id,
            enseignant_id=enseignement.enseignant.id,
            matiere_id=enseignement.matiere.id)
        if query.exists():
            dic = {}
            dic["enseignement"] = enseignement
            dic["status"] = True
            evaluation = query.first()
            dic["note"] = evaluation.note
            dic["justification"] = evaluation.justification
            tabEnseignement.append(dic)
        else:
            date_actuel = datetime.now(timezone.utc)
            if  date_actuel <= enseignement.date_eval:
                dic = {}
                dic["enseignement"] = enseignement
                dic["status"] = False
                dic["note"] = 0
                dic["justification"] = ""
                tabEnseignement.append(dic)
        
    
    context = {
        "setting": setting,
        "enseignements": tabEnseignement
    }
    return render(request, "eval_enseignant.html", context)

@unauthenticated_customer
def add_eval(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    student_id = request.session.get('student_id')
    if request.method == "POST":
        try:
            id = int(request.POST["id"])
            enseignement = Enseigner.objects.get(id=id)
            
            note = request.POST["note"]
            justification = request.POST["justification"]
            
            # Validation des données
            if not all([student_id, enseignement.enseignant.id, enseignement.matiere.id, anneeacademique_id]):
                return JsonResponse({"error": "Données manquantes ou invalides"}, status=400)

            evaluation = EvaluationEnseignant(
                student_id=student_id,
                enseignant_id=enseignement.enseignant.id,
                matiere_id=enseignement.matiere.id,
                note=note,
                justification=justification,
                anneeacademique_id=anneeacademique_id
            )
            evaluation.save()
            return JsonResponse({
                    "status": "success",
                    "evaluation": {
                        "note": evaluation.note,
                        "justification": evaluation.justification,
                        "nom_enseignant": evaluation.enseignant.last_name,
                        "prenom_enseignant": evaluation.enseignant.first_name,
                        "matiere": evaluation.matiere.libelle
                    }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)
        
