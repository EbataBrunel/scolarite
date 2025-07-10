# Importation des modules standards
import bleach
import re
import base64
import pdfkit
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from django.views import View
from django.db import transaction
from decimal import Decimal
from datetime import date
from django.http.response import HttpResponse
from django.template.loader import get_template
from django.contrib import messages
# Importation des modules locaux
from .models import*
from school.views import get_setting
from app_auth.decorator import unauthenticated_customer, allowed_users
from enseignement.models import Enseigner
from inscription.models import Inscription
from programme.models import Programme
from classe.models import Classe
from absence.models import Absencestudent
from cycle.models import Cycle
from scolarite.utils.crypto import dechiffrer_param

permission_directeur_etudes = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Enseignant']
permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_enseignant = ['Enseignant']
permission_promoteur_enseignant = ['Promoteur', 'Enseignant']

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def compositions(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles = Composer.objects.values("salle_id").filter(anneeacademique_id=anneeacademique_id).annotate(effectif=Count("salle_id"))
    tabComposition = []
    for salle in salles:
        count_trimestres = (Composer.objects.values("trimestre")
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=salle["salle_id"])
                        .annotate(effectif=Count("trimestre")).count()
        )
        # Recuperer la salle
        s = Salle.objects.get(id=salle["salle_id"])
        if s.classe.id == classe_id:
            dic = {}
            dic["salle"] = s
            dic["effectif"] = count_trimestres
            
            tabComposition.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "compositions": tabComposition,
        "anneeacademique": anneeacademique
    }
    return render(request, "compositions.html", context)
  

@login_required(login_url='connection/login') 
@allowed_users(allowed_roles=permission_directeur_etudes)  
def detail_cmp_salle(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    salle_id = int(dechiffrer_param(str(id)))
    salle = Salle.objects.get(id=salle_id)
    compositions = (
        Composer.objects.values("trimestre")
        .filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
        .annotate(nb_student=Count("student_id", distinct=True), nb_matiere=Count("matiere_id", distinct=True))
    )

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "compositions": compositions,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_cmp_salle.html", context)


@login_required(login_url='connection/login')  
@allowed_users(allowed_roles=permission_directeur_etudes)
def detail_cmp_trimestre(request, salle_id, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    trim = dechiffrer_param(trimestre)
    salle = Salle.objects.get(id=id)
    # Récuperer les étudiants qui ont composé dans cette salle pour ce trimestre
    students = (
        Composer.objects.values("student_id")
            .filter(anneeacademique_id=anneeacademique_id, salle_id=id, trimestre=trim)
            .annotate(effectif=Count("student_id"))
    )
    tabStudents = []
    for student in students:
        s = Student.objects.get(id=student["student_id"])
        dic = {}
        dic["student"] = s
        dic["nb_matieres"] = student["effectif"]
        tabStudents.append(dic)
    
    # Récuperer toutes les matières que les étudiants ont composé dans cette salle pour ce trimestre
    matieres = (
        Composer.objects.values("matiere_id")
            .filter(anneeacademique_id=anneeacademique_id, salle_id=id, trimestre=trim)
            .annotate(effectif=Count("matiere_id"))
    )
    tabMatiers = []
    for matiere in matieres:
        
        evaluations = (
            Composer.objects.values('evaluation')
                .filter(anneeacademique_id=anneeacademique_id, salle_id=id, trimestre=trim, matiere_id=matiere["matiere_id"])
                .annotate(effectif=Count("evaluation"))
        )
        
        m = Matiere.objects.get(id=matiere["matiere_id"])
        dic = {}
        for evaluation in evaluations:
            
            if evaluation["evaluation"] == "Examen":
                dic["nb_examens"] = evaluation["effectif"] 
            if evaluation["evaluation"] == "Contrôle":
                nb_comp_numcontrole = (
                    Composer.objects.values('numerocontrole')
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=id, trimestre=trim, matiere_id=matiere["matiere_id"], evaluation=evaluation["evaluation"])
                        .annotate(effectif=Count("numerocontrole")).count()
                )
                dic["nb_controles"] = nb_comp_numcontrole 
        dic["matiere"] = m
        tabMatiers.append(dic)     
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "salle": salle,
        "students": tabStudents,
        "matieres": tabMatiers,
        "trimestre": trim,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_cmp_trimestre.html", context)


@login_required(login_url='connection/login')
def detail_comp_student(request, salle_id, trimestre, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    trim = dechiffrer_param(trimestre)
    st_id = int(dechiffrer_param(str(student_id)))
    salle = Salle.objects.get(id=id)
    student = Student.objects.get(id=st_id)

    compositions = Composer.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=id, student_id=st_id, trimestre=trim)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
            "setting": setting,
            "compositions": compositions,
            "salle": salle,
            "student": student,
            "trimestre": trim,
            "param": "s", # Utiliser pour un retour sur la page,
            "anneeacademique": anneeacademique
    }
    return render(request, "detail_comp_student.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def detail_comp_matiere(request, salle_id, trimestre, matiere_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    trim = dechiffrer_param(trimestre)
    mt_id = int(dechiffrer_param(str(matiere_id)))
    
    salle = Salle.objects.get(id=id)
    matiere = Matiere.objects.get(id=mt_id)

    compositions = Composer.objects.filter(
        anneeacademique_id=anneeacademique_id, 
        salle_id=id, matiere_id=mt_id, 
        trimestre=trim)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
            "setting": setting,
            "compositions":compositions,
            "salle": salle,
            "matiere": matiere,
            "trimestre": trim,
            "param": "m", # Utiliser pour un retour sur la page
            "anneeacademique": anneeacademique
    }
    return render(request, "detail_comp_matiere.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def add_composition(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    
    if request.method == "POST":

        salle_id = request.POST["salle"]
        matiere_id = request.POST["matiere"]
        student_id = request.POST["student"]
        evaluation = bleach.clean(request.POST["evaluation"].strip())
        note = bleach.clean(request.POST["note"].strip())
        trimestre = bleach.clean(request.POST["trimestre"].strip())
        
        if request.session.get('cycle_id'):
            cycle_id = request.session.get('cycle_id')
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=cycle_id)
            if  trimestre == "Trimestre 3" and cycle.libelle == "Lycée":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
                
            if  trimestre == "Trimestre 3" and cycle.libelle == "Collège":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
                
            if  trimestre == "Trimestre 3" and cycle.libelle == "Primaire":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
        else:            
            salle = Salle.objects.get(id=salle_id)            
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=salle.cycle.id)
            if  trimestre == "Trimestre 3" and cycle.libelle == "Lycée":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
                
            if  trimestre == "Trimestre 3" and cycle.libelle == "Collège":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
                
            if  trimestre == "Trimestre 3" and cycle.libelle == "Primaire":
                remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                trimestre = remplacer_trimestre
            
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(salle_id=salle_id, trimestre=trimestre, status_cloture=False, anneeacademique_id=anneeacademique_id)        
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        note = re.sub(r'\xa0', '', note)  # Supprime les espaces insécables
        note = note.replace(" ", "").replace(",", ".")

        try:
            note = Decimal(note) # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "La note doit être un nombre valide."})
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
        if deliberation.exists(): # Verifier si on a déjà cloturé les opérations de ce trimestre
            return JsonResponse({
                "status": "error",
                "message": "Les opérations de ce trimestre ont déjà été clôturées."})
        if evaluation == "Examen":   
            query = Composer.objects.filter(student_id=student_id, salle_id=salle_id, matiere_id=matiere_id, trimestre=trimestre, evaluation="Examen", anneeacademique_id=anneeacademique_id)
            if query.exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cette composition existe déjà."})

            else:
                composition = Composer(
                    user_id=user_id,
                    student_id=student_id, 
                    salle_id=salle_id, 
                    matiere_id=matiere_id, 
                    evaluation=evaluation, 
                    trimestre=trimestre, 
                    note=note, 
                    anneeacademique_id=anneeacademique_id)
                    
                # Nombre de compositions avant l'ajout
                count0 = Composer.objects.all().count()
                composition.save()
                # Nombre de compositions après l'ajout
                count1 = Composer.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Composition enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
        else:
            numerocontrole = bleach.clean(request.POST["numerocontrole"].strip())
            query = Composer.objects.filter(student_id=student_id, salle_id=salle_id, matiere_id=matiere_id, trimestre=trimestre, anneeacademique_id=anneeacademique_id, numerocontrole=numerocontrole)
            if query.exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cette composition existe déjà."})

            else:
                composition = Composer(
                    user_id=user_id,
                    student_id=student_id, 
                    salle_id=salle_id, 
                    matiere_id=matiere_id, 
                    evaluation=evaluation, 
                    numerocontrole=numerocontrole,
                    trimestre=trimestre, 
                    note=note, 
                    anneeacademique_id=anneeacademique_id)
                    
                # Nombre de compositions avant l'ajout
                count0 = Composer.objects.all().count()
                composition.save()
                # Nombre de compositions après l'ajout
                count1 = Composer.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Composition enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
    tabSalles = []
    if request.session.get('group_name') in permission_promoteur_DG:
        classe_id = request.session.get('classe_id')
        # Récuperer la classe
        salles = Salle.objects.filter(classe_id=classe_id)
        for salle in salles:
            tabSalles.append(salle)
    if request.session.get('group_name') == "Enseignant":
        salles_enseignements = (Enseigner.objects.values("salle_id")
                                .filter(enseignant_id=user_id, anneeacademique_id=anneeacademique_id)
                                .annotate(nb_salle=Count("salle_id")))
        for se in salles_enseignements:
            salle = Salle.objects.get(id=se["salle_id"])
            tabSalles.append(salle)
            
        
    evaluations = ["Contrôle", "Examen"]
    context = {
        "setting": setting,
        "salles": tabSalles,
        "evaluations": evaluations
    }
    return render(request, "add_composition.html", context)

class get_student_inscris_salle(View):
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        
        inscriptions = Inscription.objects.filter(salle_id=id, anneeacademique_id = anneeacademique_id)
        students=[]
        for inscription in inscriptions:
                students.append(inscription.student)

        context = {
            "students": students
        }
        return render(request, "ajax_student_inscris.html", context)

# Recuperer les trimestres auxquelles les matières sont enseignées dans une salle    
class get_trimestre_enseigner_salle(View):
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        
        trimestre_enseignements = (Enseigner.objects.values('trimestre')
                         .filter(salle_id=id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_trimestre=Count('trimestre')).order_by('trimestre'))
        
        trimestres = []
        for te in trimestre_enseignements:
            trimestres.append(te['trimestre'])
                
        context = {
            "trimestres": trimestres
        }
        return render(request, "ajax_trimestre_enseigner.html", context)

# Récuperer les matières enseignées dans une salle     
class get_matiere_enseigner_salle(View):
    def get(self, request, trimestre, salle_id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        if request.session.get('cycle_id'):
            cycle_id = request.session.get('cycle_id')
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=cycle_id)
        
            enseignements = Enseigner.objects.filter(trimestre=trimestre, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
            matieres = []
            for enseignement in enseignements:
                matieres.append(enseignement.matiere)

            context = {
                "matieres": matieres,
                "cycle": cycle,
                "trimestre": trimestre
            }
            return render(request, "ajax_matiere_enseigner.html", context)
        else:
            salle = Salle.objects.get(id=salle_id)
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=salle.cycle.id)
        
            enseignements = Enseigner.objects.filter(trimestre=trimestre, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
            matieres = []
            for enseignement in enseignements:
                matieres.append(enseignement.matiere)

            context = {
                "matieres": matieres,
                "cycle": cycle,
                "trimestre": trimestre
            }
            return render(request, "ajax_matiere_enseigner.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_enseignant)
def edit_composition(request, id, param):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    composition_id = int(dechiffrer_param(str(id)))
    composition = Composer.objects.get(id=composition_id)
    
    # Récuperer toutes les matières enseignées par trimestre dans une salle
    trimestres_enseignements = (Enseigner.objects.values('trimestre')
                         .filter(salle_id=composition.salle.id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_trimestre=Count('trimestre')).order_by('trimestre'))
    # Simplifier l'écritrure du trimestre
    trimestres = []
    for te in trimestres_enseignements:
        trimestres.append(te['trimestre'])
    
    tabSalle = []
    if request.session.get('group_name') in permission_directeur_etudes:    
        # Récuperer la classe 
        classe_id = request.session.get('classe_id')       
        salles = Salle.objects.filter(classe_id=classe_id).exclude(id=composition.salle.id)
        for salle in salles:
            tabSalle.append(salle)
    else:
        salles_enseignements = (Enseigner.objects.values("salle_id")
                         .filter(anneeacademique_id=anneeacademique_id)
                         .annotate(nb_salles=Count("salle_id")))
        
        for se in salles_enseignements:
            salle = Salle.objects.get(id=se["salle_id"])
            tabSalle.append(salle)
    
        
    tabTrimestre = []
    for trimestre in trimestres:
        if trimestre != composition.trimestre:
            tabTrimestre.append(trimestre)
            
    evaluations = ["Contrôle", "Examen"]
    tabEvalution = []
    for evaluation in evaluations:
        if evaluation != composition.evaluation:
            tabEvalution.append(evaluation)
            
    # Création de la session evaluation pour cacher ou afficher le formulaire
    request.session['evaluation'] = composition.evaluation
            
    students = Student.objects.exclude(id=composition.student.id)
    tabStudents = []
    # Récuperer uniquements les étudiants inscris dans la salle selectionnée.
    for student in students:
        query = Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique_id, salle_id=composition.salle.id)
        if query.exists():
            tabStudents.append(student)
            
    matieres = Matiere.objects.exclude(id=composition.matiere.id)
    tabMatieres = []
    # Récuperer uniquement les matières programmées dans une salle selectionnée.
    for matiere in matieres:
        q = (Enseigner.objects.filter(
            anneeacademique_id=anneeacademique_id, 
            salle_id=composition.salle.id,  
            matiere_id=matiere.id,
            trimestre=composition.trimestre ))

        if q.exists():
            tabMatieres.append(matiere)  
            
    numerocontroles = ["Contrôle n°1", "Contrôle n°2", "Contrôle n°3", "Contrôle n°4", "Contrôle n°5"] 
    tabNumerocontrole = []
    for numerocontrole in numerocontroles: 
            if composition.numerocontrole !=numerocontrole:
                tabNumerocontrole.append(numerocontrole)
    context = {
        "setting": setting,
        "composition": composition,
        "salles": tabSalle,
        "trimestres": tabTrimestre,
        "evaluations": tabEvalution,
        "students": tabStudents,
        "matieres": tabMatieres,
        "controles": tabNumerocontrole,
        "param": param
    }
    return render(request, "edit_composition.html", context)

class get_trim_matiere_enseigner_salle(View):
    def get(self, request, salle_id, id, *args, **kwargs):
            
        anneeacademique_id = request.session.get('anneeacademique_id')
        
        trimestres_enseignements = (Enseigner.objects.values('trimestre')
                         .filter(salle_id=id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_trimestre=Count('trimestre')).order_by('trimestre'))
        
        tabTrimestres = []
        for trimestre in trimestres_enseignements:
            tabTrimestres.append(trimestre['trimestre'])
            
        trimestres = []
        for trimestre in tabTrimestres:
            if request.user.is_superuser:
                classe_id = request.session.get('classe_id')
                classe = Classe.objects.get(id=classe_id) 
                if classe.libelle.capitalize() == "Terminale" and trimestre == "Trimestre 3":
                    trimestres.extend(["Bac Test", "Bac Blanc"])
                else:
                    trimestres.append(trimestre)
            else:
                trimestres.append(trimestre)
                
        context = {
            "trimestres": trimestres
        }
        return render(request, "ajax_trim_enseigner.html", context)
    
class get_trim_student_inscris_salle(View):
    def get(self, request, salle_id, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        
        inscriptions = Inscription.objects.filter(salle_id=id, anneeacademique_id = anneeacademique_id)
        students=[]
        for inscription in inscriptions:
                students.append(inscription.student)

        context = {
            "students": students
        }
        return render(request, "ajax_student_inscris.html", context)
    
# Récuperer les matières enseignées dans une salle pour un trimestre    
class get_trimestre_matiere_enseigner_salle(View):
    def get(self, request, salle_id, trimestre, id, *args, **kwargs):
        if request.session.get('cycle_id'):
            cycle_id = request.session.get('cycle_id')
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=cycle_id)
            
            trim = ""
            if trimestre in ["Baccalauréat teste", "Baccalauréat blanc", "BEPC teste", "BEPC blanc", "CEPE teste", "CEPE blanc", "Concours"]:
                trim = "Trimestre 3"
            else:
                trim = trimestre
                
            anneeacademique_id = request.session.get('anneeacademique_id')
            enseignements = Enseigner.objects.filter(trimestre=trim, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
            matieres = []
            for enseignement in enseignements:
                matieres.append(enseignement.matiere)

            context = {
                "matieres": matieres,
                "trimestre": trim,
                "cycle": cycle
            }
            return render(request, "ajax_trimestre_matiere_enseigner.html", context)
        else:
            salle = Salle.objects.get(id=id)
            # Récuperer le cycle
            cycle = Cycle.objects.get(id=salle.cycle.id)
            
            trim = ""
            if trimestre in ["Baccalauréat teste", "Baccalauréat blanc", "BEPC teste", "BEPC blanc", "CEPE teste", "CEPE blanc", "Concours"]:
                trim = "Trimestre 3"
            else:
                trim = trimestre
                
            anneeacademique_id = request.session.get('anneeacademique_id')
            enseignements = Enseigner.objects.filter(trimestre=trim, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
            matieres = []
            for enseignement in enseignements:
                matieres.append(enseignement.matiere)

            context = {
                "matieres": matieres,
                "trimestre": trim,
                "cycle": cycle
            }
            return render(request, "ajax_trimestre_matiere_enseigner.html", context)
        
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_cp(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            composition = Composer.objects.get(id=id)
        except:
            composition = None
        
        if composition is None:
            return JsonResponse({
                        "status": "error",
                        "message": "Identifiant inexistant."})
        else: 
            salle_id = request.POST["salle"]
            matiere_id = request.POST["matiere"]
            trimestre = bleach.clean(request.POST["trimestre"].strip())
            note = bleach.clean(request.POST["note"].strip())
            student_id = request.POST["student"]
            evaluation = bleach.clean(request.POST["evaluation"].strip())
            
            if request.session.get('cycle_id'):
                cycle_id = request.session.get('cycle_id')
                # Récuperer le cycle
                cycle = Cycle.objects.get(id=cycle_id)
                if  trimestre == "Trimestre 3" and cycle.libelle == "Lycée":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
                    
                if  trimestre == "Trimestre 3" and cycle.libelle == "Collège":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
                    
                if  trimestre == "Trimestre 3" and cycle.libelle == "Primaire":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
            else:
                salle = Salle.objects.get(id=salle_id)
                # Récuperer le cycle
                cycle = Cycle.objects.get(id=salle.cycle.id)
                if  trimestre == "Trimestre 3" and cycle.libelle == "Lycée":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
                    
                if  trimestre == "Trimestre 3" and cycle.libelle == "Collège":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
                    
                if  trimestre == "Trimestre 3" and cycle.libelle == "Primaire":
                    remplacer_trimestre = bleach.clean(request.POST["remplacer_trimestre"].strip())
                    trimestre = remplacer_trimestre
            
            numerocontrole = ""
            if evaluation == "Contrôle":
                numerocontrole = request.POST["numerocontrole"]
            
            compositions = Composer.objects.filter(anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabComposition = []
            for c in compositions: 
                
                dic = {} 
                dic["salle_id"] = c.salle.id 
                dic["matiere_id"] = c.matiere.id
                dic["student_id"] = c.student.id
                dic["trimestre"] = c.trimestre
                    
                tabComposition.append(dic)
            
            new_dic = {} 
            new_dic["salle_id"] = int(salle_id) 
            new_dic["matiere_id"] = int(matiere_id)
            new_dic["student_id"] = int(student_id)
            new_dic["trimestre"] = trimestre
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            note = re.sub(r'\xa0', '', note)  # Supprime les espaces insécables
            note = note.replace(" ", "").replace(",", ".")
            # Récuperer la délibération
            deliberation = Deliberation.objects.filter(salle_id=salle_id, trimestre=trimestre, status_cloture=False, anneeacademique_id=anneeacademique_id)        
            try:
                note = Decimal(note) # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "La note doit être un nombre valide."})
                
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."})  
            
            if deliberation.exists(): # Verifier si on a déjà cloturé les opérations de ce trimestre
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de ce trimestre ont déjà été clôturées."})               
            if (new_dic in tabComposition) and evaluation == "Examen": # Verifier l'existance de la composition
                return JsonResponse({
                        "status": "error",
                        "message": "Cette composition existe déjà."})
            else:
                composition.salle_id = salle_id
                composition.matiere_id = matiere_id
                composition.student_id = student_id
                composition.note = note
                composition.trimestre = trimestre
                composition.evaluation = evaluation
                composition.numerocontrole = numerocontrole
                composition.user_id = user_id
                composition.save()
                return JsonResponse({
                        "status": "success",
                        "message": "Composition modifiée avec succès."})


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def del_composition(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        composition_id = int(dechiffrer_param(str(id)))
        composition = Composer.objects.get(id=composition_id)
    except:
        composition = None
        
    if composition:
        # Nombre de compositions avant la suppression
        count0 = Composer.objects.all().count()
        composition.delete()
        # Nombre de compositions après la suppression
        count1 = Composer.objects.all().count()
        if count1 < count0: 
            messages.success(request, "ELément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("del_composition", composition.salle.id, composition.student.id, composition.trimestre)

    
def get_ajax_eval_controle(request, evaluation):
    # Mise à jour de la session evaluation pour cacher ou afficher le formulaire
    numerocontrole = ["Contrôle n°1", "Contrôle n°2", "Contrôle n°3", "Contrôle n°4", "Contrôle n°5"]
    context = {
        "controles": numerocontrole,
        "evaluation": evaluation
    }   
    return render(request, "ajax_eval_controle.html", context=context)
    
def get_ajax_evaluation_controle(request, id, evaluation):
    # Mise à jour de la session evaluation pour cacher ou afficher le formulaire
    request.session['evaluation'] = evaluation
    numerocontrole = ["Contrôle n°1", "Contrôle n°2", "Contrôle n°3", "Contrôle n°4", "Contrôle n°5"]
    context = {
        "controles": numerocontrole,
        "evaluation": evaluation
    }   
    return render(request, "ajax_evaluation_controle.html", context=context)
        
    
# =============================== Délibération ==================================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def comp_deliberation(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles = Salle.objects.filter(classe_id=classe_id)
    context = {
        "setting": setting,
        "salles": salles
    }
    
    return render(request, "comp_deliberation.html", context=context)

class trimestre_deliberation(View):
    def get(self, request, salle_id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        tabTrimestres = []
        trimestre_compositions = (Composer.objects.values("trimestre")
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
                        .annotate(effectif=Count("trimestre")))
        
        for trimestre in trimestre_compositions:
            tabTrimestres.append(trimestre["trimestre"])
            
        # Ordonner les trimestre suivant ordre decroissant
        trimestre_trier = sorted(tabTrimestres, reverse=True)
        context = {
            "trimestres": trimestre_trier
        }
        return render(request, "trimestre_deliberation.html", context=context)
        
        

# Récuperer les matières qui ont été enseignées et composer par les étudiants
def matiere_enseigner(anneeacademique_id, salle_id, trimestre):
    trim = ""
    if trimestre in ["Baccalauréat teste", "Baccalauréat blanc", "BEPC teste", "BEPC blanc", "CEPE teste", "CEPE blanc", "Concours"]:
        trim = "Trimestre 3"
    else:
        trim = trimestre
        
    enseignements = Enseigner.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id, trimestre=trim)
    matieres = []
    # Récuperer les matières auxquelles les élèves ont composé
    for enseignement in enseignements:
            count_composer = (Composer.objects.filter(
                                        salle_id=salle_id, 
                                        anneeacademique_id=anneeacademique_id, 
                                        trimestre=trimestre, 
                                        matiere_id=enseignement.matiere.id).count())
            if count_composer > 0:
                matieres.append(enseignement.matiere)                        
    return matieres

# Récuperer les élèves inscris
def students_inscris(salle_id, anneeacademique_id):
    students = []
    inscriptions = Inscription.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id)
    for inscription in inscriptions:
        students.append(inscription.student)
        
    return students

# Compter le nombre de contrôles d'une matière
def nombre_controle_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
    count_controle_matiere = 0
    matiere_composer = (Composer.objects.values("numerocontrole")
                        .filter(anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            matiere_id=matiere_id, 
                            trimestre=trimestre,
                            evaluation="Contrôle")
                        .annotate(nb_controle=Count("numerocontrole")))
    for cmp in matiere_composer:
        count_controle_matiere += 1
    return count_controle_matiere 

# Calculer la moyenne des notes de controles d'une matière 
def moyenne_note_controle(anneeacademique_id, salle_id, matiere_id, trimestre, student_id):
    note_controle = 0
    compositions = Composer.objects.filter(
                            student_id=student_id,
                            anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            matiere_id=matiere_id, 
                            trimestre=trimestre,
                            evaluation="Contrôle")
    
    for composition in compositions:
        note_controle += composition.note
    
    moyenne_matiere = 0
    # Compter le nombre de contrôle d'une matière
    nombre_controle = nombre_controle_matiere(anneeacademique_id, salle_id, matiere_id, trimestre)
    if nombre_controle > 0:
        moyenne_matiere = note_controle/nombre_controle
    # Calucler la moyenne 
     
    return moyenne_matiere

# Note de l'examens
def note_examen(anneeacademique_id, salle_id, matiere_id, trimestre, student_id):
    note_exam = 0
    composition = Composer.objects.filter(
                            student_id=student_id,
                            anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            matiere_id=matiere_id, 
                            trimestre=trimestre,
                            evaluation="Examen").first()
    if composition:
        note_exam = composition.note
        
    return note_exam

# Verifier l'existence d'un examen
def exitence_examen_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
    existence = False
    query = (Composer.objects.values("matiere_id")
                            .filter(anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            matiere_id=matiere_id, 
                            trimestre=trimestre,
                            evaluation="Examen"))
    if query.exists():
        existence = True
    return existence

# Verifier l'existence de controle d'une matière
def exitence_controle_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
    existence = False
    query = (Composer.objects.values("matiere_id")
                            .filter(anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            matiere_id=matiere_id, 
                            trimestre=trimestre,
                            evaluation="Contrôle"))
    if query.exists():
        existence = True
    return existence

# Calucler la note finale d'une matière
def calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere_id, trimestre, student_id):
    # Récupere la moyenne des note de contrôles de la matière
    note_controle = moyenne_note_controle(anneeacademique_id, salle_id, matiere_id, trimestre, student_id)
    # Récuperer la note de l'examen
    note_exam = note_examen(anneeacademique_id, salle_id, matiere_id, trimestre, student_id)
    # Calcule la moyenne finale de la matière
    note_finale_matiere = float(0)
    if exitence_examen_matiere(anneeacademique_id, salle_id, matiere_id, trimestre) and exitence_controle_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
        note_finale_matiere = float((float(note_exam) + float(note_controle))/2)
    elif exitence_examen_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
        note_finale_matiere = float(note_exam) 
    else:
        note_finale_matiere = float(note_controle)
 
    return note_finale_matiere

# Liste des notes d'une matiere
def liste_notes_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
    # Récuperer les élèves inscris dans cette salle
    students = students_inscris(salle_id, anneeacademique_id)

    moyenne_matieres =[]            
    for student in students: 
        # La note finale d'une matière
        moyenne_matiere = calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere_id, trimestre, student.id)
        moyenne_matieres.append(moyenne_matiere)
          
    return moyenne_matieres 

# Caclucler la somme des coefficients
def calculer_somme_coefficient(anneeacademique_id, salle_id, trimestre):
    # Récuperer les matières qui ont été enseignées et composées par les étudiants
    matieres = matiere_enseigner(anneeacademique_id, salle_id, trimestre)
    somme_coefficient = 0
    for matiere in matieres:
        # Recuperer le coefficient 
        programmes = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
        for programme in programmes:
            if programme.matiere.id == matiere.id:
                somme_coefficient += programme.coefficient
                
    return somme_coefficient

def avg_student(anneeacademique_id, salle_id, trimestre, student_id): 
    moyenne_generale = 0  
    # Récuperer les matières enseignées
    matieres = matiere_enseigner(anneeacademique_id, salle_id, trimestre)
    somme_note_finale = 0
    for matiere in matieres:
        # Recuperer le coefficient
        programme = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, matiere_id=matiere.id).first()
        note_finale_matiere = calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
        
        # Multiplier la note finale par le coefficient
        somme_note_finale += float(programme.coefficient) * float(note_finale_matiere) 
        
    somme_coefficient = calculer_somme_coefficient(anneeacademique_id, salle_id, trimestre)
    
    if somme_coefficient > 0:
        moyenne_generale = somme_note_finale/somme_coefficient
   
    return moyenne_generale

# Définir la mention
def mention_student(moyenne_generale):
    mention = ""
    if moyenne_generale < 6:
        mention = "Mediocre"
    elif moyenne_generale >=6 and moyenne_generale <9:
        mention = "Insuffisante"
    elif moyenne_generale >=9 and moyenne_generale <12:
        mention = "Passable"
    elif moyenne_generale >=12 and moyenne_generale <14:
        mention = "Assez-bien"
    elif moyenne_generale >=14 and moyenne_generale <16:
        mention = "Bien"
    elif moyenne_generale >=16 and moyenne_generale <20:
        mention = "Très bien"
    else:
        mention = "Honorable"   
        
    return mention   

# Recuperer l'enseignant de la matière
def recuperer_enseignant_matiere(anneeacademique_id, salle_id, matiere_id, trimestre):
    trim = ""
    if trimestre in ["Baccalauréat teste", "Baccalauréat blanc", "BEPC teste", "BEPC blanc", "CEPE teste", "CEPE blanc", "Concours"]:
        trim = "Trimestre 3"
    else:
        trim = trimestre
    enseigner = (Enseigner.objects.filter(
        anneeacademique_id=anneeacademique_id, 
        salle_id=salle_id, 
        matiere_id=matiere_id, 
        trimestre=trim).first())
    return enseigner.enseignant

def detail_note_student(anneeacademique_id, salle_id, trimestre, student_id):
    # Récuperer les matières qui ont été enseignées et composer par les étudiants
    matieres = matiere_enseigner(anneeacademique_id, salle_id, trimestre)
    # Recuperer les notes de l'examen et de contrôles de chaque matière
    details = []
    total_note = 0
    for matiere in matieres:
        dic = {}
        # Calculer la moyenne des notes de controles d'une matière 
        moyenne_controle = moyenne_note_controle(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
        # Note de l'examen
        note_exam = note_examen(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
        # Récuperer le coefficient de la matière
        programme = Programme.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, matiere_id=matiere.id).first()
           
        
        if exitence_examen_matiere(anneeacademique_id, salle_id, matiere.id, trimestre) is False:
            note_exam = ""
        
        if exitence_controle_matiere(anneeacademique_id, salle_id, matiere.id, trimestre) is False:
            moyenne_controle = ""       
        
        dic["matiere"] = matiere
        dic["moyenne_controle"] = moyenne_controle
        dic["note_examen"] = note_exam
        dic["moyenne_finale_matiere"] = calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
        dic["coefficient"] = programme.coefficient
        dic["total_note"] = programme.coefficient * calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
        dic["mention_note_matiere"] = mention_student(calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere.id, trimestre, student_id))
        dic["enseignant"] = recuperer_enseignant_matiere(anneeacademique_id, salle_id, matiere.id, trimestre)
        dic["note_minimale"] = min(liste_notes_matiere(anneeacademique_id, salle_id, matiere.id, trimestre))
        dic["note_maximale"] = max(liste_notes_matiere(anneeacademique_id, salle_id, matiere.id, trimestre))
        details.append(dic)
        
        total_note += programme.coefficient * calucler_note_finale_matiere(anneeacademique_id, salle_id, matiere.id, trimestre, student_id)
    return details, total_note

# nombre des étudiants inscris
def nombre_student_inscris(anneeacademique_id, salle_id):
    nombre_inscris = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id).count()
    return nombre_inscris 

#nombre des étudiants qui ont composé 
def nombre_student_composer(anneeacademique_id, salle_id, trimestre):
    # Récuperer les élèves inscris
    students = students_inscris(salle_id, anneeacademique_id) 
    count_students_composer = 0
    for student in students:
        query = Composer.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre, student_id=student.id)   
        if query.exists():
            count_students_composer += 1
    return count_students_composer


# Liste des étudiants admis
def list_students_admis(anneeacademique_id, salle_id, trimestre):
    # Récuperer la délibération
    deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
    # Récuperer les élèves inscris dans cette salle
    students = students_inscris(salle_id, anneeacademique_id)
    
    moyenne_students_admis =[]
    for student in students: 
        dic = {}
        moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                    
        if moyenne_generale >= deliberation.moyennevalidation:
            dic["student"] = student
            dic["moyenne"] = moyenne_generale
            dic["mention"] = mention_student(moyenne_generale)
            dic["details"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[0]
            dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[1]
            moyenne_students_admis.append(dic)
                
    # Trier par moyenne en ordre croissant
    moyenne_students_trier = sorted(moyenne_students_admis, key=lambda x: x["moyenne"], reverse=True)
    # Ajouter le rang à chaque élément
    for i, st in enumerate(moyenne_students_trier, start=1):
        st["rang"] = i
                
    return moyenne_students_trier

# Liste des élèves ajournés
def list_students_ajournes(anneeacademique_id, salle_id, trimestre):
    # Récuperer la délibération
    deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
    # Récuperer les élèves inscris dans cette salle
    students = students_inscris(salle_id, anneeacademique_id)
    moyenne_students_ajournes = []
    for student in students: 
        dic = {}
        moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                    
        if moyenne_generale < deliberation.moyennevalidation:
            dic["student"] = student
            dic["moyenne"] = moyenne_generale
            dic["mention"] = mention_student(moyenne_generale)
            dic["details"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[0]
            dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[1]
            moyenne_students_ajournes.append(dic)
                
    # Trier par moyenne en ordre croissant
    moyenne_students_trier = sorted(moyenne_students_ajournes, key=lambda x: x["moyenne"], reverse=True)
    # Ajouter le rang à chaque élément
    for i, st in enumerate(moyenne_students_trier, start=1):
        # On ajoute le nombre total au rang des élèves ajournés pour determiner le rang de chacun. 
        st["rang"] = i + len(list_students_admis(anneeacademique_id, salle_id, trimestre))
                
    return moyenne_students_trier

# Liste de tous les élèves
def list_all_students(anneeacademique_id, salle_id, trimestre):
    # Récuperer les élèves inscris dans cette salle
    students = students_inscris(salle_id, anneeacademique_id)

    moyenne_students =[]            
    for student in students: 
        dic = {}
        moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                    
        dic["student"] = student
        dic["moyenne"] = moyenne_generale
        dic["mention"] = mention_student(moyenne_generale)
        dic["details"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[0]
        dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[1]
        moyenne_students.append(dic)
                
    # Trier par moyenne en ordre croissant
    moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
    # Ajouter le rang à chaque élément
    for i, st in enumerate(moyenne_students_trier, start=1):
        st["rang"] = i
                
    return moyenne_students_trier

  
class content_deliberation(View):
    def get(self, request, salle_id, trimestre, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        # Récuperer les élèves inscris dans cette salle
        students = students_inscris(salle_id, anneeacademique_id)
        
        # moyenne 
        moyennes = []
        # Calucle de la moyenne des élèves
        moyenne_students =[] 
        for student in students: 
            dic = {}
            moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
            dic["student"] = student
            dic["moyenne"] = moyenne_generale
            dic["mention"] = mention_student(moyenne_generale)
            dic["details"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[0]
            dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[1]
            
            moyenne_students.append(dic)
            moyennes.append(moyenne_generale)
            
        # Trier par moyenne en ordre croissant
        moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
        # Ajouter le rang à chaque élément
        for i, st in enumerate(moyenne_students_trier, start=1):
            st["rang"] = i
            
        # Nombre total des détudiant inscris
        nombre_total_students = len(list_all_students(anneeacademique_id, salle_id, trimestre))
        # Moyenne minimal et maximal
        moyenne_min = min(moyennes)
        moyenne_max = max(moyennes) 
        # Somme des coefficients
        somme_coefficient = calculer_somme_coefficient(anneeacademique_id, salle_id, trimestre)
        # Nombre des étudiants qui ont composé
        nb_students_inscris = nombre_student_inscris(anneeacademique_id, salle_id)
        # Nombre des étudiants qui ont composé
        nb_student_composer = nombre_student_composer(anneeacademique_id, salle_id, trimestre)
        # Récuperer la salle
        salle = Salle.objects.get(id=salle_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
        
        context = {
            "salle": salle,
            "trimestre": trimestre,
            "moyenne_students": moyenne_students_trier,
            "somme_coefficient": somme_coefficient,
            "nb_students_inscris": nb_students_inscris,
            "nb_student_composer": nb_student_composer,
            "deliberation": deliberation,
            "nombre_total_students": nombre_total_students,
            "moyenne_min": moyenne_min,
            "moyenne_max": moyenne_max
        }
        return render(request, "content_deliberation.html", context=context)
    
class tri_student_composer(View):
    def get(self, request, action, salle_id, trimestre, *args, **kwargs):
        
        anneeacademique_id = request.session.get('anneeacademique_id')
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
        
        # Calucle de la moyenne des élèves
        moyenne_all_students_trier = []
        moyenne_students_admis_trier = []
        moyenne_student_ajournes_trier = [] 
        if action == "all":
            # Liste de tous les élèves
            moyenne_all_students_trier = list_all_students(anneeacademique_id, salle_id, trimestre)

        elif action == "admis":  
            # liste des élèves admis             
            moyenne_students_admis_trier = list_students_admis(anneeacademique_id, salle_id, trimestre)
                
        else:
            # Liste des élèves ajournés
            moyenne_student_ajournes_trier = list_students_ajournes(anneeacademique_id, salle_id, trimestre)
            
        nombre_admis = len(list_students_admis(anneeacademique_id, salle_id, trimestre))
        nombre_ajournes = len(list_students_ajournes(anneeacademique_id, salle_id, trimestre))
        nombre_total_students = len(list_all_students(anneeacademique_id, salle_id, trimestre))
            
        # Somme des coefficients
        somme_coefficient = calculer_somme_coefficient(anneeacademique_id, salle_id, trimestre)
        # Nombre des étudiants qui ont composé
        nb_students_inscris = nombre_student_inscris(anneeacademique_id, salle_id)
        # Nombre des étudiants qui ont composé
        nb_student_composer = nombre_student_composer(anneeacademique_id, salle_id, trimestre)
        # Récuperer la salle
        salle = Salle.objects.get(id=salle_id)
        
        context = {
            "salle": salle,
            "trimestre": trimestre,
            "moyenne_students": moyenne_all_students_trier,
            "moyenne_students_admis": moyenne_students_admis_trier,
            "moyennes_students_ajournes": moyenne_student_ajournes_trier,
            "somme_coefficient": somme_coefficient,
            "nb_students_inscris": nb_students_inscris,
            "nb_student_composer": nb_student_composer,
            "deliberation": deliberation,
            "nombre_admis": nombre_admis,
            "nombre_ajournes": nombre_ajournes,
            "nombre_total_students": nombre_total_students,
            "action": action
        }
        return render(request, "tri_student_composer.html", context=context)   

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
@transaction.atomic    
def moyenne_validation(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        anneeacademique_id = request.session.get('anneeacademique_id')
        salle_id = request.POST["salle_id"]
        moyenne = bleach.clean(request.POST["moyenne"].strip())
        trimestre = request.POST["trimestre"]
        # Verifier si la déliberation existe ou pas.
        if id !=0: 
            deliberation = Deliberation.objects.get(id=id)      
            deliberation.anneeacademique_id = anneeacademique_id
            deliberation.salle_id = salle_id
            deliberation.trimestre = trimestre
            deliberation.moyennevalidation = moyenne
        
            deliberation.save()            
            
            # Récuperer les élèves inscris dans cette salle
            students = students_inscris(salle_id, anneeacademique_id)
            
            # Calucle de la moyenne des élèves
            moyenne_students =[] 
            for student in students: 
                dic = {}
                moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                dic["student"] = student
                dic["moyenne"] = moyenne_generale
                dic["mention"] = mention_student(moyenne_generale)

                moyenne_students.append(dic)
            
            # Trier par moyenne en ordre croissant
            moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
            # Ajouter le rang à chaque élément
            for i, st in enumerate(moyenne_students_trier, start=1):
                st["rang"] = i
            
            # Récuperer la salle
            salle = Salle.objects.get(id=salle_id)
            # Récuperer la délibération
            deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
            
            context = {
                "salle": salle,
                "trimestre": trimestre,
                "moyenne_students": moyenne_students,
                "deliberation": deliberation
            }
            return render(request, "content_deliberation.html", context=context)
        else:
            deliberation = Deliberation(
                anneeacademique_id=anneeacademique_id, 
                salle_id=salle_id, 
                trimestre=trimestre,
                moyennevalidation=moyenne)
        
            deliberation.save()           
            
            # Récuperer les élèves inscris dans cette salle
            students = students_inscris(salle_id, anneeacademique_id)
            
            # Calucle de la moyenne des élèves
            moyenne_students =[] 
            for student in students: 
                dic = {}
                moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                dic["student"] = student
                dic["moyenne"] = moyenne_generale
                dic["mention"] = mention_student(moyenne_generale)

                moyenne_students.append(dic)
            
            # Trier par moyenne en ordre croissant
            moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
            # Ajouter le rang à chaque élément
            for i, st in enumerate(moyenne_students_trier, start=1):
                st["rang"] = i
            
            # Récuperer la salle
            salle = Salle.objects.get(id=salle_id)
            # Récuperer la délibération
            deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
            
            context = {
                "salle": salle,
                "trimestre": trimestre,
                "moyenne_students": moyenne_students,
                "deliberation": deliberation
            }
            return render(request, "content_deliberation.html", context=context)
        
# ========================== Résultat ===============================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)
def comp_resultat(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles = Salle.objects.filter(classe_id=classe_id)
    context = {
        "setting": setting,
        "salles": salles
    }    
    return render(request, "comp_resultat.html", context=context) 

class content_resultat(View):
    def get(self, request, salle_id, trimestre, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        # Récuperer les élèves inscris dans cette salle
        students = students_inscris(salle_id, anneeacademique_id)
        # Moyenne
        moyennes = []
        # Calucle de la moyenne des élèves
        moyenne_students = [] 
        for student in students: 
            dic = {}
            moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
            dic["student"] = student
            dic["moyenne"] = moyenne_generale
            dic["mention"] = mention_student(moyenne_generale)
            dic["details"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[0]
            dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, trimestre, student.id)[1]
            moyenne_students.append(dic)
            moyennes.append(moyenne_generale)
            
        # Trier par moyenne par ordre croissant
        moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
        # Ajouter le rang à chaque élément
        for i, st in enumerate(moyenne_students_trier, start=1):
            st["rang"] = i
        
        # Récuperer la salle
        salle = Salle.objects.get(id=salle_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
        
        # Somme des coefficients
        somme_coefficient = calculer_somme_coefficient(anneeacademique_id, salle_id, trimestre)
        # Nombre des étudiants qui ont composé
        nb_students_inscris = nombre_student_inscris(anneeacademique_id, salle_id)
        # Nombre des étudiants qui ont composé
        nb_student_composer = nombre_student_composer(anneeacademique_id, salle_id, trimestre)
        # Moyenne minimal et maximal
        moyenne_min = min(moyennes)
        moyenne_max = max(moyennes) 
        # Récuperer la salle
        salle = Salle.objects.get(id=salle_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
        
        context = {
            "salle": salle,
            "trimestre": trimestre,
            "moyenne_students": moyenne_students_trier,
            "somme_coefficient": somme_coefficient,
            "nb_students_inscris": nb_students_inscris,
            "nb_student_composer": nb_student_composer,
            "moyenne_min": moyenne_min,
            "moyenne_max": moyenne_max,
            "deliberation": deliberation
        }
        return render(request, "content_resultat.html", context=context)
    
class trimestre_resultat(View):
    def get(self, request, salle_id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        tabTrimestres = []
        trimestre_compositions = (Composer.objects.values("trimestre")
                        .filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
                        .annotate(effectif=Count("trimestre")))
        
        for trimestre in trimestre_compositions:
            tabTrimestres.append(trimestre["trimestre"])
            
        # Ordonner les trimestre suivant ordre decroissant
        trimestre_trier = sorted(tabTrimestres, reverse=True)
        context = {
            "trimestres": trimestre_trier
        }
        return render(request, "trimestre_resultat.html", context=context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)    
def publication_result(request):
    
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            deliberation = Deliberation.objects.get(id=id)
        except:
            deliberation = None
            
        if deliberation is None:
            return JsonResponse({"status": 0})
        else:   
            password = bleach.clean(request.POST["password"])
            user = User.objects.get(id=request.user.id)
            if user.check_password(password):
                deliberation.status = True
                deliberation.save()
                return JsonResponse({
                            "status": "success",
                            "message": "Résultat publié avec succès."})
            else:
                return JsonResponse({
                            "status": "error",
                            "message": "Mot de passe incorrect."})

# =============================== Gestion des études ====================================

# Recuperer toutes les notes de l'examen d'un trimestre d'un étudiant
def examen_trimestre_student(anneeacademique_id, salle_id, trimestre, student_id):
    compositions = Composer.objects.filter(
                            student_id=student_id,
                            anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            trimestre=trimestre,
                            evaluation="Examen")      
    return compositions

# Recuperer toutes les contrôle d'un trimestre de l'étudiant
def controle_trimestre_student(anneeacademique_id, salle_id, trimestre, student_id):
    compositions = Composer.objects.filter(
                            student_id=student_id,
                            anneeacademique_id=anneeacademique_id, 
                            salle_id=salle_id, 
                            trimestre=trimestre,
                            evaluation="Contrôle").order_by("numerocontrole")
    return compositions

def comparaison_note_matiere(anneeacademique_id, salle_id, student_id):
    
    trimestres_compositions = (Composer.objects.values("trimestre")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, student_id=student_id)
                     .annotate(nb_trimestre=Count("trimestre")))
    
    tabCompositions = []   
    for tm in trimestres_compositions: 
            dic = {}
            dic["trimestre"] = tm["trimestre"]
            moyenne_generale = avg_student(anneeacademique_id, salle_id, tm["trimestre"], student_id)
            dic["moyenne"] = moyenne_generale
            dic["details"] = detail_note_student(anneeacademique_id, salle_id, tm["trimestre"], student_id)[0]
            dic["somme_note"] = detail_note_student(anneeacademique_id, salle_id, tm["trimestre"], student_id)[1]

            tabCompositions.append(dic)
            
    return tabCompositions
       

@unauthenticated_customer
def gestion_etude(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = request.session.get('student_id')
    # Récuperer la salle de l'étudiant
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    
    trimestres_compositions = (Composer.objects.values("trimestre")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id)
                     .annotate(nb_trimestre=Count("trimestre")))
    
    tabCompositions = []   
    i = 0 
    for tc in trimestres_compositions:
        i += 1
        dic = {}
        
        dic["i"] = i
        dic["trimestre"] = tc["trimestre"]
        dic["controles"] = controle_trimestre_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student_id)
        dic["examens"] = examen_trimestre_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student_id)
        # Resultats
        moyenne_generale = avg_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student_id)
        dic["moyenne"] = moyenne_generale
        dic["mention"] = mention_student(moyenne_generale)
        dic["details"] = detail_note_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student_id)[0]
        dic["somme_note"] = detail_note_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student_id)[1]
        # Somme des coefficients
        somme_coefficient = calculer_somme_coefficient(anneeacademique_id, inscription.salle.id, tc["trimestre"])
        dic["somme_coefficient"] = somme_coefficient
        # Nombre des étudiants qui ont composé
        dic["nb_students_inscris"] = nombre_student_inscris(anneeacademique_id, inscription.salle.id)      
        # Récuperer les élèves inscris dans cette salle
        students = students_inscris(inscription.salle.id, anneeacademique_id)
        # Calculer la moyenne des élèves pour determiner le min et le max et le rang de chaque étudiant
        moyennes = []
        moyenne_students = []
        for student in students:  
            my = avg_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student.id)          
            moyennes.append(my)   
            dic_rang = {}
            dic_rang["student_id"] = student.id
            dic_rang["moyenne"] = my
            moyenne_students.append(dic_rang)
        
        # Moyenne minimal et maximal
        moyenne_min = min(moyennes)
        moyenne_max = max(moyennes) 
        dic["moyenne_min"] = moyenne_min
        dic["moyenne_max"] = moyenne_max
        
        # Trier par moyenne en ordre croissant
        moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
        # Ajouter le rang à chaque élément
        rang = 0
        for i, st in enumerate(moyenne_students_trier, start=1):
            if st["student_id"] == student_id:
                rang = i
        dic["rang"] = rang
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id, trimestre=tc["trimestre"]).first() 
        dic["deliberation"] = deliberation
        # Récuperer l'étudiant
        student = Student.objects.get(id=student_id)
        dic["student"] = student
        dic["salle"] = inscription.salle
        tabCompositions.append(dic)
    
    # Compter le nombre de déliberation pour verifier s'il y a eu au moins une déliberation
    nb_deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id).count()
    
    # Absence des étudiants
    absences = Absencestudent.objects.filter(student_id=student_id)
    tababsences = []
    for absence in absences:
        if absence.emargement.anneeacademique.id == anneeacademique_id:
            absence.status = True
            absence.save()
            
            tababsences.append(absence)
            # Mettre à jour le status de l'absence pour marquer la lecture 
            
    # Récuperer les matières que l'étudiant a composé
    tabMatiere = []
    for v in comparaison_note_matiere(anneeacademique_id, inscription.salle.id, student_id):
        for m in v['details']:
            matiere = m["matiere"] 
            if matiere.abreviation not in tabMatiere:
                tabMatiere.append(matiere.abreviation)
                
    # Mettre à jour le status de composition de l'étudiant pour marque la lecture
    compositions_students = Composer.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id)
    for composition in compositions_students:
        composition.status = True
        composition.save()
        
    context = {
        "setting": setting,
        "compositions": tabCompositions,
        "nb_deliberation" : nb_deliberation,
        "absences": tababsences,
        "stats_compositions": comparaison_note_matiere(anneeacademique_id, inscription.salle.id, student_id),
        "matieres": tabMatiere,
        "student_id": student_id
    }
    return render(request, "gestion_etude.html", context=context)

@unauthenticated_customer
def gestion_etude_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    parent_id = request.session.get('parent_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer les enfants du parent
    students = Student.objects.filter(parent_id=parent_id) 
    # Selectionner les enfants du parent qui sont inscris cette année
    tabinscription = []
    for student in students:
        query = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id)
        if query.exists():
            # Récuperer l'inscription
            inscription = query.first()
            tabinscription.append(inscription)
    
    gestions = []       
    for inscription in tabinscription:
        dic = {}
        dic["inscription"] = inscription
        # Absence des étudiants
        absences = Absencestudent.objects.filter(student_id=inscription.student.id, status_parent=0)
        for absence in absences:
            if absence.emargement.anneeacademique.id == anneeacademique_id:
                absence.status_parent = 1
                absence.save()
        
        new_absences = Absencestudent.objects.filter(student_id=inscription.student.id, status_parent=1)        
        nombre_absences = 0
        for absence in new_absences:
            if absence.emargement.anneeacademique.id == anneeacademique_id:
                nombre_absences += 1
        
        dic["nombre_absences"] = nombre_absences
        # Récuperer les composition de l'étudiant        
        compositions = Composer.objects.filter(anneeacademique_id=anneeacademique_id, student_id=inscription.student.id, status_parent=0)
        nombre_compositions = 0
        for composition in compositions:
            composition.status_parent = 1  
            composition.save() 
            
        nombre_compositions = Composer.objects.filter(anneeacademique_id=anneeacademique_id, student_id=inscription.student.id, status_parent=1).count()
            
        dic["nombre_compositions"] = nombre_compositions
        
        gestions.append(dic)
            
    context = {
        "setting": setting,
        "gestions": gestions
    }
    return render(request, "gestion_etude_parent.html", context)

@unauthenticated_customer
def gestion_etude_parent_detail(request, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    st_id = int(dechiffrer_param(str(student_id)))
    # Récuperer la salle de l'étudiant
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=st_id).first()
    
    trimestres_compositions = (Composer.objects.values("trimestre")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id)
                     .annotate(nb_trimestre=Count("trimestre")))
    
    tabCompositions = []   
    i = 0 
    for tc in trimestres_compositions:
        i += 1
        dic = {}
        
        dic["i"] = i
        dic["trimestre"] = tc["trimestre"]
        dic["controles"] = controle_trimestre_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], st_id)
        dic["examens"] = examen_trimestre_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], st_id)
        # Resultats
        moyenne_generale = avg_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], st_id)
        dic["moyenne"] = moyenne_generale
        dic["mention"] = mention_student(moyenne_generale)
        dic["details"] = detail_note_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], st_id)[0]
        dic["somme_note"] = detail_note_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], st_id)[1]
        # Somme des coefficients
        somme_coefficient = calculer_somme_coefficient(anneeacademique_id, inscription.salle.id, tc["trimestre"])
        dic["somme_coefficient"] = somme_coefficient
        # Nombre des étudiants qui ont composé
        dic["nb_students_inscris"] = nombre_student_inscris(anneeacademique_id, inscription.salle.id)      
        # Récuperer les élèves inscris dans cette salle
        students = students_inscris(inscription.salle.id, anneeacademique_id)
        # Calculer la moyenne des élèves pour determiner le min et le max et le rang de chaque étudiant
        moyennes = []
        moyenne_students = []
        for student in students:  
            my = avg_student(anneeacademique_id, inscription.salle.id, tc["trimestre"], student.id)          
            moyennes.append(my)   
            dic_rang = {}
            dic_rang["student_id"] = student.id
            dic_rang["moyenne"] = my
            moyenne_students.append(dic_rang)
        
        # Moyenne minimal et maximal
        moyenne_min = min(moyennes)
        moyenne_max = max(moyennes) 
        dic["moyenne_min"] = moyenne_min
        dic["moyenne_max"] = moyenne_max
        
        # Trier par moyenne en ordre croissant
        moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
        # Ajouter le rang à chaque élément
        rang = 0
        for i, st in enumerate(moyenne_students_trier, start=1):
            if st["student_id"] == student_id:
                rang = i
        dic["rang"] = rang
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id, trimestre=tc["trimestre"]).first() 
        dic["deliberation"] = deliberation
        # Récuperer l'étudiant
        student = Student.objects.get(id=st_id)
        dic["student"] = student
        dic["salle"] = inscription.salle
        tabCompositions.append(dic)
    
    # Compter le nombre de déliberation pour verifier s'il y a eu au moins une déliberation
    nb_deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id).count()
    
    # Absence des étudiants
    absences = Absencestudent.objects.filter(student_id=st_id, status_parent__in=[0,1])
    for absence in absences:
        if absence.emargement.anneeacademique.id == anneeacademique_id:
            absence.status_parent = 2
            absence.save()      
            # Mettre à jour le status de l'absence pour marquer la lecture 
            
    # Absence des étudiants
    new_absences = Absencestudent.objects.filter(student_id=st_id)
    tababsences = []
    for absence in new_absences:
        if absence.emargement.anneeacademique.id == anneeacademique_id:      
            tababsences.append(absence)
            
    # Récuperer les matières que l'étudiant a composé
    tabMatiere = []
    for v in comparaison_note_matiere(anneeacademique_id, inscription.salle.id, st_id):
        for m in v['details']:
            matiere = m["matiere"] 
            if matiere.abreviation not in tabMatiere:
                tabMatiere.append(matiere.abreviation)
                
    # Mettre à jour le status de composition de l'étudiant pour marque la lecture
    compositions_students = Composer.objects.filter(student_id=st_id, anneeacademique_id=anneeacademique_id, status_parent__in=[0,1])
    for composition in compositions_students:
        composition.status_parent = 2
        composition.save()
    
    # Récuperer l'étudiant
    stud = Student.objects.get(id=st_id)
    context = {
        "setting": setting,
        "compositions": tabCompositions,
        "nb_deliberation" : nb_deliberation,
        "absences": tababsences,
        "stats_compositions": comparaison_note_matiere(anneeacademique_id, inscription.salle.id, st_id),
        "matieres": tabMatiere,
        "student": stud
    }
    return render(request, "gestion_etude_parent_detail.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_enseignant)
def cmp_teacher(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_enseignements = (Enseigner.objects.values("salle_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("salle_id")))
    
    tabCompositions = []
    for se in salles_enseignements:
        dic = {}
        salle = Salle.objects.get(id=se["salle_id"])
        #query_comp = Composer.objects.filter()
        dic["salle"] = salle
        # Recuperer les matières de l'enseignant auxquelles les élèves ont composé
        enseignements = Enseigner.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=se["salle_id"])
        matieres = []
        for enseignement in enseignements:            
            matieres_compositions = (Composer.objects.values("matiere_id")
                                .filter(anneeacademique_id=anneeacademique_id, matiere_id=enseignement.matiere.id, salle_id=se["salle_id"])
                                .annotate(nb_cmp=Count("matiere_id")))    
            
            for mc in matieres_compositions:
                dic_matiere = {}
                matiere = Matiere.objects.get(id=mc["matiere_id"])
                dic_matiere["matiere"] = matiere
                # Recuperer les trimestres que les étudiants ont composé pour cette matière
                trimestres_compositions = (Composer.objects.values("trimestre")
                                    .filter(anneeacademique_id=anneeacademique_id, salle_id=se["salle_id"], matiere_id=mc["matiere_id"])
                                    .annotate(nb_cmp=Count("trimestre")))
                
                trimestres = []
                for tc in trimestres_compositions:
                    dic_trimestre = {}
                    dic_trimestre["trimestre"] = tc["trimestre"]
                    
                    trimestres.append(dic_trimestre)
                    
                dic_matiere["trimestres"] = trimestres
                """if matieres:
                    #print(matieres)
                    for mt in matieres:
                        if mt["matiere"] != matiere.libelle:
                            matieres.append(dic_matiere)
                else:
                    matieres.append(dic_matiere)"""
                matieres.append(dic_matiere)
        matiere_rencontrees = set()  # Ensemble pour suivre les matières déjà ajoutées
        resultat = []

        for item in matieres:
            if item['matiere'] not in matiere_rencontrees:
                resultat.append(item)
                matiere_rencontrees.add(item['matiere'])  # Ajouter la matière rencontrée                                           

        dic["matieres"] = resultat
            
        tabCompositions.append(dic)
    
    context = {
        "setting": setting,
        "compositions": tabCompositions
    }
    
    return render(request, "cmp_teacher.html", context=context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_enseignant)
def detail_cmpteacher(request, salle_id, matiere_id, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    
    sl_id = int(dechiffrer_param(str(salle_id)))
    mt_id = int(dechiffrer_param(str(matiere_id)))
    trim = dechiffrer_param(trimestre)
    
    salle = Salle.objects.get(id=sl_id)
    matiere = Matiere.objects.get(id=mt_id)
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    evaluations_compositions = (Composer.objects.values("evaluation")
                    .filter(
                        salle_id=sl_id, 
                        matiere_id=mt_id, 
                        trimestre=trim, 
                        anneeacademique_id=anneeacademique_id)
                    .annotate(nb_evaluation=Count("evaluation")))
    
    tabComposition = []
    for ec in evaluations_compositions:
        evaluation = ec["evaluation"]   
        if evaluation == "Examen": 
            dic = {}   
            compositions = Composer.objects.filter(
                        salle_id=sl_id, 
                        matiere_id=mt_id, 
                        trimestre=trim, 
                        anneeacademique_id=anneeacademique_id, 
                        evaluation="Examen"
            )
            
            dic["evaluation"] = evaluation
            dic["compositions"] = compositions
            dic["eval"] = evaluation
            tabComposition.append(dic) 
        else:
            numevaluations_compositions = (Composer.objects.values("numerocontrole")
                            .filter(
                                salle_id=sl_id, 
                                matiere_id=mt_id,
                                trimestre=trim, 
                                anneeacademique_id=anneeacademique_id,
                                evaluation="Contrôle")
                            .annotate(nb_numerovaluation=Count("numerocontrole"))
            )
            
            for nc in numevaluations_compositions:
                dic = {}
                dic["evaluation"] = nc["numerocontrole"]
                compositions = Composer.objects.filter(
                                salle_id=sl_id, 
                                matiere_id=mt_id,
                                trimestre=trim, 
                                anneeacademique_id=anneeacademique_id, 
                                evaluation="Contrôle",
                                numerocontrole=nc["numerocontrole"]
                )
                dic["compositions"]= compositions
                tabeval = nc["numerocontrole"].split(" ")
                eval = "-".join(tabeval)
                dic["eval"] = eval
                tabComposition.append(dic)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)   
    context = {
        "setting": setting,
        "examens": tabComposition,
        "salle": salle,
        "matiere": matiere,
        "trimestre": trim,
        "param": "t", # Utiliser pour un retour sur la page
        "anneeacademique": anneeacademique
    }
    
    return render(request, "detail_cmpteacher.html", context)

class examen_teacher(View):
    def get(self, request, s_id, m_id, trimestre, evaluation, salle_id, matiere_id, *args, **kwargs):       
        anneeacademique_id = request.session.get('anneeacademique_id')
        if evaluation == "Examen":
            compositions = Composer.objects.filter(
                anneeacademique_id = anneeacademique_id,
                salle_id=salle_id,
                trimestre=trimestre,
                matiere_id=matiere_id,
                evaluation=evaluation
            )
            context = {
                "compositions": compositions,
                "evaluation": evaluation,
                "salle_id": salle_id,
                "trimestre": trimestre,
                "matiere_id": matiere_id,
                "param": "t", # Utiliser pour un retour sur la page
            }
            return render(request, "examen_teacher.html", context)  
        else:
            tabeval = evaluation.split("-")
            eval = " ".join(tabeval)
            compositions = Composer.objects.filter(
                anneeacademique_id = anneeacademique_id,
                salle_id=salle_id,
                trimestre=trimestre,
                matiere_id=matiere_id,
                numerocontrole=eval
            )
            
            context = {
                "compositions": compositions,
                "evaluation": eval,
                "salle_id": salle_id,
                "trimestre": trimestre,
                "matiere_id": matiere_id,
                "param": "t", # Utiliser pour un retour sur la page
            }
            return render(request, "examen_teacher.html", context) 

def pourcentage_comp(anneeacademique_id, trimestre, salle_id):
    
        students = students_inscris(salle_id, anneeacademique_id)
        # Moyenne
        moyennes = []
        # Calucle de la moyenne des élèves
        for student in students: 
            moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
            moyennes.append(moyenne_generale)
        
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
        nombre_admis = 0
        for moyenne in moyennes:
            if deliberation:
                if moyenne >= deliberation.moyennevalidation:
                    nombre_admis += 1
        # Nombre des étudiants qui ont composé
        nb_student_composer = nombre_student_composer(anneeacademique_id, salle_id, trimestre)
        pourcentage = 0
        if nb_student_composer > 0:
            pourcentage = (nombre_admis * 100) / nb_student_composer 
        return pourcentage 
    
def pourcentage_comp_salle(anneeacademique_id, salle_id):   
        tabTrimestres = []
        trimestre_compositions = (Composer.objects.values("trimestre")
                            .filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
                            .annotate(effectif=Count("trimestre")))
        
        for tc in trimestre_compositions:
            dic = {}
            trimestre = tc["trimestre"]
            students = students_inscris(salle_id, anneeacademique_id)
            # Moyenne
            moyennes = []
            # Calucle de la moyenne des élèves
            for student in students: 
                moyenne_generale = avg_student(anneeacademique_id, salle_id, trimestre, student.id)
                moyennes.append(moyenne_generale)
            
            # Récuperer la délibération
            deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, trimestre=trimestre).first() 
            nombre_admis = 0
            for moyenne in moyennes:
                if deliberation:
                    if moyenne >= deliberation.moyennevalidation:
                        nombre_admis += 1
            # Nombre des étudiants qui ont composé
            nb_student_composer = nombre_student_composer(anneeacademique_id, salle_id, trimestre)
            pourcentage = 0
            if nb_student_composer > 0:
                pourcentage = (nombre_admis * 100) / nb_student_composer 
            
            dic["trimestre"] = trimestre
            dic["pourcentage"] = pourcentage
        
            tabTrimestres.append(dic)
            
        return tabTrimestres   

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_directeur_etudes)       
def stat_composition(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    classe_id = request.session.get('classe_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Recuperer toutes les salles de cette classe
    salles = Salle.objects.filter(classe_id=classe_id)
    
    tabTrimestres = []
    for salle in salles:
        trimestre_compositions = (Composer.objects.values("trimestre")
                            .filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                            .annotate(effectif=Count("trimestre")))
        
        for trimestre in trimestre_compositions:
            if trimestre not in tabTrimestres:
                tabTrimestres.append(trimestre["trimestre"])
            
    # Ordonner les trimestre suivant ordre decroissant
    trimestre_trier = sorted(tabTrimestres, reverse=True)
    
    context = {
        "setting": setting,
        "trimestres": trimestre_trier,
        "salles": salles
    }
    
    return render(request, "stat_composition.html", context) 
        
def content_stat_comp(request, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    classe_id = request.session.get('classe_id')
    salles = Salle.objects.filter(classe_id=classe_id)
    tabSalles = []
    for salle in salles:
        dic = {}
        dic["salle"] = salle
        dic["pourcentage"] = pourcentage_comp(anneeacademique_id, trimestre, salle.id)
        tabSalles.append(dic)
    context = {
        "salles": tabSalles,
        "trimestre": trimestre
    }
    return render(request, "content_stat_comp.html", context)

def content_stat_comp_trimestre(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    # Récuperer la salle 
    salle = Salle.objects.get(id=salle_id)
    trimestres = pourcentage_comp_salle(anneeacademique_id, salle_id)
    context = {
        "trimestres": trimestres,
        "salle": salle
    }
    return render(request, "content_stat_comp_trimestre.html", context)


def bulletin_etudiant(request, student_id, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    st_id = int(dechiffrer_param(str(student_id)))
    trim = dechiffrer_param(trimestre)
    
    inscription = Inscription.objects.filter(student_id=st_id, anneeacademique_id=anneeacademique_id).first()
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo
    
    # Lire l'image en mode binaire et encoder en Base64
    base64_string = None
    if setting.logo:
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    
    # Chemin vers notre image
    image_path_student = inscription.student.photo
    
    # Lire l'image en mode binaire et encoder en Base64
    base64_string_student = None
    if inscription.student.photo:
        base64_string_student = base64.b64encode(image_path_student.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    # Resultats
    moyenne_generale = avg_student(anneeacademique_id, inscription.salle.id, trim, inscription.student.id)
    mention = mention_student(moyenne_generale)
    details = detail_note_student(anneeacademique_id, inscription.salle.id, trim, inscription.student.id)[0]
    somme_note = detail_note_student(anneeacademique_id, inscription.salle.id, trim, inscription.student.id)[1]
    # Somme des coefficients
    somme_coefficient = calculer_somme_coefficient(anneeacademique_id, inscription.salle.id, trim)
    # Nombre des étudiants qui ont composé
    nb_students_inscris = nombre_student_inscris(anneeacademique_id, inscription.salle.id)   
    # Nombre d'étudiants qui ont composé
    nb_student_compose = nombre_student_composer(anneeacademique_id, inscription.salle.id, trim)   
    # Récuperer les élèves inscris dans cette salle
    students = students_inscris(inscription.salle.id, anneeacademique_id)
    # Calculer la moyenne des élèves pour determiner le min, le max et le rang de chaque étudiant
    moyennes = []
    moyenne_students = []
    for student in students:  
            my = avg_student(anneeacademique_id, inscription.salle.id, trim, student.id)          
            moyennes.append(my)   
            dic_rang = {}
            dic_rang["student_id"] = student.id
            dic_rang["moyenne"] = my
            moyenne_students.append(dic_rang)
        
    # Moyenne minimal et maximal
    moyenne_min = min(moyennes)
    moyenne_max = max(moyennes) 
        
    # Trier par moyenne en ordre croissant
    moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
    # Ajouter le rang à chaque élément
    rang = 0
    for i, st in enumerate(moyenne_students_trier, start=1):
        if st["student_id"] == st_id:
            rang = i 
            break
    
    # Récuperer la délibération
    deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id, trimestre=trim).first() 
    # Nombre d'absences
    nb_absences = 0
    absences = Absencestudent.objects.filter(student_id=st_id)
    for absence in absences:
        if absence.emargement.anneeacademique.id == anneeacademique_id:
            nb_absences += 1
          
    context = {
        "inscription": inscription,
        "details": details,     
        "somme_coefficient": somme_coefficient,
        "somme_note": somme_note,
        "base64_image": base64_string, 
        "moyenne_generale": moyenne_generale,
        "moyenne_min": moyenne_min,
        "moyenne_max": moyenne_max,
        "mention": mention,
        "rang": rang,
        "nb_absences": nb_absences,
        "nb_student_compose": nb_student_compose,
        "deliberation": deliberation,
        "trimestre": trim,
        "nb_students_inscris": nb_students_inscris,
        "base64_image_student": base64_string_student,
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle
    }
    template = get_template("bulletin_etudiant.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Bulletin_{ student.lastname }_{ student.firstname }.pdf"
    return reponse
        
def proces_verbal_examen(request, salle_id, trimestre):
        anneeacademique_id = request.session.get('anneeacademique_id')
        setting = get_setting(anneeacademique_id)
        # Chemin vers notre image
        image_path = setting.logo

        # Lire l'image en mode binaire et encoder en Base64
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
        # Date actuelle
        date_actuelle = date.today()
    
        sl_id = int(dechiffrer_param(str(salle_id)))
        trim = dechiffrer_param(trimestre)
        # Récuperer les élèves inscris dans cette salle
        students = students_inscris(sl_id, anneeacademique_id)
        # Moyenne
        moyennes = []
        # Calucle de la moyenne des élèves
        moyenne_students =[] 
        for student in students: 
            dic = {}
            moyenne_generale = avg_student(anneeacademique_id, sl_id, trim, student.id)
            dic["student"] = student
            dic["moyenne"] = moyenne_generale
            dic["mention"] = mention_student(moyenne_generale)
            moyenne_students.append(dic)
            moyennes.append(moyenne_generale)
            
        # Trier par moyenne par ordre croissant
        moyenne_students_trier = sorted(moyenne_students, key=lambda x: x["moyenne"], reverse=True)
        # Ajouter le rang à chaque élément
        for i, st in enumerate(moyenne_students_trier, start=1):
            st["rang"] = i
        
        # Récuperer la salle
        salle = Salle.objects.get(id=sl_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=sl_id, trimestre=trim).first() 
        # Nombre des étudiants qui ont composé
        nb_students_inscris = nombre_student_inscris(anneeacademique_id, sl_id)
        # Nombre des étudiants qui ont composé
        nb_student_compose = nombre_student_composer(anneeacademique_id, sl_id, trim)
        # Moyenne minimal et maximal
        moyenne_min = min(moyennes)
        moyenne_max = max(moyennes) 
        # Récuperer la salle
        salle = Salle.objects.get(id=sl_id)
        # Récuperer la délibération
        deliberation = Deliberation.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=sl_id, trimestre=trim).first() 
        # Recuperer l'année scolaire
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        context = {
            "setting": setting,
            "salle": salle,
            "trimestre": trim,
            "moyenne_students": moyenne_students_trier,
            "nb_students_inscris": nb_students_inscris,
            "nb_student_compose": nb_student_compose,
            "moyenne_min": moyenne_min,
            "moyenne_max": moyenne_max,
            "deliberation": deliberation,
            "base64_image": base64_string,
            "date_actuelle": date_actuelle,
            "anneeacademique": anneeacademique
        }
        template = get_template("proces_verbal_examen.html")
        html = template.render(context)
        options = {
            'page-size': 'Letter',
            'encoding': "UTF-8",
        }
        pdf = pdfkit.from_string(html, False, options)
        reponse = HttpResponse(pdf, content_type='application/pdf')
        reponse['Content-Disposition'] = f"attachment; filename=Proces_{ salle }_{ trim }.pdf"
        return reponse    


def fetch_releve_controle(request, student_id, matiere_id, num_controle, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    matiere = Matiere.objects.get(id=matiere_id)
    compositions = Composer.objects.filter(
        salle_id=inscription.salle.id, 
        matiere_id=matiere_id,  
        numerocontrole=num_controle,
        trimestre=trimestre,
        anneeacademique_id=anneeacademique_id).order_by("-note")
    context = {
        "inscription": inscription,
        "compositions": compositions,
        "numcontrole": num_controle, 
        "matiere": matiere,
        "trimestre": trimestre
    }
    return render(request, "fetch_releve_controle.html", context)


def fetch_releve_examen(request, student_id, matiere_id, trimestre):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    matiere = Matiere.objects.get(id=matiere_id)
    compositions = Composer.objects.filter(
        salle_id=inscription.salle.id, 
        matiere_id=matiere_id,  
        evaluation="Examen",
        trimestre=trimestre,
        anneeacademique_id=anneeacademique_id).order_by("-note")
    
    context = {
        "inscription": inscription,
        "compositions": compositions, 
        "matiere": matiere,
        "trimestre": trimestre,
        "setting": setting
    }
    return render(request, "fetch_releve_examen.html", context)


def releve_note_controle(request, salle_id, num_controle, matiere_id, trimestre):
        anneeacademique_id = request.session.get('anneeacademique_id')
        setting = get_setting(anneeacademique_id)
        # Chemin vers notre image
        image_path = setting.logo

        # Lire l'image en mode binaire et encoder en Base64
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
        # Date actuelle
        date_actuelle = date.today()
        mt_id = int(dechiffrer_param(str(matiere_id)))
        sl_id = int(dechiffrer_param(str(salle_id)))
        num_cont = dechiffrer_param(str(num_controle))
        trim = dechiffrer_param(trimestre)
        
        matiere = Matiere.objects.get(id=mt_id)
        compositions = Composer.objects.filter(
            salle_id=sl_id, 
            matiere_id=mt_id,  
            numerocontrole=num_cont,
            trimestre=trim,
            anneeacademique_id=anneeacademique_id).order_by("-note")
        
        # Compter le nombre d'élèves qui ont composé
        nb_student_compose = compositions.count()
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        # Récuperer la salle
        salle = Salle.objects.get(id=sl_id)
        
        context = {
            "compositions": compositions, 
            "matiere": matiere,
            "numcontrole": num_cont,
            "trimestre": trim,
            "salle": salle,
            "base64_image": base64_string,
            "date_actuelle": date_actuelle,
            "nb_student_compose":nb_student_compose,
            "setting": setting,
            "anneeacademique": anneeacademique
        }
    
        template = get_template("releve_note_controle.html")
        html = template.render(context)
        options = {
            'page-size': 'Letter',
            'encoding': "UTF-8",
        }
        pdf = pdfkit.from_string(html, False, options)
        reponse = HttpResponse(pdf, content_type='application/pdf')
        reponse['Content-Disposition'] = f"attachment; filename=Releve_note_{ salle }_{ trim }.pdf"
        return reponse


def releve_note_examen(request, salle_id, matiere_id, trimestre):
        anneeacademique_id = request.session.get('anneeacademique_id')
        setting = get_setting(anneeacademique_id)
        # Chemin vers notre image
        image_path = setting.logo

        # Lire l'image en mode binaire et encoder en Base64
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
        # Date actuelle
        date_actuelle = date.today()

        mt_id = int(dechiffrer_param(str(matiere_id)))
        sl_id = int(dechiffrer_param(str(salle_id)))
        trim = dechiffrer_param(trimestre)
        
        matiere = Matiere.objects.get(id=mt_id)
        compositions = Composer.objects.filter(
            salle_id=sl_id, 
            matiere_id=mt_id,  
            evaluation="Examen",
            trimestre=trim,
            anneeacademique_id=anneeacademique_id).order_by("-note")
        
        # Compter le nombre d'élèves qui ont composé
        nb_student_compose = compositions.count()
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
        salle = Salle.objects.get(id=sl_id)
        context = {
            "compositions": compositions, 
            "matiere": matiere,
            "trimestre": trim,
            "salle": salle,
            "nb_student_compose": nb_student_compose,
            "base64_image": base64_string,
            "date_actuelle": date_actuelle,
            "anneeacademique": anneeacademique,
            "setting": setting
        }
    
        template = get_template("releve_note_examen.html")
        html = template.render(context)
        options = {
            'page-size': 'Letter',
            'encoding': "UTF-8",
        }
        pdf = pdfkit.from_string(html, False, options)
        reponse = HttpResponse(pdf, content_type='application/pdf')
        reponse['Content-Disposition'] = f"attachment; filename=Proces_{ sl_id }_{ trim }.pdf"
        return reponse 
    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def deliberations(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    deliberations_groupes = (Deliberation.objects.values('salle_id')
              .filter(anneeacademique_id=anneeacademique_id)
              .annotate(nombre_trimestres=Count('salle_id'))
    )
    tabDeliberations = []
    for dg in deliberations_groupes:
        salle = Salle.objects.get(id=dg["salle_id"])
        dic = {}
        dic["salle"] = salle
        dic["nombre_trimestres"] = dg["nombre_trimestres"]
        dic["deliberations"] = Deliberation.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id)
        tabDeliberations.append(dic)

    context = {
        "setting": setting,
        "deliberations":tabDeliberations
    }
    return render(request, "deliberation/deliberations.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_promoteur_DG)
def detail_deliberation(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    deliberation = Deliberation.objects.get(id=id)

    context = {
        "setting": setting,
        "deliberation": deliberation
    }
    return render(request, "deliberation/detail_deliberation.html", context)

def cloture_deliberation(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            deliberation = Deliberation.objects.get(id=id)
        except:
            deliberation = None
        
        if deliberation is None:
            return JsonResponse({
                        "status": "error",
                        "message": "Identifiant inexistant."})
        else: 
            password = bleach.clean(request.POST["password"].strip())
            user = User.objects.get(id=request.user.id)
            if user.check_password(password):
                if deliberation.status_cloture:
                    deliberation.status_cloture = False
                    deliberation.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_cloture": deliberation.status_cloture,
                                "message": "Délibération désactivée avec succès."})
                else:
                    deliberation.status_cloture = True
                    deliberation.save()
                    
                    return JsonResponse({
                                "status": "success",
                                "status_cloture": deliberation.status_cloture,
                                "message": "Délibération activée avec succès."})
            else:
                return JsonResponse({
                            "status": "error",
                            "message": "Mot de passe incorrect."})