import json
from core.utils import (
    API,
    render,
    assert_or_404,
    get_model_or_404,
)
from django.apps import apps
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
    QueryDict,
    Http404,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from text.translate import gettext_lazy as _

from .models import Contact, Project, Tag, Team, Stream, Task, Model
from core.rest import RESTModel

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    return render(
        request,
        "project/main.html",
        {
            "project_form": Project.form(request)(),
            "task_form"  :  Task.form(request)() ,
            "Project" : Project,
            "Task" : Task,
            "standalone": not request.htmx,
        },
    )


