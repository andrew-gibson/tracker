import time
import dateparser
import json

from .utils import (
    API,
    assert_or_404,
    get_model_or_404,
    get_related_model_or_404,
    link_or_404,
    render,
    unlink_or_404,
    refetch,
)
from django.apps import apps
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, aget_object_or_404, redirect, render
from django.urls import reverse
from django.utils import safestring
from django.views.decorators.csrf import ensure_csrf_cookie
from text.translate import gettext_lazy as _

from . import models
from tracker import jinja2
from .core import AutoCompleteNexus

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


@api.get_post_delete_put(
    [
        "m/<str:m>/",
        "m/<str:m>/<int:pk>/",
    ]
)
def main(request, m="", pk=None):
    session, set_session = api.get_url_session(request)
    model = get_model_or_404(m)
    if not model:
        return HttpResponseBadRequest()
    match [request.method, pk]:
        case ["GET", _]:
            return model.GET(request, pk)
        case ["POST", None]:
            return model.POST(request)
        case ["PUT", int()]:
            return model.PUT(request, pk)
        case ["DELETE", int()]:
            return model.DELETE(request, pk)
        case _:
            return HttpResponseBadRequest()


@api.get("model_info/")
def model_info(request):
    return JsonResponse(
        {
            m._meta.label: m.model_info
            for m in apps.get_models()
            if hasattr(m, "model_info")
        }
    )


@api.post_get("create_from_parsed/<str:m>/<str:attr>/")
def create_from_parsed(request, m, attr, suppress_links=""):
    model = get_model_or_404(m, test=lambda m: issubclass(m, AutoCompleteNexus))
    ctx = {"attr": attr, "m": m, "params": request.GET.urlencode(), "model": model}
    if request.method == "POST":
        parse_payload = model.parse_text(request)
        obj = model.save_from_parse(
            request, parse_payload["results"], attr, parse_payload["remainder"]
        )
        return render(
            request,
            f"parse_for_links.html",
            ctx,
        )
    return render(
        request,
        "parse_for_links.html",
        ctx,
    )


@api.get("parse_for_links/<str:m>/<str:attr>/")
def parse_for_links(request, m, attr):
    model = get_model_or_404(m, test=lambda m: issubclass(m, AutoCompleteNexus))
    return render(
        request,
        f"show_parsed_links.html",
        {"attr": attr, "m": m.replace(".", "-"), **model.parse_text(request)},
    )


@api.post_delete(
    [
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<int:pk2>/",
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<int:pk2>/<str:attr>/",
    ]
)
def toggle_link(request, m1, pk1, m2, pk2, attr=""):
    model1 = get_model_or_404(m1)
    model2 = get_model_or_404(m2)
    obj1, _ = model1.get_projection_by_pk(request, pk1)
    obj2, _ = model2.get_projection_by_pk(request, pk2)
    if request.method == "POST":
        link_or_404(obj1, obj2, attr)
    if request.method == "DELETE":
        unlink_or_404(obj1, obj2, attr)
    projection = model1.readers(request)[1]
    return JsonResponse(projection(obj1))


@api.post(
    [
        "m2m/<str:m1>/<int:pk1>/<str:m2>/",
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<str:attr>/",
    ]
)
async def post_and_link(request, m1, pk1, m2, attr=""):
    # create the new m2
    resp = await refetch(
        request,
        url_name="core:main",
        url_kwargs={"m": m2},
        method="POST",
        payload=request.POST,
    )
    if r.ok:
        resp_dict = await resp.json()
    else:
        return HttpResponseBadRequest()

    # now link the new lookup to m1
    reap2 = await refetch(
        request,
        url_name="core:toggle_link",
        url_kwargs={
            "m1": m1,
            "pk1": pk1,
            "pk2": resp_dict["id"],
            "m2": m2,
            "attr": attr,
        },
        method="POST",
    )
    if resp2.ok:
        return JsonResponse(await resp2.json())
    else:
        return HttpResponseBadRequest()


@api.GET(["text_ac/<str:m>/<int:pk>/<str:attr>/", "text_ac/<str:m>/__pk__/__attr__/"])
def text_ac(request, m, pk, attr):
    try:
        filters = json.loads(request.GET.get("filters", "{}"))
        q = request.GET.get("q")
    except:
        return HttpResponseBadRequest("incorrectly formatted GET params")
    model = get_model_or_404(m, test=lambda m: issubclass(m, (AutoCompleteNexus,)))
    obj = get_object_or_404(model.user_filter(request), pk=pk)
    f = model._meta.get_field(attr)
    related_model = f.related_model

    def projection(d):
        if d.get("new", False):
            url = reverse(
                "core:post_and_link",
                kwargs={
                    "m1": model._meta.label,
                    "pk1": pk,
                    "m2": related_model._meta.label,
                    "attr": attr,
                },
            )
        else:
            url = reverse(
                "core:toggle_link",
                kwargs={
                    "m1": model._meta.label,
                    "pk1": pk,
                    "m2": related_model._meta.label,
                    "pk2": d["id"],
                    "attr": attr,
                },
            )

        return {**d, "url": url}

    return JsonResponse(
        {
            "name": f.name,
            "many_to_many": f.many_to_many,
            "results": related_model.ac(
                request, q, optional_projection=projection, filter_qs=Q(**filters)
            ),
        }
    )


@api.GET(["dateparse/"])
def dateparse(request):
    date = dateparser.parse(request.GET.get("q"))
    if date:
        return HttpResponse(date.date().isoformat())
    else:
        return HttpResponse("")
