from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project"
    
    def ready(self):
        from . import permissions
        self.permissions = permissions
        from . import colours
        for model,colour in colours.get_model_colour_map().items():
            setattr(model,"__hex__",colour[0])
            setattr(model,"__rgba__",colour[1])
        
