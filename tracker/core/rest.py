import re

from django.apps import apps
from django.db.models import Field, ManyToManyField, Model, Q
from django.forms import ModelForm, modelform_factory
from django.http import JsonResponse
from django_lifecycle import LifecycleModelMixin
from django_readers import specs

from .utils import classproperty, render


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

    @classproperty
    def _name(cls):
        return f"{cls.__name__.lower()}"

    _Form = RequestForm

    @classproperty
    def rest_models(cls):
        return {
            k._meta.label: k
            for k in apps.get_models()
            if issubclass(k, RESTModel)
        }

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
            if getattr(inst, "users", False):
                inst.users.add(request.user)
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
        inst = cls.belongs_to_user(request).get(pk=pk)
        put = QueryDict(request.PUT)
        form = cls.form(request)(put, instance=inst)
        context = {"form": form, "models": cls.rest_models}
        if form.is_valid():
            inst = form.save()
            context["inst"] = projection(inst)
            if request.json:
                return JsonResponse(context["inst"])
        return render(
            request,
            f"{cls._name}/{cls._name}.html",
            context,
        )

    @classmethod
    def GET(cls, request, pk=None):
        prepare_qs, projection = cls.readers
        if pk:
            inst = cls.belongs_to_user(request).get(pk=pk)
            if request.json:
                return JsonResponse(projection(inst))
            form = cls.form(request)(instance=inst)
            return render(
                request,
                f"{cls._name}/{cls._name}.html",
                {"inst": projection(inst), "form": form, "models": cls.rest_models},
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
                },
            )

    @classmethod
    def DELETE(cls, request, pk):
        qs = cls.belongs_to_user(request).filter(pk=pk)
        if qs.count() == 1:
            qs.delete()
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
        qs = cls.objects.filter(users=request.user)
        return cls.filter(qs, request)

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
    def get_autocompletes(cls):
        return [
            f
            for f in cls._meta.get_fields()
            if f.related_model
            and isinstance(f, (Field,))
            and hasattr(f.related_model, "text_search_trigger")
        ]

    @classmethod
    def describe_links(cls):
        autocompletes = ", ".join(
            [
                f"'{x.related_model.text_search_trigger}' for {x.related_model._meta.verbose_name}"
                for x in cls.get_autocompletes()
            ]
        )
        return f"Type: {autocompletes}"


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
        f = f"{cls.search_field}"

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
            and not any(query.lower() == x["repr"].lower() for x in results)
        ):
            # not ending in space -- always create fake new one unless it
            # duplicates i.e. cursor was right at the end of the word
            new_el = {"repr": query, "id": -1, "new": True}

            if optional_projection:
                new_el = optional_projection(new_el)

            results = [new_el] + results

        return results
