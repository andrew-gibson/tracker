from django.apps import apps


def add_project_user_middleware(get_response):
    ProjectUser = apps.get_model("project.ProjectUser")

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        request.project_user = ProjectUser.objects.get(pk=request.user.pk)
        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
