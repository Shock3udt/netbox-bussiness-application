from django.db import models
from netbox.models import NetBoxModel
from virtualization.models import VirtualMachine, Cluster
from dcim.models import Device
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from utilities.choices import ChoiceSet
from django.conf import settings
from django.utils import timezone


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


class ServiceHealthStatus(ChoiceSet):
    DOWN = 'down'
    DEGRADED = 'degraded'
    UNDER_MAINTENANCE = 'under_maintenance'
    HEALTHY = 'healthy'
    CHOICES = [
        (DOWN, 'Down', 'red'),
        (DEGRADED, 'Degraded', 'orange'),
        (UNDER_MAINTENANCE, 'Under Maintenance', 'blue'),
        (HEALTHY, 'Healthy', 'green'),
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

    @property
    def health_status(self):
        """
        Calculate the health status of this service based on incidents, maintenance, and dependencies.
        Returns one of: 'down', 'degraded', 'under_maintenance', 'healthy'
        """
        return self._calculate_health_status()

    def _calculate_health_status(self, visited=None):
        """
        Internal method to calculate health status with circular dependency protection.
        """
        if visited is None:
            visited = set()

        # Prevent infinite loops in circular dependencies
        if self.id in visited:
            return ServiceHealthStatus.HEALTHY

        visited.add(self.id)

        # Check for active incidents that make this service down
        active_incident_statuses = ['new', 'investigating', 'identified']
        if self.incidents.filter(
            status__in=active_incident_statuses,
            resolved_at__isnull=True
        ).exists():
            return ServiceHealthStatus.DOWN

        # Check for ongoing maintenance
        now = timezone.now()
        if self._has_ongoing_maintenance(now):
            return ServiceHealthStatus.UNDER_MAINTENANCE

        # Check dependencies for health impact
        dependency_health = self._check_dependency_health(visited.copy())

        # Return the most severe status found
        if dependency_health == ServiceHealthStatus.DOWN:
            return ServiceHealthStatus.DOWN
        elif dependency_health == ServiceHealthStatus.DEGRADED:
            return ServiceHealthStatus.DEGRADED
        elif dependency_health == ServiceHealthStatus.UNDER_MAINTENANCE:
            return ServiceHealthStatus.DEGRADED  # Service under maintenance degrades dependents
        else:
            return ServiceHealthStatus.HEALTHY

    def _has_ongoing_maintenance(self, now):
        """Check if this service has ongoing maintenance"""
        from django.contrib.contenttypes.models import ContentType
        service_ct = ContentType.objects.get_for_model(TechnicalService)

        # Check direct maintenance on this service
        if Maintenance.objects.filter(
            content_type=service_ct,
            object_id=self.id,
            status='started',
            planned_start__lte=now,
            planned_end__gte=now
        ).exists():
            return True

        # Check maintenance on related devices and VMs
        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)

        # Check devices
        if self.devices.exists():
            device_ids = list(self.devices.values_list('id', flat=True))
            if Maintenance.objects.filter(
                content_type=device_ct,
                object_id__in=device_ids,
                status='started',
                planned_start__lte=now,
                planned_end__gte=now
            ).exists():
                return True

        # Check VMs
        if self.vms.exists():
            vm_ids = list(self.vms.values_list('id', flat=True))
            if Maintenance.objects.filter(
                content_type=vm_ct,
                object_id__in=vm_ids,
                status='started',
                planned_start__lte=now,
                planned_end__gte=now
            ).exists():
                return True

        return False

    def _check_dependency_health(self, visited):
        """Check the health of all dependencies and return the most severe impact"""
        most_severe = ServiceHealthStatus.HEALTHY

        # Group dependencies by type for redundancy analysis
        normal_deps = []
        redundant_deps = {}

        for dep in self.get_upstream_dependencies():
            if dep.dependency_type == DependencyType.NORMAL:
                normal_deps.append(dep)
            else:  # redundancy
                group_key = dep.name or 'default'
                if group_key not in redundant_deps:
                    redundant_deps[group_key] = []
                redundant_deps[group_key].append(dep)

        # Check normal dependencies - any down service makes this service down
        for dep in normal_deps:
            upstream_health = dep.upstream_service._calculate_health_status(visited.copy())
            if upstream_health == ServiceHealthStatus.DOWN:
                return ServiceHealthStatus.DOWN
            elif upstream_health == ServiceHealthStatus.DEGRADED:
                most_severe = ServiceHealthStatus.DEGRADED
            elif upstream_health == ServiceHealthStatus.UNDER_MAINTENANCE:
                most_severe = ServiceHealthStatus.DEGRADED

        # Check redundant dependencies - all services in a group must be down to cause failure
        for group_name, deps in redundant_deps.items():
            group_statuses = []
            for dep in deps:
                upstream_health = dep.upstream_service._calculate_health_status(visited.copy())
                group_statuses.append(upstream_health)

            # Count healthy services in the group
            healthy_count = sum(1 for status in group_statuses if status == ServiceHealthStatus.HEALTHY)
            down_count = sum(1 for status in group_statuses if status == ServiceHealthStatus.DOWN)
            degraded_count = sum(1 for status in group_statuses if status == ServiceHealthStatus.DEGRADED)
            maintenance_count = sum(1 for status in group_statuses if status == ServiceHealthStatus.UNDER_MAINTENANCE)

            # If all services in redundancy group are down, this service is down
            if down_count == len(deps):
                return ServiceHealthStatus.DOWN

            # If some services are down but others are healthy, this service is degraded
            if down_count > 0 and healthy_count > 0:
                most_severe = ServiceHealthStatus.DEGRADED

            # If any service in the group is degraded or under maintenance, this service is degraded
            if degraded_count > 0 or maintenance_count > 0:
                most_severe = ServiceHealthStatus.DEGRADED

        return most_severe

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
