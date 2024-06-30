from django.apps import apps
from django.contrib.auth.models import AnonymousUser


def add_project_user_middleware(get_response):
    ProjectUser = apps.get_model("project.ProjectUser")
    User = apps.get_model("core.User")

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if not isinstance(request.user, AnonymousUser):
            request.project_user = (
                ProjectUser.objects.prefetch_related(
                    "manages__children__children__children__children"
                )
                .prefetch_related("belongs_to__children__children__children__children")
                .get(pk=request.user.pk)
            )
            request.user = (
                User.objects.prefetch_related(
                    "manages__children__children__children__children"
                )
                .prefetch_related("belongs_to__children__children__children__children")
                .get(pk=request.user.pk)
            )
        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
