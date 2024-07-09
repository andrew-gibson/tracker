import datetime
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
from .time_utils import get_last_n_weeks
from . import models

api = API(namespace="project", session={})


def _whoami(request):
    prepare_qs, projection = models.ProjectUser.readers(request, pk=request.user.pk)
    prepared_user = prepare_qs(models.ProjectUser.objects.filter(id=request.user.id))
    return projection(prepared_user.first())


@api.get("whoami/")
def whoami(request):
    return JsonResponse(_whoami(request))


@api.get("model_info/")
def model_info(request):
    resp =          {
            "user": {
                "main": "/project/whoami/",
                "filters": [],
                "data": _whoami(request),
                "refresh_time": datetime.datetime.now().timestamp(),
            },
            **{
                m._meta.label: m.model_info(request)
                for m in apps.get_models()
                if hasattr(m, "model_info") and m._meta.app_label == "project"
            },
        } 
    return JsonResponse(
       resp
    )


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
    update = bool(request.GET.get("update", False))
    myreports = models.TimeReport.user_filter(request).all()
    weeks = get_last_n_weeks(20)
    for week in weeks:
        week["total"] = float(request.project_user.settings(request)["work_hours"])
        week["worked"] = float(
            sum(
                x.time
                for x in myreports
                if x.week.strftime("%Y-%m-%d") == week["week_start"]
            )
        )
    if update:
        return JsonResponse(weeks, safe=False)
    return render(
        request,
        "timereport/timereports.html",
        {
            "standalone": not request.htmx,
            "weeks": weeks,
        },
    )
