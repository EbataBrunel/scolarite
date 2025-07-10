from django.shortcuts import redirect
from django.http import HttpResponse
from etablissement.models import Etablissement
from django.contrib.auth.models import Group

def unauthenticated_user(views_func):
    def wrapper_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connection/login_user")
        else:
            return views_func(request, *args, **kwargs)
    return wrapper_func

def unauthenticated_customer(views_func):
    def wrapper_func(request, *args, **kwargs):
        if not request.session.get('student_id') and not request.session.get('parent_id'):
            return redirect("connection/connexion")
        else:
            return views_func(request, *args, **kwargs)
    return wrapper_func

def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            
            etablissement_id = request.session.get('etablissement_id')
            groups = []
            if etablissement_id:
                etablissement = Etablissement.objects.get(id=etablissement_id)            
                user = request.user
                if etablissement.groups.filter(user=user).exists():
                    list_groups = etablissement.groups.filter(user=user)
                    for group in list_groups:
                        groups.append(group)
                else:
                    list_groups = etablissement.groups.all()
                    for group in list_groups:
                        groups.append(group)
                        
                    g = Group.objects.get(name="Super user")
                    groups.append(g)
            else:
                user = request.user
                if user.groups.exists():
                    list_groups = user.groups.all()
                    for group in list_groups:
                        groups.append(group)
            status = False
            for group in groups:
                if group.name in allowed_roles:
                    status = True
                    break
            if status: 
               return view_func(request, *args, **kwargs)
            else: 
                return redirect("settings/authorization") #Vous n'êtes pas autorisés à acceder à cette page"
        
        return wrapper_func
    return decorator

def only_admin(view_func):
    def wrapper_func(request, *args, **kwargs):
        group = None
        if request.user.groups.exists():
            group=request.user.groups.all()[0].name

        if group=="customer":
            return redirect("home")   
        if group=="admin" or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            #return HttpResponse("Vous n'êtes pas autorisés à acceder à cette page")
            return redirect("settings/db")
    return wrapper_func
            