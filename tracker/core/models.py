from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import (CASCADE, PROTECT, SET_NULL, BigAutoField,
                              CharField, DateTimeField, ForeignKey, Model,
                              Prefetch, TextField)

from text.translate import gettext_lazy as _
from .rest import belongs_to
from core.utils import  add_to_admin 



def field_names(model):
    fields = (
        model._meta.concrete_fields
        + model._meta.related_objects
        + model._meta.many_to_many
    )
    return {f.name: _(f.name) for f in fields}



def from_dict(obj, data):
    for key, val in data.items():
        setattr(obj, key, val)


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
class User(AbstractUser):


    login_redirect = CharField(max_length=100, default="project:main")
    objects = GroupPrefetcherManager()

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects

    class Meta:
        base_manager_name = "objects"


class ActiveChannels(Model):
    def __str__(self):
        return self.channel_name

    channel_name = CharField(max_length=300, null=True, blank=True)
    user = ForeignKey(User, related_name="active_channels", on_delete=CASCADE)

