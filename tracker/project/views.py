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
from . import models

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
    update = bool(request.GET.get("update",False))
    myreports = models.TimeReport.user_filter(request).all()
    weeks =  get_last_n_weeks(20)
    for week in weeks:
        week["total"] = float(request.project_user.settings(request)["work_hours"])
        week["worked"] = float(sum(x.time for x in myreports if x.week.strftime("%Y-%m-%d") == week["week_start"]))
    if update:
       return JsonResponse(weeks,safe=False) 
    return render(
        request,
        "timereport/timereports.html",
        {
            "standalone": not request.htmx,
            "weeks" : weeks,
        },
    )

