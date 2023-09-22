from django import apps
from django.contrib import admin

from core.utils import ModelAdmin

# Register your models here.
this_app = apps.registry.apps.all_models["core"]

for model in this_app.values():
    if hasattr(model, "__add_to_admin"):
        if hasattr(model, "adminClass"):
            admin.site.register(model, model.adminClass)

        else:
            admin.site.register(model, ModelAdmin)
