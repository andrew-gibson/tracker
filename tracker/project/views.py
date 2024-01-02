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

from .models import Contact, Project, Tag, Team, Stream, StreamWork, Model
from core.rest import RESTModel

api = API(namespace="project", session={})
'''
    tags_typeahead = {
        "m": "project.Project",
        "attr": "tags",
    }
    teams_typeahead = {
        "m": "project.Project",
        "attr": "teams",
    }
    if project.pk:
        tags_typeahead["pk"] = project.pk
        teams_typeahead["pk"] = project.pk

    "tags_typeahead": reverse("core:sel_setup", kwargs=tags_typeahead),
    "teams_typeahead": reverse("core:sel_setup", kwargs=teams_typeahead),
'''

@api.get("main/")
def main(request):
    return render(
        request,
        "project/main.html",
        {
            "project_form": Project.form(request)(),
            "stream_work_form"  :  StreamWork.form(request)() ,
            "Project" : Project,
            "StreamWork" : StreamWork,
        },
    )

@api.get("projects/")
def projects(request):
    return render(
        request,
        "project/projects.html",
        {"models" : RESTModel.rest_models },
    )

