from django.db import models
from netbox.models import NetBoxModel
from virtualization.models import VirtualMachine, Cluster
from dcim.models import Device
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from utilities.choices import ChoiceSet
from django.conf import settings


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


class ServiceType(ChoiceSet):
    TECHNICAL = 'technical'
    LOGICAL = 'logical'
    CHOICES = [
        (TECHNICAL, 'Technical', 'blue'),
        (LOGICAL, 'Logical', 'purple'),
    ]


class DependencyType(ChoiceSet):
    NORMAL = 'normal'
    REDUNDANCY = 'redundancy'
    CHOICES = [
        (NORMAL, 'Normal', 'orange'),
        (REDUNDANCY, 'Redundancy', 'green'),
    ]


class TechnicalService(NetBoxModel):
    name             = models.CharField(max_length=240, unique=True)
    service_type     = models.CharField(max_length=16, choices=ServiceType, default=ServiceType.TECHNICAL, help_text='Type of service')
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

    def get_absolute_url(self):
        return reverse('plugins:business_application:technicalservice_detail', args=[self.pk])

    def get_upstream_dependencies(self):
        """Get all services this service depends on"""
        return ServiceDependency.objects.filter(downstream_service=self)

    def get_downstream_dependencies(self):
        """Get all services that depend on this service"""
        return ServiceDependency.objects.filter(upstream_service=self)

    def get_downstream_business_applications(self):
        """Get all business applications that are affected by this service (full subtree)"""
        visited = set()
        apps = set()

        def traverse_downstream(service):
            if service.id in visited:
                return
            visited.add(service.id)

            # Add direct business applications
            apps.update(service.business_apps.all())

            # Traverse downstream services
            for dep in service.get_downstream_dependencies():
                traverse_downstream(dep.downstream_service)

        traverse_downstream(self)
        return apps

    def __str__(self):
        return self.name


class ServiceDependency(NetBoxModel):
    """
    Represents a dependency relationship between two technical services.
    """
    name = models.CharField(max_length=240, help_text='Name of the dependency relationship')
    description = models.TextField(blank=True, help_text='Optional description of the dependency')
    upstream_service = models.ForeignKey(
        TechnicalService,
        on_delete=models.CASCADE,
        related_name='downstream_dependencies',
        help_text='Service that is depended upon'
    )
    downstream_service = models.ForeignKey(
        TechnicalService,
        on_delete=models.CASCADE,
        related_name='upstream_dependencies',
        help_text='Service that depends on the upstream service'
    )
    dependency_type = models.CharField(
        max_length=16,
        choices=DependencyType,
        default=DependencyType.NORMAL,
        help_text='Normal: dependent on all upstream services, Redundancy: dependent on any upstream service'
    )

    class Meta:
        ordering = ['name']
        unique_together = ['upstream_service', 'downstream_service']
        verbose_name = 'Service Dependency'
        verbose_name_plural = 'Service Dependencies'

    def get_absolute_url(self):
        return reverse('plugins:business_application:servicedependency_detail', args=[self.pk])

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.upstream_service == self.downstream_service:
            raise ValidationError('A service cannot depend on itself')

    def __str__(self):
        return f"{self.downstream_service} depends on {self.upstream_service} ({self.name})"


class EventStatus(ChoiceSet):
    TRIGGERED = 'triggered'
    OK        = 'ok'
    SUPPRESSED= 'suppressed'
    CHOICES = [
        (TRIGGERED, 'Triggered', 'red'),
        (OK, 'OK', 'green'),
        (SUPPRESSED, 'Suppressed', 'gray'),
    ]

class EventCrit(ChoiceSet):
    CRITICAL = 'critical'
    WARNING  = 'warning'
    INFO     = 'info'
    CHOICES = [
        (CRITICAL, 'Critical', 'red'),
        (WARNING, 'Warning', 'orange'),
        (INFO, 'Info', 'blue'),
    ]

class EventSource(NetBoxModel):        # reference catalog
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

    def get_absolute_url(self):
        return reverse('plugins:business_application:eventsource_detail', args=[self.pk])

    def __str__(self):
        return self.name

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

    def get_absolute_url(self):
        return reverse('plugins:business_application:event_detail', args=[self.pk])

    def __str__(self):
        return f"{self.message[:50]}..."


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

    def get_absolute_url(self):
        return reverse('plugins:business_application:maintenance_detail', args=[self.pk])

    def __str__(self):
        return f"{self.description[:50]}..."

class ChangeType(NetBoxModel):        # reference catalog
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

    def get_absolute_url(self):
        return reverse('plugins:business_application:changetype_detail', args=[self.pk])

    def __str__(self):
        return self.name

class Change(NetBoxModel):
    type          = models.ForeignKey(ChangeType, on_delete=models.PROTECT)
    created_at    = models.DateTimeField(auto_now_add=True)
    description   = models.TextField()
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id     = models.PositiveIntegerField()
    obj           = GenericForeignKey('content_type','object_id')

    def get_absolute_url(self):
        return reverse('plugins:business_application:change_detail', args=[self.pk])

    def __str__(self):
        return f"{self.description[:50]}..."


class IncidentStatus(ChoiceSet):
    NEW         = 'new'
    INVESTIGATING = 'investigating'
    IDENTIFIED  = 'identified'
    MONITORING  = 'monitoring'
    RESOLVED    = 'resolved'
    CLOSED      = 'closed'
    CHOICES = [
        (NEW, 'New', 'red'),
        (INVESTIGATING, 'Investigating', 'orange'),
        (IDENTIFIED, 'Identified', 'yellow'),
        (MONITORING, 'Monitoring', 'blue'),
        (RESOLVED, 'Resolved', 'green'),
        (CLOSED, 'Closed', 'gray'),
    ]

class IncidentSeverity(ChoiceSet):
    CRITICAL = 'critical'
    HIGH     = 'high'
    MEDIUM   = 'medium'
    LOW      = 'low'
    CHOICES = [
        (CRITICAL, 'Critical', 'red'),
        (HIGH, 'High', 'orange'),
        (MEDIUM, 'Medium', 'yellow'),
        (LOW, 'Low', 'green'),
    ]

class Incident(NetBoxModel):
    title           = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    status          = models.CharField(max_length=16, choices=IncidentStatus)
    severity        = models.CharField(max_length=10, choices=IncidentSeverity)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    detected_at     = models.DateTimeField(null=True, blank=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)

    # Responders - people who respond to the incident
    responders      = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='incidents_responding',
        blank=True,
        help_text='Users responding to this incident'
    )

    # Affected services
    affected_services = models.ManyToManyField(
        TechnicalService,
        related_name='incidents',
        blank=True,
        help_text='Technical services affected by this incident'
    )

    # Related events
    events          = models.ManyToManyField(
        Event,
        related_name='incidents',
        blank=True,
        help_text='Events related to this incident'
    )

    # Contact information
    reporter        = models.CharField(max_length=120, blank=True)
    commander       = models.CharField(max_length=120, blank=True, help_text='Incident commander')

    class Meta:
        ordering = ['-created_at']

    def get_absolute_url(self):
        return reverse('plugins:business_application:incident_detail', args=[self.pk])

    def __str__(self):
        return self.title
