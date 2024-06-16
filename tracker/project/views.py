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
from .time_utils import  get_last_n_weeks

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    return render(
        request,
        "shared/main.html",
        {
            "standalone": not request.htmx,
        },
    )

@api.get("metadata/")
def metadata(request):
    return render(
        request,
        "shared/metadata.html",
        {
            "standalone": not request.htmx,
        },
    )

@api.get("timereporting/")
def timereporting(request):
    return render(
        request,
        "timereport/timereports.html",
        {
            "standalone": not request.htmx,
            "weeks" : get_last_n_weeks(20),
        },
    )

