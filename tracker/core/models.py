from functools import cached_property, lru_cache
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
    CharField,
    DateTimeField,
    Model,
    Prefetch,
    TextField,
    BooleanField,
)
from core.fields import (
    ForeignKey,
    ManyToManyField,
    OneToOneField,
)

from django.contrib import admin
from text.translate import gettext_lazy as _
from .core import CoreModel, AutoCompleteCoreModel
from core.utils import add_to_admin
from django.conf import settings
from django_lifecycle import (
    AFTER_SAVE,
    hook,
)


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
class Group(AbstractGroup, AutoCompleteCoreModel):

    class adminClass(admin.ModelAdmin):
        list_display = ("name_en", "system", "app", "parent")
        list_editable = ("system", "app", "parent")
        list_filter = ("system", "app")
        search_fields = ("name",)

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()

    @cached_property
    def descendants(self):
        query = f'''
            WITH RECURSIVE children_cte AS (
                SELECT id, name_en, name_fr, acronym_en, acronym_fr, system, parent_id
                FROM {self._meta.db_table}
                WHERE id = {self.id}
                UNION ALL
                SELECT g.id, g.name_en, g.name_fr, g.acronym_en, g.acronym_fr, g.system, g.parent_id
                FROM {self._meta.db_table} g
                INNER JOIN children_cte c ON c.id = g.parent_id
            )
            SELECT * FROM children_cte;
        '''
        return self.__class__.objects.raw(query)

    @property
    @lru_cache()
    def parents(self):
        query = f'''
            WITH RECURSIVE parents_cte AS (
                SELECT id, name_en, name_fr, acronym_en, acronym_fr, system, parent_id
                FROM {self._meta.db_table}
                WHERE id = {self.id}
                UNION ALL
                SELECT g.id, g.name_en, g.name_fr, g.acronym_en, g.acronym_fr, g.system, g.parent_id
                FROM {self._meta.db_table} g
                INNER JOIN parents_cte p ON p.parent_id = g.id
            )
            SELECT * FROM parents_cte;
        '''
        return self.__class__.objects.raw(query)

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
        list_display = (
            "username",
            "belongs_to",
            "manages",
        )
        list_editable = (
            "belongs_to",
            "manages",
        )

    class Meta:
        base_manager_name = "objects"

    @hook(AFTER_SAVE)
    def force_groups(self):
        self.groups.add(self.belongs_to)
        if self.manages:
            self.groups.add(self.manages)

    belongs_to = ForeignKey(Group, on_delete=PROTECT, related_name="team_members")
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
