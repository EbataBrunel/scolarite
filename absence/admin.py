from django.contrib import admin
from absence.models import Absence, AbsenceAdmin, Absencestudent

admin.site.register(Absence)
admin.site.register(AbsenceAdmin)
admin.site.register(Absencestudent)
