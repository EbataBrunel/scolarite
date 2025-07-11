# Importation des modules standards
import bleach
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count
from django.views import View
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models.functions import TruncMonth, ExtractMonth
from datetime import datetime, timedelta, timezone
from django.utils.timezone import make_aware
# Importation des modules locaux
from .models import Absence, Absencestudent, AbsenceAdmin
from salle.models import Salle
from emploi_temps.models import EmploiTemps
from emargement.models import Emargement
from inscription.models import Inscription
from app_auth.models import Student, EtablissementUser
from matiere.models import Matiere
from etablissement.models import Etablissement
from anneeacademique.models import AnneeCademique
from renumeration.models import Contrat, Renumeration
from school.views import get_setting
from school.methods import format_month, recuperer_mois_annee
from app_auth.decorator import allowed_users, unauthenticated_customer
from renumeration.views import status_contrat_user
from scolarite.utils.crypto import dechiffrer_param


permission_user = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Surveillant Général', 'Gestionnaire']
permission_directeur_etudes = ['Promoteur', 'Directeur Général', 'Directeur des Etudes']
permission_enseignant = ['Enseignant']

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def absences(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        enseignant_absences = (Absence.objects.values("enseignant_id")
                               .filter(anneeacademique_id=anneeacademique_id)
                               .annotate(nb_salle =Count("enseignant_id")))
        liste_absences = []
        for absence in enseignant_absences:
            user = User.objects.get(id=absence["enseignant_id"])
            dic = {}
            dic["enseignant"] = user
            dic["nb_salle"] = absence["nb_salle"]
            # Compter les motifs des absences d'un enseignant que le DG n'a pas encore pris la decision
            nombre_absences_enseignants = 0
            for abs in Absence.objects.filter(enseignant_id=user.id, status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
                month = recuperer_mois_annee(abs.date_absence) # Récuperer le mois de l'absence 
                if not Renumeration.objects.filter(user_id=abs.user.id, month=month, anneeacademique_id=anneeacademique_id).exclude(type_renumeration="Administrateur scolaire").exists():
                    nombre_absences_enseignants += 1
            dic["nombre_motifs_absences"] = nombre_absences_enseignants
            
            liste_absences.append(dic)
            
        context = {
            "liste_absences": liste_absences,
            "setting": setting
        }
        return render(request, "absences.html", context=context)

@login_required(login_url='connection/account')  
@allowed_users(allowed_roles=permission_directeur_etudes)
def detail_salle_absence(request, enseignant_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(enseignant_id)))
    enseignant = User.objects.get(id=id)
    salle_absences = (Absence.objects.values("salle_id")
                  .filter(anneeacademique_id=anneeacademique_id, enseignant_id=id)
                  .annotate(nb_absence=Count("salle_id")))
    
    tabAbsence = []
    for absence in salle_absences:
        salle = Salle.objects.get(id=absence["salle_id"])
        dic = {}
        dic["salle"] = salle
        dic["nb_absence"] = absence["nb_absence"]
        # Compter les motifs des absences d'un enseignant que le DG n'a pas encore pris la decision
        nombre_motifs_absences = 0
        for abs in Absence.objects.filter(enseignant_id=id, salle_id=salle.id, status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
            month = recuperer_mois_annee(abs.date_absence) # Récuperer le mois de l'absence 
            if not Renumeration.objects.filter(user_id=abs.user.id, month=month, anneeacademique_id=anneeacademique_id).exclude(type_renumeration="Administrateur scolaire").exists():
                nombre_motifs_absences += 1
                
        dic["nombre_motifs_absences"] = nombre_motifs_absences 
        tabAbsence.append(dic)

    context = {
        "absences": tabAbsence,
        "setting": setting,
        "enseignant": enseignant
    }   
    
    return render(request, "detail_salle_absence.html", context=context) 
        
@login_required(login_url='connection/account') 
@allowed_users(allowed_roles=permission_directeur_etudes)
def detail_absences(request,enseignant_id, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    en_id = int(dechiffrer_param(str(enseignant_id)))
    sl_id = int(dechiffrer_param(str(salle_id)))
    
    enseignant = User.objects.get(id=en_id)
    salle = Salle.objects.get(id=sl_id)
    absences = Absence.objects.filter(
        anneeacademique_id=anneeacademique_id, 
        enseignant_id=en_id, 
        salle_id=sl_id
    )
    
    tabAbsences = []
    for absence in absences:
        dic = {}
        dic["absence"] = absence
        status_paye = False
        month = recuperer_mois_annee(absence.date_absence) # Récuperer le mois de l'absence 
        if Renumeration.objects.filter(user_id=absence.user.id, month=month, anneeacademique_id=anneeacademique_id).exclude(type_renumeration="Administrateur scolaire").exists():
            status_paye = True
        dic["status_paye"] = status_paye
        tabAbsences.append(dic)
        
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "absences": tabAbsences,
        "enseignant": enseignant,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_absences.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def save_absence(request, emploi_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'emploi du temps
    emploitemps_id = int(dechiffrer_param(str(emploi_id)))
    emploitemps = EmploiTemps.objects.get(id=emploitemps_id)  
    # Verifier le statut du contrat de l'enseignant 
    user_id = emploitemps.enseignant.id
    status_contrat = status_contrat_user(user_id, anneeacademique_id)
    
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()    
    context = {
        "setting": setting,
        "emploitemps": emploitemps,
        "status_contrat": status_contrat,
        "contrat": contrat
    }
    return render(request, "save_absence.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def save_ab(request):
    
    if request.method == "POST":
            date_absence = request.POST["date_absence"]
            emploi_id = request.POST["emploi_id"]
            
            # Récuperer l'emploi du temps
            emploitemps = EmploiTemps.objects.get(id=emploi_id) 
            
            matiere = None
            if emploitemps.salle.cycle.libelle in ["Collège", "Lycée"]:
                matiere = emploitemps.matiere
            
            user_id = request.user.id
            query = Absence.objects.filter(
                anneeacademique_id=emploitemps.anneeacademique.id,
                salle_id=emploitemps.salle.id,
                matiere=matiere,
                enseignant_id=emploitemps.enseignant.id,
                jour=emploitemps.jour, 
                heure_debut=emploitemps.heure_debut,
                heure_fin=emploitemps.heure_fin,
                date_absence=date_absence)
                
            if query.exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cette absence existe déjà."})
            else:
                date_actuelle = datetime.now()   
                # Ajouter trois semaines
                date_plus_trois_jours = make_aware(date_actuelle) + timedelta(days=3)    
                absence = Absence(
                    anneeacademique_id=emploitemps.anneeacademique.id,
                    salle_id=emploitemps.salle.id,
                    matiere=matiere,
                    enseignant_id=emploitemps.enseignant.id,
                    jour=emploitemps.jour, 
                    heure_debut=emploitemps.heure_debut,
                    heure_fin=emploitemps.heure_fin,
                    user_id=user_id,
                    date_absence=date_absence,
                    date_limite=date_plus_trois_jours,
                )
                # Nombre de classes avant l'ajout
                count0 = Absence.objects.all().count()
                absence.save()
                # Nombre de classes après l'ajout
                count1 = Absence.objects.all().count()
                # On verifie si l'insertion a eu lieu ou pas.
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Absence enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_absence(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    absence_id = int(dechiffrer_param(str(id)))
    absence = Absence.objects.get(id=absence_id)
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "absence": absence,
        "setting": setting,
        "contrat": contrat
    }
    return render(request, "edit_absence.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_ab(request):
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            absence = Absence.objects.get(id=id)
        except:
            absence = None

        if absence is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            
            date_absence = request.POST["date_absence"]
            #On verifie si cette classe a été déjà enregistrée
            absences = Absence.objects.exclude(id=id)
            tabAbsence = []
            for a in absences:          
                tabAbsence.append(a.date_absence)
            #On verifie si cette absence existe déjà
            if date_absence in tabAbsence:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette absence existe déjà."}) 
            else:
                absence.date_absence = date_absence
                absence.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Absence modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def del_absence(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    else:
        try:
            absence_id = int(dechiffrer_param(str(id)))
            absence = Absence.objects.get(id=absence_id)
        except:
            absence = None
            
        if absence:
            absence.delete()
        return redirect("absences")
    
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def presence_student(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    emargement_id = int(dechiffrer_param(str(id)))
    emargement = Emargement.objects.get(id=emargement_id)
    
    # Récuperer les étudiants inscris dans la salle ou l'enseignant a été emargé
    inscriptions  = Inscription.objects.filter(
        anneeacademique_id=anneeacademique_id, 
        salle_id=emargement.salle.id)
    
    students = []
    for inscription in inscriptions:
        dic = {}
        dic["student"] = inscription.student
        query = Absencestudent.objects.filter(emargement_id=emargement_id, student_id=inscription.student.id)
        if inscription.status_block:
            if query.exists():
                dic["presence"] = "Absent"
            else:
                dic["presence"] = "Présent"
            students.append(dic)
        else:   
            dic["presence"] = "Bloqué"
            students.append(dic)
    context = {
        "setting": setting,
        "students": students,
        "emargement": emargement
    }
    return render(request, "presence_student.html", context)

class save_absencestudent(View):
    def get(self, request, id, emargement_id, *args, **kwargs):
        student = Student.objects.get(id=id)
        
        query = Absencestudent.objects.filter(
                student_id=id,
                emargement_id=emargement_id)
                
        if query.exists():
            absence = query.first()
            absence.delete()
            presence = "Présent"
            context = {
                "presence": presence,
                "student": student
                
            }
            return render(request, "save_absencestudent.html", context)
        else:               
            absence = Absencestudent(
                emargement_id=emargement_id,
                student_id=id
            )
            absence.save()
            presence = "Absent"
            context = {
                "presence": presence,
                "student": student
            }
            return render(request, "save_absencestudent.html", context)
        
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def abs_students(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_emargements = (Emargement.objects.values("salle_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("salle_id")))
    
    tabEmargements = []
    for se in salles_emargements:
        dic = {}
        salle = Salle.objects.get(id=se["salle_id"])
        dic["salle"] = salle
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            # Recuperer les matières auxquelles l'enseignants a été émargées pour cette salle
            matieres_emargements = (Emargement.objects.values("matiere_id")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=salle.id)
                                    .annotate(nb_matieres=Count("matiere_id")))
            
            matieres = []
            for me in matieres_emargements:
                dic_matiere = {}
                matiere = Matiere.objects.get(id=me["matiere_id"])
                dic_matiere["matiere"] = matiere
                
                # Recuperer les émargements de l'enseignant
                enseignants_emargements = Emargement.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=se["salle_id"], matiere_id=me["matiere_id"])
                
                nb_absences_par_matiere = 0
                for emargement in enseignants_emargements:
                    nb_absences_par_matiere += Absencestudent.objects.filter(emargement_id=emargement.id).count()
                    
                dic_matiere["nb_absences"] = nb_absences_par_matiere
                matieres.append(dic_matiere)
                
            dic["matieres"] = matieres  
            tabEmargements.append(dic)
        else:
            # Recuperer les matières auxquelles l'enseignants a été émargées pour cette salle
            months_emargements = (Emargement.objects.values("month")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=salle.id)
                                    .annotate(nb_matieres=Count("month")))
            
            months = []
            for me in months_emargements:
                dic_month = {}
                month = me["month"]
                dic_month["month"] = month
                
                # Recuperer les émargements de l'enseignant
                enseignants_emargements = Emargement.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=salle.id, month=month)
                
                nb_absences_par_mois = 0
                for emargement in enseignants_emargements:
                    nb_absences_par_mois += Absencestudent.objects.filter(emargement_id=emargement.id).count()
                    
                dic_month["nb_absences"] = nb_absences_par_mois
                months.append(dic_month)
                
            dic["months"] = months
            tabEmargements.append(dic)
    
    context = {
        "setting": setting,
        "emargements": tabEmargements
    }
    
    return render(request, "abs_students.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def abs_student_user(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    classe_id = request.session.get('classe_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles = Salle.objects.filter(classe_id=classe_id)
    
    absences = []
    for salle in salles:
        dic = {}
        dic["salle"] = salle
        # Recuperer tous les emargements de cette salles
        emargements = Emargement.objects.filter(salle_id=salle.id)
        nb_absences_students = 0
        for emargement in emargements:
            # Compter le nombre d'absence de chaque emargement
            nb_absences_students = nb_absences_students + Absencestudent.objects.filter(emargement_id=emargement.id).count() 
    
        dic["nb_absences_students"] = nb_absences_students
        
        # Compter les motifs des absences d'une classe que le DG n'a pas encore pris la decision
        nombre_motifs_students = 0
        for absence in Absencestudent.objects.filter(status_decision=0).exclude(motif=""):
            if absence.emargement.salle.id == salle.id:
                nombre_motifs_students += 1
        
        dic["nombre_motifs_students"] = nombre_motifs_students
        # Recuperer les absences des élèves
        absences_students = Absencestudent.objects.values("student_id").annotate(nb_abs=Count("student_id"))
        students = []
        for ast in absences_students:
            student = Student.objects.get(id=ast["student_id"])
            # Récuperer l'inscription de l'étudiant
            inscription = Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique_id).first()
            if inscription and (inscription.salle.id == salle.id):
                dic_st = {}
                nb_absence = 0
                nb_motifs_absence = 0
                dic_st["student"] = student
                liste_absences = Absencestudent.objects.filter(student_id=ast["student_id"]).order_by("-id")
                new_absences = []
                for absence in liste_absences:
                    if absence.emargement.salle.id == salle.id:
                        nb_absence += 1
                        if absence.status_decision == 0 and absence.motif:
                            nb_motifs_absence += 1
                        new_absences.append(absence)
                
                dic_st["new_absences"] = new_absences
                dic_st["nb_absences"] = nb_absence
                dic_st["nb_motifs_absence"] = nb_motifs_absence
                students.append(dic_st)               
        dic["students"] = students
        absences.append(dic)
    context = {
        "setting": setting,
        "absences": absences
    }
    
    return render(request, "abs_student_user.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def abs_student_mat_user(request, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'élève
    id = int(dechiffrer_param(str(student_id)))
    student = Student.objects.get(id=id)
    
    inscription = Inscription.objects.filter(student_id=id, anneeacademique_id=anneeacademique_id).first()
    
    emargements_dates = Emargement.objects.values("date_emargement").filter(anneeacademique_id=anneeacademique_id, salle_id=inscription.salle.id).annotate(nb_absences=Count("date_emargement"))
    
    liste_absences = []
    for ed in emargements_dates:    
        emargements = Emargement.objects.filter(date_emargement=ed["date_emargement"])
        dic = {}
        dic["date_emargement"] = ed["date_emargement"] 
        absences = []
        for emargement in emargements:
            query = Absencestudent.objects.filter(emargement_id=emargement.id, student_id=id)
            if query.exists():
                absence = Absencestudent.objects.filter(emargement_id=emargement.id, student_id=id).first()
                absences.append(absence)
        dic["absences"] = absences
        liste_absences.append(dic)
    context = {
        "setting": setting,
        "liste_absences": liste_absences,
        "student": student
    }
    
    return render(request, "abs_student_mat_user.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def mes_absences(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_absences = (Absence.objects.values("salle_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("salle_id")))
    
    tabAbsences = []
    for sa in salles_absences:
        dic = {}
        salle = Salle.objects.get(id=sa["salle_id"])
        dic["salle"] = salle
        if salle.cycle.libelle in ["Collège", "Lycée"]:
            # Recuperer les matières auxquelles l'enseignants a été émargées pour cette salle
            matieres_absences = (Absence.objects.values("matiere_id")
                                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=sa["salle_id"])
                                    .annotate(nb_matieres=Count("matiere_id")))
            
            matieres = []
            for ma in matieres_absences:
                dic_matiere = {}
                matiere = Matiere.objects.get(id=ma["matiere_id"])
                dic_matiere["matiere"] = matiere
                
                # Recuperer les absences de l'enseignant
                enseignants_absences = Absence.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=sa["salle_id"], matiere_id=ma["matiere_id"])
                dic_matiere["absences"] = enseignants_absences
                dic_matiere["nb_absences"] = enseignants_absences.count()
                matieres.append(dic_matiere)
                
            dic["matieres"] = matieres  
            tabAbsences.append(dic)
        else:
            # Regrouper les absences de l'enseignant par mois
            absences_par_month = (
                Absence.objects
                .filter(enseignant_id=user_id, anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                .annotate(month=ExtractMonth('date_absence'))
                .values('month')
                .annotate(nombre_absences=Count('id'))
                .order_by('month')
            )
            
            months = []
            for ma in absences_par_month:
                dic_month = {}
                month = ma["month"]
                dic_month["month"] = format_month(month)
                # Recuperer les absences de l'enseignant
                enseignants_absences = Absence.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id, salle_id=salle.id, date_absence__month=month)
                dic_month["absences"] = enseignants_absences
                dic_month["nb_absences"] = enseignants_absences.count()
                months.append(dic_month)
                
            dic["months"] = months
            tabAbsences.append(dic)
            
        
    # Recuperer les absences de l'enseignant
    absences_enseignants = Absence.objects.filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
    for absence in absences_enseignants:
        # Mise à jour de status pour marquer la lecture
        absence.status = True
        absence.save()
        
    context = {
        "setting": setting,
        "absences": tabAbsences
    }
    
    return render(request, "mes_absences.html", context)

@login_required(login_url='connection/account')
def decision_absence_enseignant(request, enseignant_id, id, status):
    
    absence = Absence.objects.get(id=id)
    absence.status_decision = int(status)
    absence.save()

    return JsonResponse({
        "status": absence.status_decision
    })

@login_required(login_url='connection/account')   
def save_motif_absence(request):
    if request.method == "POST":
        try:
            id = int(request.POST["id"])           
            
            motif = bleach.clean(request.POST["motif"].strip()) 
            type_absence = bleach.clean(request.POST["type_absence"].strip())         
            # Validation des données
            if not all([motif]):
                return JsonResponse({"error": "Données manquantes ou invalides"}, status=400)

            if type_absence == "Enseignant":
                absence = Absence.objects.get(id=id)
                absence.motif = motif
                absence.save()
                
                return JsonResponse({
                        "status": "success",
                        "motif": absence.motif
                })
            else:
                absence = AbsenceAdmin.objects.get(id=id)
                absence.motif = motif
                absence.save()
                
                return JsonResponse({
                        "status": "success",
                        "motif": absence.motif
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_user)
def mes_absences_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    absences = AbsenceAdmin.objects.filter(anneeacademique_id=anneeacademique_id, user_id=user_id)
    for absence in absences:
        absence.status = True
        absence.save()
        
    # Regrouper les absences de l'enseignant par mois
    absences_par_month = (
                AbsenceAdmin.objects
                .filter(user_id=user_id, anneeacademique_id=anneeacademique_id)
                .annotate(month=ExtractMonth('date_absence'))
                .values('month')
                .annotate(nombre_absences=Count('id'))
                .order_by('month')
    )
            
    months_absence = []
    for ma in absences_par_month:
        dic_month = {}
        month = ma["month"]
        dic_month["month"] = format_month(month)
        # Recuperer les absences de l'enseignant
        enseignants_absences = AbsenceAdmin.objects.filter(anneeacademique_id=anneeacademique_id, user_id=user_id, date_absence__month=month)
        dic_month["absences"] = enseignants_absences
        dic_month["nb_absences"] = enseignants_absences.count()
        months_absence.append(dic_month)
                    
    context = {
        "setting": setting,
        "months_absence": months_absence
    }
    
    return render(request, "mes_absences_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def abs_studentmatiere(request, salle_id, matiere_month):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")       
        
    sl_id = int(dechiffrer_param(str(salle_id)))
    salle = Salle.objects.get(id=sl_id)
    if salle.cycle.libelle in ["Collège", "Lycée"]:   
           
        mt_id = int(dechiffrer_param(str(matiere_month)))
        matiere = Matiere.objects.get(id=mt_id)
        
        # Récuperer les étudiants inscris dans la salle ou l'enseignant a été emargé
        inscriptions  = Inscription.objects.filter(
            anneeacademique_id=anneeacademique_id, 
            salle_id=sl_id)
        
        students = []
        for inscription in inscriptions:
            count = 0
            emargements = Emargement.objects.filter(
                anneeacademique_id=anneeacademique_id, 
                salle_id=sl_id, 
                matiere_id=mt_id,
                enseignant_id=user_id) 
    
            absences = []
            for emargement in emargements:            
                query = Absencestudent.objects.filter(student_id=inscription.student.id, emargement_id=emargement.id)
                if query.exists():
                    count += query.count()
                    absences.append(query.first())
            # Verifier si l'élève a au moins une absence
            if count > 0:
                dic = {}
                dic["student"] = inscription.student
                dic["nb_absences"] = count
                dic["absences"] = absences
                
                students.append(dic)
                
        context = {
            "setting": setting,
            "salle": salle,
            "matiere": matiere,
            "students": students
            #"emargements": tabEmargements
        }
        return render(request, "abs_studentmatiere.html", context)
    else:
        month = dechiffrer_param(str(matiere_month))
        # Récuperer les étudiants inscris dans la salle ou l'enseignant a été emargé
        inscriptions  = Inscription.objects.filter(
            anneeacademique_id=anneeacademique_id, 
            salle_id=sl_id)
        
        students = []
        for inscription in inscriptions:
            count = 0
            emargements = Emargement.objects.filter(
                anneeacademique_id=anneeacademique_id, 
                salle_id=sl_id, 
                month=month,
                enseignant_id=user_id) 
    
            absences = []
            for emargement in emargements:            
                query = Absencestudent.objects.filter(student_id=inscription.student.id, emargement_id=emargement.id)
                if query.exists():
                    count += query.count()
                    absences.append(query.first())
            # Verifier si l'élève a au moins une absence
            if count > 0:
                dic = {}
                dic["student"] = inscription.student
                dic["nb_absences"] = count
                dic["absences"] = absences
                
                students.append(dic)
                
        context = {
            "setting": setting,
            "salle": salle,
            "month": month,
            "students": students
            #"emargements": tabEmargements
        }
        return render(request, "abs_studentmatiere.html", context)
    
@unauthenticated_customer  
def save_motif_absence_student(request):
    if request.method == "POST":
        try:
            id = int(request.POST["id"])           
            
            motif = bleach.clean(request.POST["motif"].strip())         
            # Validation des données
            if not all([motif]):
                return JsonResponse({"error": "Données manquantes ou invalides"}, status=400)

            absence = Absencestudent.objects.get(id=id)
            absence.motif = motif
            absence.save()
                
            return JsonResponse({
                    "status": "success",
                    "motif": absence.motif
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)   

@login_required(login_url='connection/account')
def decision_absence_student(request, id, status):
    
    absence = Absencestudent.objects.get(id=id)
    absence.status_decision = int(status)
    absence.save()

    return JsonResponse({
        "status": absence.status_decision
    })


#========================= Gestion de l'absence des administrateurs ===================
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def absences_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    absences_users = AbsenceAdmin.objects.values("user_id").filter(anneeacademique_id=anneeacademique_id).annotate(nb_absences=Count('user_id'))
    liste_absences = []
    for au in absences_users:
        user = User.objects.get(id=au["user_id"])
        dic={}
        dic["user"] = user
        dic["nb_absences"] = au["nb_absences"]
        absences = []
        for absence in AbsenceAdmin.objects.filter(user_id=user.id, anneeacademique_id=anneeacademique_id).order_by("-id"):
            dic_absence = {}
            dic_absence["absence"] = absence
            status_paye = False
            month = recuperer_mois_annee(absence.date_absence) # Récuperer le mois de l'absence 
            if Renumeration.objects.filter(user_id=absence.user.id, month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exists():
                    status_paye = True
            dic_absence["status_paye"] = status_paye
            absences.append(dic_absence)
                    
        dic["absences"] = absences
        # Compter les motifs des absences d'un enseignant que le DG n'a pas encore pris la decision
        nombre_absences_admin = 0
        for abs in AbsenceAdmin.objects.filter(user_id=user.id, status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
                month = recuperer_mois_annee(abs.date_absence) # Récuperer le mois de l'absence 
                if not Renumeration.objects.filter(user_id=abs.user.id, month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exists():
                    nombre_absences_admin += 1
        dic["nombre_motifs_absences"] = nombre_absences_admin
        liste_absences.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "liste_absences": liste_absences,
        "anneeacademique": anneeacademique
    }
    return render(request, "absences_admin.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def add_absence_admin(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")

    if request.method == "POST":
        user_id = request.POST["user"]
        date_absence = request.POST["date_absence"]

        query = AbsenceAdmin.objects.filter(anneeacademique_id=anneeacademique_id, user_id=user_id, date_absence=date_absence)
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette absence existe déjà."})
        else:
            date_actuelle = datetime.now()   
            # Ajouter trois semaines
            date_plus_trois_jours = make_aware(date_actuelle) + timedelta(days=3)  
            absence = AbsenceAdmin(
                anneeacademique_id=anneeacademique_id, 
                user_id=user_id, 
                admin_id=request.user.id, 
                date_absence=date_absence,
                date_limite=date_plus_trois_jours)
            
            # Nombre d'absences avant l'ajout
            count0 = AbsenceAdmin.objects.all().count()
            absence.save()
            # Nombre d'absences après l'ajout
            count1 = AbsenceAdmin.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Absence enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'insertion a échouée."})     
    
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    admin = []
    roles = EtablissementUser.objects.filter(etablissement=etablissement)                
    for role in roles:
        if role.user not in admin and role.group.name in ['Directeur Général', 'Directeur des Etudes', 'Surveillant Général', 'Gestionnaire']:
            admin.append(role.user)
    
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()      
    context = {
        "setting": setting,
        "users": admin,
        "contrat": contrat
    }
    return render(request, "add_absence_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_absence_admin(request,id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    absence_id = int(dechiffrer_param(str(id)))
    absence = AbsenceAdmin.objects.get(id=absence_id)
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    roles = EtablissementUser.objects.filter(etablissement=etablissement).exclude(user=absence.user)  
    admin = []             
    for role in roles:
        if role.user not in admin and role.group.name in ['Directeur Général', 'Directeur des Etudes', 'Surveillant Général', 'Gestionnaire']:
            admin.append(role.user)
    
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()          
    context = {
        "setting": setting,
        "absence": absence,
        "users": admin,
        "contrat": contrat
    }
    return render(request, "edit_absence_admin.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def edit_aa(request):
    
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            absence = AbsenceAdmin.objects.get(id=id)
        except:
            absence = None

        if absence is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            user_id = request.POST["user"]
            date_absence = request.POST["date_absence"]
            motif = bleach.clean(request.POST["motif"].strip())
            #On verifie si cette classe a déjà été associée à une série
            litse_absences = AbsenceAdmin.objects.exclude(id=id)
            salles = []
            for a in litse_absences: 
                dic = {} 
                dic["user_id"] = int(a.user.id)
                dic["date_absence"] = a.date_absence
                salles.append(dic)
                
            new_dic = {}
            new_dic["user_id"] = int(user_id)
            new_dic["date_absence"] = date_absence
                        
            #On verifie si cette absence existe
            if new_dic in salles:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette absence existe déjà."})
            else:
                absence.user_id = user_id
                absence.date_absence = date_absence
                absence.motif = motif
                absence.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Absence modifiée avec succès."})


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_directeur_etudes)
def del_absence_admin(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("gettings/maintenance")
    
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    if contrat and contrat.status_signature:
        try:
            absence_id = int(dechiffrer_param(str(id)))
            absence = AbsenceAdmin.objects.get(id=absence_id)
        except:
            absence = None
            
        if absence:
            # Nombre d'absences avant la suppression
            count0 = AbsenceAdmin.objects.all().count()
            absence.delete()
            # Nombre d'absences après la suppression
            count1 = AbsenceAdmin.objects.all().count()
            if count1 < count0: 
                messages.success(request, "ELément supprimé avec succès.")
            else:
                messages.error(request, "La suppression a échouée.")
            return redirect("absences_admin")
    else:
        messages.error(request, "Veuillez signer votre contrat avant de procéder à la suppression d’un programme.")
        return redirect("absences_admin")

def ajax_delete_absence_admin(request, id):
    absence = AbsenceAdmin.objects.get(id=id)
    context = {
        "absence": absence
    }
    return render(request, "ajax_delete_absence_admin.html", context)


def modal_decision_absence(request, id):
    absence = AbsenceAdmin.objects.get(id=id)
    
    return JsonResponse({
       "id": absence.id,
       "status_decision": absence.status_decision,
       "motif": absence.motif
    })
    
@login_required(login_url='connection/account')
def decision_absence_admin(request, id, status):
    anneeacademique_id = request.session.get('anneeacademique_id')
    absence = AbsenceAdmin.objects.get(id=id)
    # Compter les motifs des absences d'un enseignant que le DG n'a pas encore pris la decision
    nombre_absences_admin = 0
    for abs in AbsenceAdmin.objects.filter(user_id=absence.user.id, status_decision=0, anneeacademique_id=anneeacademique_id).exclude(motif=""):
        month = recuperer_mois_annee(abs.date_absence) # Récuperer le mois de l'absence 
        if not Renumeration.objects.filter(user_id=abs.user.id, month=month, type_renumeration="Administrateur scolaire", anneeacademique_id=anneeacademique_id).exists():
            nombre_absences_admin += 1
                   
    if absence.status_decision == 0:
        nombre_absences_admin = nombre_absences_admin - 1

    absence.save()
    return JsonResponse({
        "status": absence.status_decision,
        "nombre_absences_admin": nombre_absences_admin,
        "adminId": absence.user.id
    })