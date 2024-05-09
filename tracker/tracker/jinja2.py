import datetime
import json
import random
import string
import base64

from urllib import parse

from crispy_forms.utils import render_crispy_form
from django.apps import apps
from django.http import QueryDict
from django.template.backends.jinja2 import Jinja2
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import SafeString
from django.utils.translation import activate
from jinja2 import Environment, pass_context
from text.translate import gettext_lazy as _
from text.translate import other_lang


def encode_get_param(data):
    jsonb = json.dumps(data).encode("utf-8")
    b64_jsonb = base64.urlsafe_b64encode(jsonb)
    return b64_jsonb.decode()

def decode_get_param(val):
    try:
        return json.loads(base64.urlsafe_b64decode(val.encode("utf-8")).decode())
    except:
        return val

def decode_get_params(querydict):
    return {k: decode_get_param(v) for k, v in querydict.items()}

def add_encode_parameter(key, data, querydict=None):
    querydict = querydict if querydict else QueryDict()
    return parse.urlencode(
        {
            **querydict,
            key: encode_get_param(data),
        }
    )


@pass_context
def url_translate(context):
    request = context["request"]
    r = request.resolver_match
    url_name, args, kwargs = r.url_name, r.args, r.kwargs
    activate(other_lang())
    translated_url = reverse(url_name, args=args, kwargs=kwargs)
    activate(other_lang())
    return translated_url


@pass_context
def crispy(context, form):
    return render_crispy_form(form, context=context)


def random_id():
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(20))


def url_session(view_name, session=None, kwargs=None):
    url = reverse(view_name, kwargs=kwargs)
    return "?".join(url, parse.urlencode(session))


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)


def dumps(obj):
    return SafeString(json.dumps(obj, default=default))

def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "models": {m._meta.label: m for m in apps.get_models() if hasattr(m, "model_info")},
            "static": static,
            "url": reverse,
            "random_id": random_id,
            "crispy": crispy,
            "len": len,
            "url_translate": url_translate,
            "_": _,
            "getattr": getattr,
            "print": print,
            "dumps": dumps,
            "add_encode_parameter": add_encode_parameter,
        }
    )
    return env
