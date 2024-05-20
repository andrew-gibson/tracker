import markdown
from django.apps import apps
from django_readers import qs, pairs, projectors, producers, specs
from core import utils



__type__ = {"__type__": (qs.noop, producers.attrgetter("_meta.label"))}

