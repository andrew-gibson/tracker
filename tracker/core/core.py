import json
import re
import operator
import functools

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Field, Model, Q, PROTECT, ForeignKey, Manager
from django.forms import ModelForm, modelform_factory
from django.http import JsonResponse, Http404, QueryDict, HttpResponse
from django_lifecycle import LifecycleModelMixin
from django.urls import reverse
from django_readers import specs
from django.shortcuts import get_object_or_404
from .utils import classproperty, render, flatten, get_related_model_or_404
from .lang import resolve_field_to_current_lang
from tracker.jinja2 import add_encode_parameter, decode_get_params


class RequestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data:
            self.data._mutable = True
            for field in self._meta.model.bilingual_fields:
                if field in self.data:
                    self.data[resolve_field_to_current_lang(field)] = self.data[field]
                    del self.data[field]
            self.data._mutable = False
        # for attr, field in self.fields.items():
        #    setattr(field, "request", self.request)
        #    setattr(field.widget, "request", self.request)
        #    if hasattr(field.widget, "a_c"):
        #        setattr(field.a_c, "request", self.request)
        #        setattr(field.widget.a_c, "request", self.request)


class CoreManager(Manager):

    def user_get(self, request, *args, **kwargs):
        try:
            return self.user_filter(request).get(*args, **kwargs)
        except self.model.DoesNotExist:
            raise Http404("cannot find requested object")

    def user_filter(self, request):
        if hasattr(self.model, "user_filter"):
            return self.model.user_filter(request)
        return self.filter(group__in=request.user.groups.all())

    def user_delete(self, request, *args, **kwargs):
        try:
            obj = self.user_filter(request).get(*args, **kwargs)
            if getattr(obj, "can_delete", lambda r: True)(request):
                obj.delete()
            else:
                raise Http404("cannot find requested object")
        except self.model.DoesNotExist:
            raise Http404("cannot find requested object")


class CoreModel(LifecycleModelMixin, Model):
    class Meta:
        abstract = True

    objects = CoreManager()

    @classproperty
    def model_info(cls):
        return {
            "fields": cls.fields_map,
            "search_relation": reverse("core:text_ac", kwargs={"m": cls._meta.label}),
            "main": reverse("core:main", kwargs={"m": cls._meta.label}),
            "main_pk": reverse(
                "core:main", kwargs={"m": cls._meta.label, "pk": 9999}
            ).replace("9999", "__pk__"),
            "rgba": getattr(cls, "trigger_color", "rgba(21,21,21,0.3))"),
            "hex": getattr(cls, "hex_trigger_color", "#1a1a1a"),
            "bilingual_fields": cls.bilingual_fields,
        }

    @classmethod
    def settings(cls, request):
        try:
            settings = apps.get_model(f"{cls._meta.app_label}.settings")
            obj = settings.objects.get_or_create(user=request.user)[0]
            prepare_qs, projection = settings.readers(request)
            return projection(obj)
        except LookupError:
            return {}

    @classproperty
    def bilingual_fields(cls):
        return [
            x.replace("_en", "") for x in cls._fields_map.keys() if x.endswith("_en")
        ]

    @classmethod
    def localize_field(cls,attr):
        if attr not in cls._fields_map:
            localized = resolve_field_to_current_lang(attr)
            if localized not in cls._fields_map: 
                cls._meta.get_field(localized) # this will raise fieldDoesNotExist
            return localized
        return attr

    @classproperty
    def _fields_map(cls):
        return {x.name: x.__class__.__name__ for x in cls._meta.get_fields()}

    @classproperty
    def fields_map(cls):
        all_fields = cls._fields_map
        for bif in cls.bilingual_fields:
            all_fields[bif] = all_fields[resolve_field_to_current_lang(bif)]
        return all_fields

    @classmethod
    def readers(cls, request,pk=None):
        if callable(cls.spec):
            spec = cls.spec(cls, request, pk)
        else:
            spec = cls.spec
        return specs.process(spec)

    @classmethod
    def get_projection_by_pk(cls, request, pk):
        ''' 
          can't user model.objects.get because need to apply all the 
          preparing functions to then apply the producers and then the projections 
        '''
        prepare_qs, projection = cls.readers(request,pk)
        qs =  prepare_qs(cls.objects.user_filter(request).filter(pk=pk))
        try:
            obj = qs.first()
            if not obj:
                raise  cls.DoesNotExist()
            return obj, projection(obj)
        except cls.DoesNotExist:
            raise Http404("No object matches the given query")

    @classproperty
    def _name(cls):
        return cls.__name__.lower()

    _Form = RequestForm

    @classmethod
    def form(cls, request):
        Form = modelform_factory(
            cls,
            form=cls._Form,
            fields=getattr(cls, "form_fields", cls._Form._meta.fields),
            field_classes=getattr(cls, "field_classes", {}),
            widgets=getattr(cls, "form_widgets", {}),
        )
        Form.request = request
        return Form

    @classmethod
    def POST(cls, request):
        form = cls.form(request)(request.POST)
        context = {"form": form}
        preoare_qs, projection = cls.readers(request,pk)
        if form.is_valid():
            inst = form.instance
            # by default associasave()te objects with their creator
            inst.add_user_and_save(request)
            _, context["inst"] = cls.get_projection_by_pk(request, inst.pk)
            if request.json:
                return JsonResponse(context["inst"])
        else:
            context["inst"] = form.instance
            if request.json:
                return JsonResponse({"errors": form.errors})

        return render(
            request,
            f"{cls._name}/{cls._name}.html",
            context,
        )

    @classmethod
    def PUT(cls, request, pk):
        prepare_qs, projection = cls.readers(request,pk)
        inst, inst_dict = cls.get_projection_by_pk(request, pk)
        put = QueryDict(request.body)
        form = cls.form(request)(put, instance=inst)
        context = {"form": form}
        if form.is_valid():
            form.save()
            try:
                obj, context["inst"] = cls.get_projection_by_pk(request, pk)
                if request.json:
                    return JsonResponse(context["inst"])
            except:
                return HttpResponse("access lost")
        else:
            context["inst"] = form.instance
            if request.json:
                return JsonResponse({"errors": form.errors})

        return render(
            request,
            f"{cls._name}/{cls._name}.html",
            context,
        )

    @classmethod
    def GET(cls, request, pk=None):
        prepare_qs, projection = cls.readers(request,pk)
        if pk:
            inst, inst_dict = cls.get_projection_by_pk(request, pk)
            if request.json:
                return JsonResponse(inst_dict)
            form = cls.form(request)(instance=inst)
            return render(
                request,
                f"{cls._name}/{cls._name}.html",
                {
                    "inst": inst_dict,
                    "form": form,
                    "standalone": not request.htmx,
                    "settings": cls.settings(request),
                },
            )
        else:
            insts = [
                projection(p)
                for p in prepare_qs(cls.objects.user_filter(request)).order_by(
                    *cls._meta.ordering
                )
            ]
            if request.json:
                return JsonResponse(insts, safe=False)
            return render(
                request,
                f"{cls._name}/{cls._name}s.html",
                {
                    "insts": insts,
                    "standalone": not request.htmx,
                    "settings": cls.settings(request),
                },
            )

    @classmethod
    def DELETE(cls, request, pk):
        cls.objects.user_delete(request, pk=pk)
        return HttpResponse("Deleted")

    @classmethod
    def filter(cls, qs, request):
        return qs

    @classmethod
    def get_filters(cls, request):
            filters = decode_get_params(request.GET).get("f", {}).get("filters", {})
            # remove any possible filter terms which might try to alter the
            # users filter condition
            q_param = {k: v for k, v in filters.items() if "group" not in k}
            if "full-text-search" in q_param:
                val =  q_param["full-text-search"]
                del q_param["full-text-search"]
                fts = [ Q(**{f"{k}__icontains": val})
                        for k, v in cls._fields_map.items()
                        if v in ["CharField", "TextField"]
                    ]
                q = functools.reduce(operator.or_, fts)
            else:
                q = Q()
            q = q & Q(**q_param)
            return q

    def add_user_and_save(self, request):
        if "group" in self.model_info["fields"]:
            self.group = request.user.main_group
        self.save()


class AutoCompleteNexus:

    @classmethod
    def find_words_from_trigger(cls, text, trigger, many=True):
        split_text = text.split(" ")
        regex = re.compile(f"\\{trigger}\\w+")
        length = len(split_text)
        words = [
            x.replace(trigger, "") + " "
            for i, x in enumerate(split_text[0:-1])
            if re.match(regex, x)
        ]
        if len(split_text) and split_text[-1].startswith(trigger):
            words.append(split_text[-1].replace(trigger, ""))
        if not many and len(words):
            return [words[-1]]
        return words

    @classmethod
    def cls_text_scan(cls, text_input, results, triggers):
        return results

    @classmethod
    def get_autocompletes(cls, excludes=None):
        excludes = [] if not excludes else excludes
        return [
            f
            for f in cls._meta.get_fields()
            if f.related_model
            and isinstance(f, (Field,))
            and hasattr(f.related_model, "text_search_trigger")
            and f.name not in excludes
        ]

    @classmethod
    def describe_links(cls, excludes=None):
        autocompletes = ", ".join(
            [
                f"'{x.related_model.text_search_trigger}' for {x.related_model._meta.verbose_name}"
                for x in cls.get_autocompletes(excludes=excludes)
            ]
        )
        return f"Add {cls._meta.verbose_name.title()} (Type: {autocompletes})"

    @classmethod
    def parse_text(cls, request):
        f = decode_get_params(request.GET).get("f", {})
        ac_filters = f.get("ac_filters", {})
        exclude = f.get("exclude", [])

        if request.method == "POST":
            remainder = text_input = request.POST.get("q")
        else:
            remainder = text_input = request.GET.get("q", "")

        fields = cls.get_autocompletes(exclude)
        results = {
            f.name: {
                "trigger": f.related_model.text_search_trigger,
                "model": f.related_model,
                "model_info": f.related_model.model_info,
                "verbose": getattr(
                    f.related_model._meta,
                    "verbose_name_plural" if f.many_to_many else "verbose_name",
                ).title(),
                "name": f.name,
                "many_to_many": f.many_to_many,
                "search_terms": cls.find_words_from_trigger(
                    text_input, f.related_model.text_search_trigger, many=f.many_to_many
                ),
            }
            for f in fields
        }

        for name in results:
            filter_qs = Q(**ac_filters.get(name, {}))
            results[name]["results"] = [
                [term, results[name]["model"].ac(request, term, filter_qs=filter_qs)]
                for term in results[name]["search_terms"]
            ]
            trigger = results[name]["trigger"]
            for parsed in results[name]["search_terms"]:
                remainder = remainder.replace(trigger + parsed, "")

        cls.cls_text_scan(
            remainder, results, [x.related_model.text_search_trigger for x in fields]
        )  # default is nothing happens, but classes can add extra scanning, for example: dates

        # secondd pass through
        for name in results:
            trigger = results[name]["trigger"]
            for parsed in results[name]["search_terms"]:
                remainder = remainder.replace(trigger + parsed, "")

        return {
            "results": results,
            "remainder": remainder,
            "anything_removed": remainder != text_input,
        }

    @classmethod
    def save_from_parse(cls, request, results, attr, attr_val):
        f = decode_get_params(request.GET).get("f", {})
        obj = cls(**{attr: attr_val})

        if "attach_to" in f:
            instructions = f.get("attach_to")
            atachee_model = get_related_model_or_404(cls, instructions["attr"])[0]
            atachee = get_object_or_404(
                atachee_model.objects.user_filter(request), pk=instructions["pk"]
            )
            setattr(obj, instructions["attr"], atachee)

        obj.add_user_and_save(request)

        for rel_name in results:
            x = results[rel_name]

            """
             x has format of:
             {'trigger': '@',
             'model': <some lookup model>,
             'name': 'attrbute name',
             "attr_only" : boolean,
             'many_to_many': boolean,
             'search_terms': ['matthew'],     <-- when many to many there will be multiple search terms
             'results': [
                 ['search_term', [{ 'id': 2, 'name': 'screen name', 'new' : True}]]
                ]
             }

            """

            if x["results"]:
                if x.get("attr_only", False):
                    setattr(obj, rel_name, x["results"][0][1][0]["val"])

                else:
                    flattened_results = list(
                        flatten(y[1] for y in x["results"] if y[0])
                    )
                    new_ones = [y for y in flattened_results if "new" in y]
                    existing_ids = [
                        y["id"] for y in flattened_results if "new" not in y
                    ]
                    new_objs = [
                        x["model"].objects.create(
                            **{
                                k: v
                                for k, v in new_one.items()
                                if k not in ["name", "id", "new"]
                            }
                        )
                        for new_one in new_ones
                    ]
                    [x.add_user_and_save(request) for x in new_objs]

                    existing_objs = (
                        x["model"]
                        .objects.user_filter(request)
                        .filter(id__in=existing_ids)
                    )

                    if x["many_to_many"]:
                        getattr(obj, rel_name).add(*new_objs)
                        getattr(obj, rel_name).add(*existing_objs)
                    else:
                        if new_ones:
                            setattr(obj, rel_name, new_ones[0])
                        if existing_objs:
                            setattr(obj, rel_name, existing_objs[0])
        obj.save()
        return obj


triggers = set()


class AutoCompleteCoreModel(CoreModel):
    class Meta:
        abstract = True

    def __init_subclass__(
        cls, trigger=None, hex_color="", search_field="name", **kwargs
    ):
        super().__init_subclass__(**kwargs)
        if hex_color:
            rgba = f"rgba{tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}"

            cls.trigger_color = rgba
            cls.hex_trigger_color = "#" + hex_color
            cls._search_field = search_field
            if trigger:
                cls.text_search_trigger = trigger
                if cls.text_search_trigger in triggers:
                    raise Exception(
                        f"{cls} is trying to register {cls.text_search_trigger} as a trigger, it has already been assigned"
                    )
                triggers.add(cls.text_search_trigger)

    def get_autocomplete_triggers(cls):
        """return the instrcutions for self.search_field"""

    @classproperty
    def search_field(cls):
        f = cls._search_field
        if f in cls.bilingual_fields:
            f = resolve_field_to_current_lang(f)
        return f

    @classmethod
    def ac_query(cls, request, query):
        f = cls.search_field
        if query == "":
            q = Q()
        elif query.endswith(" "):
            q = Q(**{f"{f}__iexact": query.strip()})
        else:
            q = Q(**{f"{f}__icontains": query})

        return cls.objects.user_filter(request).filter(q).distinct()

    @classmethod
    def ac(
        cls,
        request,
        query="",
        variant=None,
        filter_qs=None,
        cutoff=None,
        optional_projection=False,
    ):
        f = cls.search_field

        preoare_qs, projection = cls.readers(request)
        qs = preoare_qs(cls.ac_query(request, query))

        if filter_qs:
            qs = qs.filter(filter_qs)

        if query == "" and cutoff:
            qs = qs[:10]

        if optional_projection:
            results = [optional_projection(projection(x)) for x in qs]
        else:
            results = [projection(x) for x in qs]

        if (
            (len(results) == 0 and query.endswith(" ") or not query.endswith(" "))
            and query.strip() != ""
            and not any(query.lower() == x["name"].lower() for x in results)
        ):
            # not ending in space -- always create fake new one unless it
            # duplicates i.e. cursor was right at the end of the word
            new_el = {
                "name": query,
                "id": -1,
                "new": True,
                f: query,
                "__type__": cls._meta.label,
            }

            if optional_projection:
                new_el = optional_projection(new_el)

            results = [new_el] + results

        return results
