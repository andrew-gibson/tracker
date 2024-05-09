import aiohttp
import asyncio
import binascii
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, make_dataclass
from functools import wraps
from urllib import parse

import bleach
import mistune
import pytz
from asgiref.sync import sync_to_async
from dateutil.relativedelta import *
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required, permission_required
from django.forms.models import ModelChoiceField
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render as _render
from django.shortcuts import resolve_url
from django.template import engines
from django.urls import path, re_path, reverse
from django.utils.safestring import mark_safe
from text.translate import gettext_lazy as _
from tracker.jinja2 import encode_get_param, decode_get_params

ALLOWED_TAGS = ["li", "ol", "ul", "p", "br", "span"]


class AdminForm(forms.ModelForm):
    """admin forms by default have 0 required fields and must declare required fields as
    class Meta:
      required = [ field1_name, .... ]

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            if not (hasattr(self.Meta, "required") and name in self.Meta.required):
                self.fields[name].required = False

            if isinstance(self.fields[name], forms.models.ModelMultipleChoiceField):
                self.fields[name].widget.widget.attrs[
                    "style"
                ] = "min-width:100%;width:100%;"


class ModelAdmin(admin.ModelAdmin):
    form = AdminForm

    def get_actions(self, request):
        actions = super().get_actions(request)
        return actions


def add_to_admin(cls):
    cls.__add_to_admin = True
    return cls


class classproperty:
    """
    allows for a property to be a deined on a class
    """

    def __init__(self, func):
        self.fget = func

    def __get__(self, instance, owner):
        return self.fget(owner)


def flatten(lst):
    """
    flattens a list:
    nested_list = [[1, 2, [3, 4]], [5, 6], 7]
    flat_list = list(flatten(nested_list))
    """
    for item in lst:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


def assert_or_404(condition):
    try:
        assert condition
    except:
        raise Http404("Incorrect request")


async def refetch(
    request, url="", url_name="", url_kwargs=None, method="GET", payload=None
):
    headers = {
        "Json-Response": "true",
        "X-Csrftoken": request.headers["X-Csrftoken"],
        "Cookie": request.headers["Cookie"],
    }
    url = "http://" + request.headers["Host"] + reverse(url_name, kwargs=url_kwargs)

    async with aiohttp.ClientSession(headers=headers) as session:
        match method:
            case "POST":
                async with session.post(url, data=request.POST) as r:
                    if r.ok:
                        return r
                    else:
                        return HttpResponseBadRequest()
            case "PUT":
                pass
            case "GET":
                pass
            case "DELETE":
                pass


def get_related_model_or_404(m, attr, test=lambda x: True):
    try:
        rel = m._meta.get_field(attr)
        assert test(rel.related_model)
        return rel.related_model, rel
    except:
        raise Http404("No Model matches the given query")


def find_linking_attr(o1, o2, attr=None):
    try:
        if not attr:
            relations = get_related_model_or_404(o1, o2)
            for m2m_rel in o1.__class__._meta.many_to_many:
                if m2m_rel.related_model == o2.__class__:
                    attr = rel.name
        if not attr:
            raise Exception
        rel = o1.__class__._meta.get_field(attr)
        return attr, rel
    except:
        raise Http404("No Model matches the given query")


def link_or_404(o1, o2, attr=None):
    attr, rel = find_linking_attr(o1, o2, attr)
    if rel.many_to_many or rel.one_to_many:
        getattr(o1, attr).add(o2)
    else:
        setattr(o1, attr, o2)
        o1.save()


def unlink_or_404(o1, o2, attr=None):
    attr, rel = find_linking_attr(o1, o2, attr)
    if rel.many_to_many or rel.one_to_many:
        getattr(o1, attr).remove(o2)
    elif rel.null:
        setattr(o1, attr, None)
        o1.save()
    else:
        raise Http404("models could not be unlinked")



def get_model_or_404(s, test=lambda x: True):
    try:
        assert not any(
            x in s.split(".")[0]
            for x in (
                "django_extensions",
                "admin",
                "contenttypes",
                "auth",
                "sessions",
                "messages",
                "staticfiles",
            )
        )
        model = apps.get_model(s)
        assert test(model)
        return model
    except:
        raise Http404("No Model matches the given query")


def render(
    request, template_name, context=None, content_type=None, status=None, using=None
):
    response = _render(request, template_name, context, content_type, status, using)
    if settings.TESTING:
        setattr(response, "__context__", context)
    return response


def sanitize_html(html_str, allow_weird_characters=False):
    with_terrible_replacements = bleach.clean(html_str, tags=ALLOWED_TAGS)
    # see https://github.com/mozilla/bleach/issues/192
    if allow_weird_characters:
        return with_terrible_replacements.replace("&amp;", "&")
    else:
        return with_terrible_replacements


def is_md_valid(md_str):
    markdown_from_src = mistune.create_markdown()
    unsanitized = markdown_from_src(str(md_str))
    sanitized = sanitize_html(unsanitized)
    return unsanitized == sanitized


def markdown(md_str):
    """
    mark_safe being run through bleach
    """
    render_markdown = mistune.create_markdown()
    return mark_safe(sanitize_html(render_markdown(str(md_str))))


HXTRIGGER = "HX-Trigger-After-Settle"


def get_html(request, template_path, context=None):
    # this method directly hands an html file over via an httpresponse
    backend = engines["jinja2"]
    template_object = backend.get_template(template_path)
    rendering = template_object.render(context=context, request=request)
    return HttpResponse(rendering, None, None)


eastern_timezone = pytz.timezone("Canada/Eastern")

POSTRequest = make_dataclass(
    "Request", ["data", ("method", str, field(default="POST"))]
)


METHODS = ["GET", "PUT", "PATCH", "DELETE", "POST"]


def user_passes_test(
    test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME
):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_view(request, *args, **kwargs):
            if await test_func(request.user):
                return await view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = parse.urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = parse.urlparse(path)[:2]
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login

            return await sync_to_async(redirect_to_login)(
                path, resolved_login_url, redirect_field_name
            )

        return _wrapped_view

    return decorator


def async_permission_required(
    function=None,
    permission_required=None,
    redirect_field_name=REDIRECT_FIELD_NAME,
    login_url=None,
):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """

    @sync_to_async
    def has_permission(u):
        return all(u.has_perm(p) for p in permission_required)

    actual_decorator = user_passes_test(
        has_permission,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def async_login_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """

    @sync_to_async
    def is_authenticated(u):
        return u.is_authenticated

    actual_decorator = user_passes_test(
        is_authenticated,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator



@dataclass
class API:
    urlpatterns: list = field(default_factory=list)
    session: dict = field(default_factory=dict)
    namespace: str = field(default_factory=lambda: "api")
    permissions: list = field(default_factory=list)

    @staticmethod
    def methods_checker(methods, request):
        return any(request.method == m for m in methods)

    @staticmethod
    def method_checker(method, request):
        return request.method == method

    def encode_session(self, session_dict):
        jsonb = json.dumps(session_dict).encode("utf-8")
        return base64.urlsafe_b64encode(jsonb)

    def build_session_url(self, request, session_dict):
        s_b64_jsonb = self.encode_session(session_dict)
        encode_get_param(request.GET, "s", session_dict)
        return "?".join([url, s_b64_jsonb])

    def current_url(self, request):
        return parse.urlsplit(
            request.headers.get("HX-Current-URL", request.build_absolute_uri())
        )

    def load_session_data(self, request):
        return decode_get_params(request.GET).get("s",self.session)

    def parse_referer(self, request):
        return parse.urlsplit(request.headers.get("Referer", ""))

    def get_url_session(self, request):
        # works in conjunction with htmx
        # use base64 and json to store session info in the url
        
        if len(request.GET.keys()) == 0:
            # make copy of session dict so it can be modified
            session = json.loads(json.dumps(self.session))
        else:
            try:
                session = self.load_session_data(request)
            except:
                print(f"session parsing error - {urlsplit.query}")
                session = self.session

        def set_session(response):
            return self.add_header(
                response,
                "hx-push",
                self.build_session_url(request, session),
            )

        return session, set_session

    def add_header(self, response, header, value):
        response.headers[header] = json.dumps(value) if type(value) == dict else value
        return response

    def hx_trigger(self, view, triggers):
        if asyncio.iscoroutinefunction(view):

            @wraps(view)
            async def _(request, *args, **kwargs):
                response = await view(request, *args, **kwargs)
                if triggers["ALL"]:
                    response.headers[HXTRIGGER] = triggers["ALL"]
                else:
                    for method, event in [t for t in triggers.items() if t[0] != "ALL"]:
                        if request.method == method and event:
                            response.headers[HXTRIGGER] = event
                return response

            return _
        else:

            @wraps(view)
            def _(request, *args, **kwargs):
                response = view(request, *args, **kwargs)
                if triggers["ALL"]:
                    response.headers[HXTRIGGER] = triggers["ALL"]
                else:
                    for method, event in [t for t in triggers.items() if t[0] != "ALL"]:
                        if request.method == method and event:
                            response.headers[HXTRIGGER] = event
                return response

            return _

    def _register_route(self, re, view, route, urlname):
        name = urlname or view.__name__
        path_func = re_path if re else path
        self.urlpatterns.append(path_func(route or (name + "/"), view, name=name))

    def route(
        self,
        route="",
        require_login=True,
        methods=False,
        hx_trigger=False,
        post_hx_trigger=False,
        put_hx_trigger=False,
        get_hx_trigger=False,
        delete_hx_trigger=False,
        re=False,
        permissions=None,
        url_name=None,
        **kwargs,
    ):
        triggers = {
            "ALL": hx_trigger,
            "POST": post_hx_trigger,
            "PUT": put_hx_trigger,
            "GET": get_hx_trigger,
            "DELETE": delete_hx_trigger,
        }
        if not isinstance(permissions, (list, tuple)):
            permissions = {x for x in [permissions] + self.permissions if x}

        # return a decorator function which will return either an async or sync function
        def _(view):
            urlname = url_name
            # convert class based views to functional views
            if isinstance(view, type):
                view = view.as_view()
                if not urlname:
                    raise Exception(
                        "@api must specify a url_name kwarg when using class based views"
                    )

            else:
                if not urlname:
                    urlname = view.__name__

            if require_login and asyncio.iscoroutinefunction(view):

                @wraps(view)
                async def set_from_headers(request, *args, **kwargs):
                    request.htmx = "Hx-Request" in request.headers
                    request.json = (
                        "json" in request.headers.get("Content-Type", "")
                        or request.headers.get("json-response", "") == "true"
                    )
                    return await view(request, *args, **kwargs)

                wrapped_view = async_login_required(set_from_headers)
                if permissions:
                    wrapped_view = async_permission_required(wrapped_view, permissions)

            elif require_login:

                @wraps(view)
                def set_from_headers(request, *args, **kwargs):
                    request.htmx = "Hx-Request" in request.headers
                    request.json = (
                        "json" in request.headers.get("content-type", "")
                        or request.headers.get("json-response", "") == "true"
                    )
                    resp = view(request, *args, **kwargs)
                    return resp

                wrapped_view = login_required(set_from_headers)
                if permissions:
                    wrapped_view = permission_required(permissions)(wrapped_view)

            else:
                wrapped_view = view

            if methods:
                wrapped_view = self.enforce_methods(
                    wrapped_view, methods, asyncio.iscoroutinefunction(view)
                )

            if any(triggers.values()):
                wrapped_view = self.hx_trigger(wrapped_view, triggers)

            if isinstance(route, (list, tuple)):
                for _route in route:
                    self._register_route(re, wrapped_view, _route, urlname)
            else:
                self._register_route(re, wrapped_view, route, urlname)

            return view

        return _

    def enforce_methods(self, view, methods, is_async=False):
        checker = (
            API.methods_checker
            if type(methods) in (list, tuple)
            else API.method_checker
        )
        if is_async:

            @wraps(view)
            async def _(request, *args, **kwargs):
                if checker(methods, request):
                    return await view(request, *args, **kwargs)
                return HttpResponseBadRequest()

        else:

            @wraps(view)
            def _(request, *args, **kwargs):
                if checker(methods, request):
                    return view(request, *args, **kwargs)
                return HttpResponseBadRequest()

        return _

    def __getattr__(self, name):
        methods = name.upper().split("_")
        if len(methods) > 1:
            assert all(m in METHODS for m in methods)
        else:
            method = methods[0]
            assert method in METHODS

        @wraps(self.route)
        def _(*args, **kwargs):
            return self.route(*args, **kwargs, methods=methods)

        return _


def group_by(iterable, key):
    groups = defaultdict(list)
    for item in iterable:
        groups[key(item)].append(item)
    return groups


def flatten(iterable):
    return [item for sublist in iterable for item in sublist]


def is_valid_employee_email(email: str):
    """
    assumes email is already validated by django
    """
    return email.endswith("@canada.ca") or email.endswith(".gc.ca")
