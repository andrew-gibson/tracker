from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import (CASCADE, PROTECT, SET_NULL, BigAutoField,
                              CharField, DateTimeField, ForeignKey, Model,
                              Prefetch, TextField)

from text.translate import gettext_lazy as _



def field_names(model):
    fields = (
        model._meta.concrete_fields
        + model._meta.related_objects
        + model._meta.many_to_many
    )
    return {f.name: _(f.name) for f in fields}


def add_to_admin(cls):
    cls.__add_to_admin = True
    return cls


def from_dict(obj, data):
    for key, val in data.items():
        setattr(obj, key, val)


def to_dict(instance, field_list=None, exclude=None):
    opts = instance._meta
    data = {}
    if not field_list:
        fields_iter = [
            f for f in (opts.concrete_fields + opts.related_objects + opts.many_to_many)
        ]
    else:
        fields_iter = [opts.get_field(f) for f in field_list]
    if exclude:
        fields_iter = [f for f in fields_iter if f.name not in exclude]

    for f in fields_iter:
        name = f.get_accessor_name() if hasattr(f, "get_accessor_name") else f.name
        if f.one_to_many or f.one_to_many or f.many_to_many:
            data[name] = [x for x in getattr(instance, name).all()]
        else:
            data[name] = getattr(instance, name)
    return data


class Serializer:
    def serialize(self, field_list=None, exclude=None):
        return to_dict(self, field_list=field_list, exclude=exclude)


def json_set_m2m(inst, attr, data):
    model = getattr(inst, attr).model
    attr_ids = [x.get("id") for x in data]
    attr_objs = model.objects.filter(id__in=attr_ids).all()
    getattr(inst, attr).set(attr_objs)


class GroupPrefetcherManager(UserManager):
    use_for_related_fields = True

    def get_queryset(self):
        return (
            super(GroupPrefetcherManager, self)
            .get_queryset()
            .prefetch_related(Prefetch("groups", to_attr="group_list"))
        )


@add_to_admin
class User(Serializer, AbstractUser):

    login_redirect = CharField(max_length=100, default="project:main")
    objects = GroupPrefetcherManager()

    class Meta:
        base_manager_name = "objects"


class ActiveChannels(Model):
    def __str__(self):
        return self.channel_name

    channel_name = CharField(max_length=300, null=True, blank=True)
    user = ForeignKey(User, related_name="active_channels", on_delete=CASCADE)

