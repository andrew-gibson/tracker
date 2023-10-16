import json

from core.utils import (API, assert_or_404, get_model_or_404,
                        get_related_model_or_404, link_m2m_or_404, render,
                        unlink_m2m_or_404)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         JsonResponse, QueryDict)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from text.translate import gettext_lazy as _

from . import models
from .utils import API

api = API(namespace="core")


@api.post_get("login/", require_login=False)
@ensure_csrf_cookie
def _login(request):
    if request.headers.get("Content-Type", "text/plain") == "application/json":
        if request.method == "POST":
            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return HttpResponse(
                    json.dumps({"status": "success"}), content_type="application/json"
                )
        else:
            return HttpResponse(
                json.dumps({"status": "failure"}), content_type="application/json"
            )
    else:
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse(user.login_redirect))
        return render(request, "login.html", {})


@api.post_get("logout/")
def _logout(request):
    logout(request)
    return render(request, "login.html", {})


def parse_lookup_args(
    request,
    m: str = None,
    pk: int = None,
    attr: str = None,
) -> dict:
    c: dict = {
        "attr": attr,
        "m": m,
        "model": get_model_or_404(m, test=lambda m: hasattr(m, attr)),
    }
    if pk:
        c["pk"] = pk
    c["related_model"], c["rel"] = get_related_model_or_404(
        c["model"], attr, test=lambda m: hasattr(m, "ac")
    )
    c["instance"] = get_object_or_404(c["model"], pk=pk) if pk else None

    def make_url(view_name):
        kwargs = {k: c[k] for k in ["pk", "m", "attr"] if k in c}
        return reverse(view_name, kwargs=kwargs)

    c["make_url"] = make_url

    if f"id_{attr}" in request.POST:
        c["selected"]: list = [
            {"__path__": request.path, **json.loads(x)}
            for x in request.POST.getlist(f"id_{attr}")
        ]
    else:
        c["selected"] = [
            {
                "name": str(x),
                "id": x.pk,
                "__path__": c["make_url"]("core:lookup_toggle"),
            }
            for x in getattr(c["instance"], attr).all()
        ]
    c["selected_ids"] = [x["id"] for x in c["selected"]]
    c["q"] = request.POST.get("q")
    c["results"] = (
        c["related_model"].ac(request, c["q"], filter_qs=~Q(id__in=c["selected_ids"]))
        if c["q"]
        else []
    )
    return c


@api.get(
    [
        "lkp_setup/<str:m>/<int:pk>/<str:attr>/",
        "lkp_setup/<str:m>/<str:attr>/",
    ]
)
def lookup_setup(request, m: str = None, pk: int = None, attr: str = None):
    c: dict = parse_lookup_args(request, m, pk, attr)
    url_kwargs = {"m": m, "attr": attr}
    if pk:
        url_kwargs["pk"] = pk
    return render(request, "typeahead.html", c)


@api.get_post(
    [
        "lkp/<str:m>/<int:pk>/<str:attr>/",
        "lkp/<str:m>/<str:attr>/",
    ]
)
def m2m_lookup(
    request,
    m: str = None,
    pk: int = None,
    attr: str = None,
):
    # remap the currently selected objects to {"id" : , "name" : }
    c: dict = parse_lookup_args(request, m, pk, attr)
    # the ac will return an array of [{"id" : , "name" : }]
    c["hx_swap_oob"] = True
    for result in c["results"]:
        result["__path__"] = c["make_url"]("core:lookup_toggle")

    return render(request, "typeahead_results.html", c)


@api.post(
    [
        "lkp_toggle/<str:m>/<int:pk>/<str:attr>/",
        "lkp_toggle/<str:m>/<str:attr>/",
    ]
)
def lookup_toggle(
    request,
    m: str = None,
    pk: int = None,
    attr: str = None,
):
    c: dict = parse_lookup_args(request, m, pk, attr)
    try:
        toggle_obj: dict = json.loads(request.POST.get("obj"))
    except:
        raise Http404("incorrect post parameters")

    c["hx_swap_oob"] = True
    if toggle_obj["id"] in c["selected_ids"]:
        c["selected"] = [x for x in c["selected"] if x["id"] != toggle_obj["id"]]
        return api.add_header(
            render(request, "typeahead_selected.html", c),
            "HX-Trigger-After-Settle",
            f"refreshQResults{m.replace('.','')}{attr}",
        )
    else:
        c["selected"] = [*c["selected"], toggle_obj]
        return render(request, "typeahead_selected.html", c)
