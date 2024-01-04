import time
import json
import aiohttp

from .utils import (
    API,
    assert_or_404,
    get_model_or_404,
    get_related_model_or_404,
    link_or_404,
    render,
    unlink_or_404,
)
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
from .rest import AutoCompleteNexus

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


@api.get_post_delete_put(["m/<str:m>/", "m/<str:m>/<int:pk>/"])
def rest(request, m="", pk=None):
    session, set_session = api.get_url_session(request)
    model = get_model_or_404(m)
    if not model:
        return HttpResponseBadRequest()
    if request.method == "GET":
        return model.GET(request, pk)
    if request.method == "POST" and not pk:
        return model.POST(request)
    if request.method == "PUT" and pk:
        return model.PUT(request, pk)
    if request.method == "DELETE" and pk:
        return model.DELETE(request, pk)
    return HttpResponseBadRequest()


@api.post(["parse_for_links/<str:m>/<str:attr>/"])
def parse_for_links(request, m, attr):
    model = get_model_or_404(m, test=lambda m: issubclass(m, (AutoCompleteNexus,)))
    remainder = text_input = request.POST.get("payload")
    fields = model.get_autocompletes()
    results = {
        f.name: {
            "trigger": f.related_model.text_search_trigger,
            "model": f.related_model,
            "name": f.name,
            "many_to_many": f.many_to_many,
            "search_terms": model.find_words_from_trigger(
                text_input, f.related_model.text_search_trigger, many=f.many_to_many
            ),
        }
        for f in fields
    }

    for name in results:
        results[name]["results"] = [
            [term, results[name]["model"].ac(request, term)]
            for term in results[name]["search_terms"]
        ]

    model.cls_text_scan(
        text_input, results
    )  # default is nothing happens, but classes can add extra scanning, for example: dates

    for name in results:
        for parsed in results[name]["search_terms"]:
            remainder = remainder.replace(parsed, "")
        remainder = remainder.replace(results[name]["trigger"], "")


    return render(
        request,
        f"show_parsed_links.html",
        {"results": results, "remainder": remainder, "attr": attr,"anything_removed" : remainder != text_input },
    )


@api.post_get(["create_from_parsed/<str:m>/<str:attr>/"])
def create_from_parsed(request, m, attr):
    model = get_model_or_404(m, test=lambda m: issubclass(m, (AutoCompleteNexus,)))
    if request.method == "POST":
        text_input = request.POST.get("payload")

    return render(
        request, f"parse_for_links.html", {"attr": attr, "m": m, "model": model}
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
    obj1 = get_object_or_404(model1.belongs_to_user(request), pk=pk1)
    obj2 = get_object_or_404(model2.belongs_to_user(request), pk=pk2)
    if request.method == "POST":
        link_or_404(obj1, obj2, attr)
    if request.method == "DELETE":
        unlink_or_404(obj1, obj2, attr)
    projection = model1.readers[1]
    return JsonResponse(projection(obj1))


@api.post(
    [
        "m2m/<str:m1>/<int:pk1>/<str:m2>/",
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<str:attr>/",
    ]
)
async def post_and_link(request, m1, pk1, m2, attr=""):
    headers = {
        "Json-Response": "true",
        "X-Csrftoken": request.headers["X-Csrftoken"],
        "Cookie": request.headers["Cookie"],
    }
    create_url = (
        "http://" + request.headers["Host"] + reverse("core:rest", kwargs={"m": m2})
    )
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(create_url, data=request.POST) as r:
            if r.ok:
                resp_dict = await r.json()
            else:
                return HttpResponseBadRequest()

        url_kwargs2 = {
            "m1": m1,
            "pk1": pk1,
            "pk2": resp_dict["id"],
            "m2": m2,
            "attr": attr,
        }
        link_url = (
            "http://"
            + request.headers["Host"]
            + reverse("core:toggle_link", kwargs=url_kwargs2)
        )
        async with session.post(link_url) as r:
            if r.ok:
                return JsonResponse(await r.json())
            else:
                return HttpResponseBadRequest()


@api.post(["text_ac/<str:m>/<int:pk>/<str:attr>/"])
def text_ac(request, m, pk, attr):
    model = get_model_or_404(m, test=lambda m: issubclass(m, (AutoCompleteNexus,)))
    obj = get_object_or_404(model.belongs_to_user(request), pk=pk)
    q = list(request.POST.values())[0]
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
            "results": related_model.ac(request, q, optional_projection=projection),
        }
    )


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
        c["selected"]: list = request.POST.getlist(f"id_{attr}")
    else:
        c["selected"]: list = [
            {
                "name": str(x),
                "id": x.pk,
            }
            for x in getattr(c["instance"], attr).all()
        ]

    c["q"] = request.POST.get("q")

    raw_q_results = c["related_model"].ac(request, c["q"]) if c["q"] else []

    c["results"] = (
        c["related_model"].ac(request, c["q"], filter_qs=~Q(id__in=c["selected"]))
        if c["q"]
        else []
    )

    c["already_selected"] = len(raw_q_results) and not len(c["results"])
    return c


@api.get(
    [
        "sel_setup/<str:m>/<int:pk>/<str:attr>/",
        "sel_setup/<str:m>/<str:attr>/",
    ]
)
def sel_setup(request, m: str = None, pk: int = None, attr: str = None):
    c: dict = parse_lookup_args(request, m, pk, attr)
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
    related_model: models.Model = c["related_model"]
    # the ac will return an array of [{"id" : , "name" : }]
    c["create_new"] = reverse("core:rest", kwargs={"m": related_model._meta.label})
    return render(request, "typeahead_results.html", c)
