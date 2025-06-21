from django.db import models
from netbox.models import NetBoxModel
from virtualization.models import VirtualMachine, Cluster
from dcim.models import Device
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from utilities.choices import ChoiceSet


class BusinessApplication(NetBoxModel):
    """
    A model representing a business application in the organization.
    """
    appcode = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=100)
    delegate = models.CharField(max_length=100, blank=True, null=True)
    servicenow = models.URLField(blank=True, null=True)
    virtual_machines = models.ManyToManyField(
        VirtualMachine,
        related_name="business_applications",
        blank=True
    )
    devices = models.ManyToManyField(
        Device,
        related_name="business_applications",
        blank=True
    )

    class Meta:
        ordering = ['appcode']

    def get_absolute_url(self):
        """
        Returns the URL to access a detail view of this object.
        """
        return reverse('plugins:business_application:businessapplication_detail', args=[self.pk])

    def __str__(self):
        return self.appcode


class TechnicalService(NetBoxModel):
    parent           = models.ForeignKey('self', null=True, blank=True,
                                         related_name='children',
                                         on_delete=models.SET_NULL)
    name             = models.CharField(max_length=240, unique=True)
    business_apps    = models.ManyToManyField(BusinessApplication,
                                              related_name='technical_services',
                                              blank=True)
    vms              = models.ManyToManyField(VirtualMachine,
                                              related_name='technical_services',
                                              blank=True)
    devices          = models.ManyToManyField(Device,
                                              related_name='technical_services',
                                              blank=True)
    clusters         = models.ManyToManyField(Cluster,
                                              related_name='technical_services',
                                              blank=True)
    class Meta:
        ordering = ['name']

class EventStatus(ChoiceSet):
    TRIGGERED = 'triggered'
    OK        = 'ok'
    SUPPRESSED= 'suppressed'
    CHOICES = ((TRIGGERED,'Triggered'),
               (OK,'OK'),
               (SUPPRESSED,'Suppressed'))

class EventCrit(ChoiceSet):
    CRITICAL = 'critical'
    WARNING  = 'warning'
    INFO     = 'info'
    CHOICES  = ((CRITICAL,'Critical'),
                (WARNING,'Warning'),
                (INFO,'Info'))

class EventSource(NetBoxModel):        # reference catalog
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

class Event(NetBoxModel):
    created_at    = models.DateTimeField(auto_now_add=True)
    last_seen_at  = models.DateTimeField()
    updated_at    = models.DateTimeField(auto_now=True)
    # polymorphic link to any core or plugin object
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id     = models.PositiveIntegerField()
    obj           = GenericForeignKey('content_type', 'object_id')
    message       = models.CharField(max_length=255)
    dedup_id      = models.CharField(max_length=128, db_index=True)
    status        = models.CharField(max_length=16, choices=EventStatus)
    criticallity  = models.CharField(max_length=10, choices=EventCrit)
    event_source  = models.ForeignKey('EventSource', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    raw           = models.JSONField()


class MaintenanceStatus(ChoiceSet):
    PLANNED  = 'planned'
    STARTED  = 'started'
    FINISHED = 'finished'
    CANCELED = 'canceled'
    CHOICES  = ((PLANNED,'Planned'),(STARTED,'Started'),
                (FINISHED,'Finished'),(CANCELED,'Canceled'))

class Maintenance(NetBoxModel):
    status        = models.CharField(max_length=10, choices=MaintenanceStatus)
    description   = models.TextField()
    planned_start = models.DateTimeField()
    planned_end   = models.DateTimeField()
    contact       = models.CharField(max_length=120)
    # polymorphic link
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id     = models.PositiveIntegerField()
    obj           = GenericForeignKey('content_type','object_id')

class ChangeType(NetBoxModel):        # reference catalog
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

class Change(NetBoxModel):
    type          = models.ForeignKey(ChangeType, on_delete=models.PROTECT)
    created_at    = models.DateTimeField(auto_now_add=True)
    description   = models.TextField()
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id     = models.PositiveIntegerField()
    obj           = GenericForeignKey('content_type','object_id')
