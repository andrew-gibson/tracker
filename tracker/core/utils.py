import asyncio
import base64
import binascii
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field, make_dataclass
from functools import wraps
from urllib import parse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import resolve_url
from django.template import engines
from django.urls import path, re_path
from django.utils.safestring import mark_safe

import bleach
import mistune
import pytz
from asgiref.sync import sync_to_async
from dateutil.relativedelta import *
from text.translate import gettext_lazy as _

ALLOWED_TAGS = ["li", "ol", "ul", "p", "br", "span"]


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
        b64_jsonb = base64.urlsafe_b64encode(jsonb)
        return b64_jsonb.decode()

    def build_session_url(self, url, session_dict):
        s_b64_jsonb = self.encode_session(session_dict)
        return "?".join([url, s_b64_jsonb])

    def current_url(self, request):
        return parse.urlsplit(
            request.headers.get("HX-Current-URL", request.build_absolute_uri())
        )

    def load_session_data(self, query):
        try:
            return json.loads(
                base64.urlsafe_b64decode(query.encode("utf-8")).decode()
            )
        except binascii.Error:
            return self.session

    def parse_referer(self, request):
        return parse.urlsplit(request.headers.get("Referer", ""))

    def get_url_session(self, request):
        # works in conjunction with htmx
        # use base64 and json to store session info in the url
        urlsplit = self.current_url(request)
        if not urlsplit.query:
            # make copy of session dict so it can be modified
            session = json.loads(json.dumps(self.session))
        else:
            try:
                session = self.load_session_data(urlsplit.query)
            except:
                print(f"session parsing error - {urlsplit.query}")
                session = self.session

        def set_session(response):
            return self.add_header(
                response,
                "hx-push",
                self.build_session_url(urlsplit.path, session),
            )

        return session, set_session

    def add_header(self, response, header, value):
        response.headers[header] = (
            json.dumps(value) if type(value) == dict else value
        )
        return response

    def hx_trigger(self, view, triggers):
        if asyncio.iscoroutinefunction(view):

            @wraps(view)
            async def _(request, *args, **kwargs):
                response = await view(request, *args, **kwargs)
                if triggers["ALL"]:
                    response.headers[HXTRIGGER] = triggers["ALL"]
                else:
                    for method, event in [
                        t for t in triggers.items() if t[0] != "ALL"
                    ]:
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
                    for method, event in [
                        t for t in triggers.items() if t[0] != "ALL"
                    ]:
                        if request.method == method and event:
                            response.headers[HXTRIGGER] = event
                return response

            return _

    def _register_route(self, re, view, route, urlname):
        name = urlname or view.__name__
        path_func = re_path if re else path
        self.urlpatterns.append(
            path_func(route or (name + "/"), view, name=name)
        )

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
                async def set_htmx(request, *args, **kwargs):
                    request.htmx = "Hx-Request" in request.headers
                    return await view(request, *args, **kwargs)

                wrapped_view = async_login_required(set_htmx)
                if permissions:
                    wrapped_view = async_permission_required(
                        wrapped_view, permissions
                    )

            elif require_login:

                @wraps(view)
                def set_htmx(request, *args, **kwargs):
                    request.htmx = "Hx-Request" in request.headers
                    return view(request, *args, **kwargs)

                wrapped_view = login_required(set_htmx)
                if permissions:
                    wrapped_view = permission_required(permissions)(
                        wrapped_view
                    )

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



def add_global_context(request):
    return {
        "app_version": app_version,
    }


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


