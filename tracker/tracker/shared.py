from django.contrib import admin
from django import forms

class AdminForm(forms.ModelForm):
    """ admin forms by default have 0 required fields and must declare required fields as 
    class Meta:
      required = [ field1_name, .... ]
  
  """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            if not (hasattr(self.Meta, "required") and name in self.Meta.required):
                self.fields[name].required = False

            if isinstance(self.fields[name], forms.models.ModelMultipleChoiceField):
                self.fields[name].widget.widget.attrs[
                    "style"
                ] = "min-width:100%;width:100%;"

class ModelAdmin(admin.ModelAdmin):
    form = AdminForm

    def get_actions(self, request):
        actions = super().get_actions(request)
        return actions



def add_to_admin(cls):
    cls.__add_to_admin = True
    return cls

class classproperty:
    def __init__(self, func):
        self.fget = func
    def __get__(self, instance, owner):
        return self.fget(owner)
