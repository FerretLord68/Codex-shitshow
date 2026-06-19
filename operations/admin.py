from django.contrib import admin

from .models import ApplicationSetting, BackgroundJob, FeatureFlag, ServiceHeartbeat

admin.site.register(FeatureFlag)
admin.site.register(ApplicationSetting)
admin.site.register(BackgroundJob)
admin.site.register(ServiceHeartbeat)

