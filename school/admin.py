from django.contrib import admin

from .models import*

admin.site.site_header="EAJC School"
admin.site.site_title="CV"
admin.site.index_title="EAJC"


admin.site.register(Setting)
admin.site.register(SettingSupUser)
