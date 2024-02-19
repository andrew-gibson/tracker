import json
import re

from django.apps import apps
from django.db.models import Field, ManyToManyField, Model, Q
from django.forms import ModelForm, modelform_factory
from django.http import JsonResponse, Http404, QueryDict
from django_lifecycle import LifecycleModelMixin
from django_readers import specs
from django.shortcuts import get_object_or_404
from .utils import classproperty, render, flatten, get_related_model_or_404


class belongs_to:
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects


class RequestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for attr, field in self.fields.items():
            setattr(field, "request", self.request)
            setattr(field.widget, "request", self.request)
            if hasattr(field.widget, "a_c"):
                setattr(field.a_c, "request", self.request)
                setattr(field.widget.a_c, "request", self.request)


class RESTModel(LifecycleModelMixin, Model):
    class Meta:
        abstract = True

    users = ManyToManyField("core.User")


    @classproperty
    def readers(cls):
        return specs.process(cls.rest_spec)

    @classmethod
    def get_projection_by_pk(cls, request, pk):
        prepare_qs, projection = cls.readers
        try:
            return [
                (x, projection(x))
                for x in prepare_qs(cls.belongs_to_user(request).filter(pk=pk))
            ][0]
        except:
            raise Http404("No Model matches the given query")

    @classproperty
    def _name(cls):
        return f"{cls.__name__.lower()}"

    _Form = RequestForm

    @classproperty
    def form_fields_map(cls):
        if hasattr(cls,"form_fields"):
            f = cls.form_fields
        elif hasattr(cls,"_Form"):
            f = cls._Form._meta.fields
        else:
            return {}

        return {x : cls._meta.get_field(x).__class__.__name__  for x in f}

    @classproperty
    def rest_models(cls):
        return {k._meta.label: k for k in apps.get_models() if issubclass(k, RESTModel)}

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
        context = {"form": form, "models": cls.rest_models}
        preoare_qs, projection = cls.readers
        if form.is_valid():
            inst = form.save()
            context["inst"] = projection(inst)
            # by default associate objects with their creator
            inst.add_user(request.user)
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
        prepare_qs, projection = cls.readers
        inst, inst_dict = cls.get_projection_by_pk(request, pk)
        put = QueryDict(request.body)
        form = cls.form(request)(put, instance=inst)
        context = {"form": form, "models": cls.rest_models}
        if form.is_valid():
            form.save()
            obj, context["inst"] = cls.get_projection_by_pk(request, pk)
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
    def GET(cls, request, pk=None):
        prepare_qs, projection = cls.readers
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
                    "models": cls.rest_models,
                    "standalone": not request.htmx,
                },
            )
        else:
            insts = [projection(p) for p in prepare_qs(cls.belongs_to_user(request))]
            if request.json:
                return JsonResponse(insts, safe=False)
            return render(
                request,
                f"{cls._name}/{cls._name}s.html",
                {
                    "insts": insts,
                    "models": cls.rest_models,
                    "standalone": not request.htmx,
                },
            )

    @classmethod
    def DELETE(cls, request, pk):
        inst, inst_dict = cls.get_projection_by_pk(request, pk)
        if qs.count() == 1:
            inst.delete()
        return render(
            request,
            f"{cls._name}/{cls._name}s.html",
            {
                "models": cls.rest_models,
            },
        )

    @classmethod
    def filter(cls, qs, request):
        return qs

    @classmethod
    def belongs_to_user(cls, request):
        try:
            filters = json.loads(request.GET.get("filters", "{}"))
            # remove any possible filter terms which might try to alter the
            # users filter condition
            filters = {k: v for k in filters if "users" not in k}
        except:
            raise Http404("incorrectly formatted GET params")

        qs = cls.objects.filter(users=request.user).filter(Q(**filters))
        return cls.filter(qs, request)

    def add_user(self, user):
        if getattr(self, "users", False):
            inst.users.add(request.user)

    def get_absolute_url(self):
        return reverse(
            "project:project", kwarg={"modelname": self._name(), "pk": self.pk}
        )


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
    def cls_text_scan(cls, text_input, results):
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
        return f"Type: {autocompletes}"

    @classmethod
    def parse_text(cls, request):
        try:
            ac_filters = json.loads(request.GET.get("ac_filters", "[]"))
            exclude = json.loads(request.GET.get("exclude", "[]"))
        except:
            raise Http404("incorrectly formatted GET params")
            return HttpResponseBadRequest("incorrectly formatted GET params")

        remainder = text_input = request.POST.get("payload")
        fields = cls.get_autocompletes(exclude)
        results = {
            f.name: {
                "trigger": f.related_model.text_search_trigger,
                "model": f.related_model,
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

        cls.cls_text_scan(
            text_input, results
        )  # default is nothing happens, but classes can add extra scanning, for example: dates

        for name in results:
            for parsed in results[name]["search_terms"]:
                remainder = remainder.replace(parsed, "")
            remainder = remainder.replace(results[name]["trigger"], "")

        return {
            "results": results,
            "remainder": remainder,
            "anything_removed": remainder != text_input,
        }

    @classmethod
    def save_from_parse(cls, request, results, attr, attr_val):
        obj = cls(**{attr: attr_val})

        if "attach_to" in request.GET:
            instructions = json.loads(request.GET["attach_to"])
            atachee_model = get_related_model_or_404(cls, instructions["attr"])[0]
            atachee = get_object_or_404(
                atachee_model.belongs_to_user(request), pk=instructions["pk"]
            )
            setattr(obj, instructions["attr"], atachee)

        obj.save()
        obj.add_user(request.user)

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
                    setattr(obj, rel_name, x[0][0]["val"])

                else:
                    flattened_results = list(flatten(y[1] for y in x["results"]))
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
                    [x.add_user(request.user) for x in new_objs]

                    existing_objs = (
                        x["model"].belongs_to_user(request).filter(id__in=existing_ids)
                    )

                    if x["many_to_many"]:
                        for results in x["results"]:
                            getattr(obj, rel_name).add(*new_objs)
                            getattr(obj, rel_name).add(*existing_objs)
                    else:
                        if new_ones:
                            setattr(obj, rel_name, new_ones[0])
                        else:
                            setattr(obj, rel_name, existing_objs[0])
        return obj


triggers = set()


class AutoCompleteREST(RESTModel):
    class Meta:
        abstract = True

    def __init_subclass__(
        cls, trigger=None, hex_color="", search_field="name", **kwargs
    ):
        super().__init_subclass__(**kwargs)
        if hex_color:
            rgba = f"rgba{tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}"
            cls.text_search_trigger = trigger
            cls.trigger_color = rgba
            cls.hex_trigger_color = "#" + hex_color
            cls.search_field = search_field
            if cls.text_search_trigger in triggers:
                raise Exception(
                    f"{cls} is trying to register {cls.text_search_trigger} as a trigger, it has already been assigned"
                )
            triggers.add(cls.text_search_trigger)

    def get_autocomplete_triggers(cls):
        """return the instrcutions for self.search_field"""

    @classmethod
    def ac_query(cls, request, query):
        f = cls.search_field

        if query == "":
            q = Q()
        elif query.endswith(" "):
            q = Q(**{f"{f}__iexact": query.strip()})
        else:
            q = Q(**{f"{f}__icontains": query})

        return cls.belongs_to_user(request).filter(q).distinct()

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
        f = f"{cls.search_field}"

        preoare_qs, projection = cls.readers
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
            new_el = {"name": query, "id": -1, "new": True, f: query}

            if optional_projection:
                new_el = optional_projection(new_el)

            results = [new_el] + results

        return results
