from django.db import models

# Create your models here.


class Project(models.Model):
    name = models.CharField(max_length=255)
    parent_project = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    point_of_contact = models.ForeignKey(
        "Contact", on_delete=models.SET_NULL, null=True
    )
    teams = models.ManyToManyField("Team", through="ProjectTeam")
    tags = models.ManyToManyField("Tag")

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=255,unique=True)
    projects = models.ManyToManyField("Project", through="ProjectTeam")

    def __str__(self):
        return self.name


class ProjectTeam(models.Model):
    project = models.ForeignKey("Project", on_delete=models.CASCADE)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    # If needed, you can add additional fields here to capture details about the relationship, for example:
    # start_date = models.DateField(null=True, blank=True)
    # role = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ["project", "team"]


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class EventLog(models.Model):
    project = models.OneToOneField(
        "Project", on_delete=models.CASCADE, related_name="event_log"
    )
    events = models.ManyToManyField("Event", through="EventLogEvent")

    def __str__(self):
        return f"Event Log for {self.project.name}"


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    event_logs = models.ManyToManyField("EventLog", through="EventLogEvent")

    def __str__(self):
        return self.title


class EventLogEvent(models.Model):
    event_log = models.ForeignKey("EventLog", on_delete=models.CASCADE)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["event_log", "event"]
