from django.contrib.auth.models import (
    AbstractUser,
    UserManager,
    GroupManager,
    Permission,
)
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    BigAutoField,
    ManyToManyField,
    OneToOneField,
    CharField,
    DateTimeField,
    ForeignKey,
    Model,
    Prefetch,
    TextField,
    BooleanField,
)
from django.contrib import admin
from text.translate import gettext_lazy as _
from .core import CoreModel, AutoCompleteCoreModel
from core.utils import add_to_admin
from django.conf import settings

group_model = settings.AUTH_GROUP_MODEL
group_model_name = group_model.split(".")[-1]
permissions_related_name = "custom_group_set" if group_model_name == "Group" else None


# This class has been copied from django.contrib.auth.models.Group
# The only additional thing set is abstract=True in meta
# This class should not be updated unless replacing it with a new version from django.contrib.auth.models.Group
class AbstractGroup(Model):
    name_en = CharField(max_length=150, unique=True)
    name_fr = CharField(max_length=150, unique=True, null=True, blank=True)
    acronym_en = CharField(max_length=10, unique=True, null=True, blank=True)
    acronym_fr = CharField(max_length=10, unique=True, null=True, blank=True)
    system = BooleanField(db_default=False)
    app = CharField(max_length=100, null=True, blank=True)
    permissions = ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
        related_name=permissions_related_name,
    )

    objects = GroupManager()

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")
        abstract = True

    def __str__(self):
        return self.name_en

    def natural_key(self):
        return (self.name,)


@add_to_admin
class Group(AbstractGroup, AutoCompleteCoreModel, trigger="*", hex_color="fb5607"):

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name_en", "system", "app")
        list_editable = ("name_en", "system", "app")
        list_filter = ("system", "app")
        search_fields = ("name",)

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()

    def can_i_delete(self, request):
        return False

    group = None
    parent = ForeignKey(
        "Group", on_delete=CASCADE, related_name="children", null=True, blank=True
    )


class GroupPrefetcherManager(UserManager):
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().prefetch_related("groups")


@add_to_admin
class User(AbstractUser):
    login_redirect = CharField(max_length=100, default="project:main")
    objects = GroupPrefetcherManager()

    class adminClass(admin.ModelAdmin):
        list_display = ("username", "belongs_to", "manages")
        list_editable = ("belongs_to", "manages", )

    @classmethod
    def user_filter(cls, request):
        return cls.objects

    def can_i_delete(self, request):
        return False

    class Meta:
        base_manager_name = "objects"

    belongs_to = ForeignKey(Group, on_delete=PROTECT, related_name="+")
    manages = OneToOneField(
        Group, on_delete=PROTECT, related_name="+", null=True, blank=True
    )
    groups = ManyToManyField(
        Group,
        blank=True,
        related_name="users",
    )


class ActiveChannels(Model):
    def __str__(self):
        return self.channel_name

    channel_name = CharField(max_length=300, null=True, blank=True)
    user = ForeignKey(User, related_name="active_channels", on_delete=CASCADE)
