from django.contrib import admin
from .models import Profile, Parent, Student, EtablissementUser

admin.site.register(Profile)
admin.site.register(Parent)
admin.site.register(Student)
admin.site.register(EtablissementUser)
