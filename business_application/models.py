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

    pagerduty_routing_key = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='PagerDuty Routing Key',
        help_text='PagerDuty Events API v2 routing key (integration key) for this application.'
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


class PagerDutyTemplateTypeChoices(ChoiceSet):
    """
    Type choices for PagerDuty templates
    """
    SERVICE_DEFINITION = 'service_definition'
    ROUTER_RULE = 'router_rule'

    CHOICES = [
        (SERVICE_DEFINITION, 'Service Definition'),
        (ROUTER_RULE, 'Router Rule'),
    ]


class PagerDutyTemplate(NetBoxModel):
    """
    A reusable PagerDuty service configuration template that can be applied to multiple technical services.
    """
    name = models.CharField(max_length=100, unique=True, help_text='Template name for easy identification')
    description = models.TextField(blank=True, help_text='Description of this PagerDuty template')
    template_type = models.CharField(
        max_length=20,
        choices=PagerDutyTemplateTypeChoices,
        help_text='Type of PagerDuty template (Service Definition or Router Rule)'
    )

    # PagerDuty Configuration
    pagerduty_config = models.JSONField(
        help_text='PagerDuty service configuration in API format'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'PagerDuty Template'
        verbose_name_plural = 'PagerDuty Templates'

    def get_absolute_url(self):
        return reverse('plugins:business_application:pagerdutytemplate_detail', args=[self.pk])

    def validate_pagerduty_config(self):
        """Validate PagerDuty configuration structure"""
        if not self.pagerduty_config:
            return False, ['PagerDuty configuration is required for templates']

        errors = []

        # Only apply strict validation to service definition templates
        # Router rules can have more flexible configuration
        if self.template_type == PagerDutyTemplateTypeChoices.SERVICE_DEFINITION:
            required_fields = ['name', 'description', 'status', 'escalation_policy']

            for field in required_fields:
                if field not in self.pagerduty_config:
                    errors.append(f"Missing required field for service definition: {field}")

            # Validate escalation_policy structure for service definitions
            if 'escalation_policy' in self.pagerduty_config:
                ep = self.pagerduty_config['escalation_policy']
                if not isinstance(ep, dict):
                    errors.append("escalation_policy must be an object")
                else:
                    if 'id' not in ep:
                        errors.append("escalation_policy must have an 'id' field")
                    if 'type' not in ep:
                        errors.append("escalation_policy must have a 'type' field")

            # Validate incident_urgency_rule structure for service definitions
            if 'incident_urgency_rule' in self.pagerduty_config:
                iur = self.pagerduty_config['incident_urgency_rule']
                if not isinstance(iur, dict):
                    errors.append("incident_urgency_rule must be an object")
                else:
                    if 'type' not in iur:
                        errors.append("incident_urgency_rule must have a 'type' field")
                    if iur.get('type') == 'constant' and 'urgency' not in iur:
                        errors.append("incident_urgency_rule with type 'constant' must have 'urgency' field")

        elif self.template_type == PagerDutyTemplateTypeChoices.ROUTER_RULE:
            # Router rules have minimal validation - just check it's valid JSON
            if not isinstance(self.pagerduty_config, dict):
                errors.append("Router rule configuration must be a valid JSON object")

        # Validate alert_grouping_parameters structure if present
        if 'alert_grouping_parameters' in self.pagerduty_config:
            agp = self.pagerduty_config['alert_grouping_parameters']
            if not isinstance(agp, dict):
                errors.append("alert_grouping_parameters must be an object")
            else:
                if 'type' not in agp:
                    errors.append("alert_grouping_parameters must have a 'type' field")
                if agp.get('type') == 'content_based' and 'config' not in agp:
                    errors.append("alert_grouping_parameters with type 'content_based' must have 'config' field")

        return len(errors) == 0, errors

    def clean(self):
        """Custom validation for the model"""
        super().clean()
        if self.pagerduty_config:
            is_valid, errors = self.validate_pagerduty_config()
            if not is_valid:
                from django.core.exceptions import ValidationError
                raise ValidationError({'pagerduty_config': errors})

    @property
    def services_using_template(self):
        """Get count of technical services using this template"""
        if self.template_type == PagerDutyTemplateTypeChoices.SERVICE_DEFINITION:
            return self.services_using_definition.count()
        elif self.template_type == PagerDutyTemplateTypeChoices.ROUTER_RULE:
            return self.services_using_router_rule.count()
        return 0

    def __str__(self):
        return self.name


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

    # PagerDuty Integration via Templates
    pagerduty_service_definition = models.ForeignKey(
        'PagerDutyTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services_using_definition',
        limit_choices_to={'template_type': PagerDutyTemplateTypeChoices.SERVICE_DEFINITION},
        help_text='PagerDuty service definition template'
    )
    pagerduty_router_rule = models.ForeignKey(
        'PagerDutyTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services_using_router_rule',
        limit_choices_to={'template_type': PagerDutyTemplateTypeChoices.ROUTER_RULE},
        help_text='PagerDuty router rule template'
    )

    pagerduty_routing_key = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='PagerDuty Routing Key',
        help_text='PagerDuty Events API v2 routing key (integration key) for this service.'
    )

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

    @property
    def has_pagerduty_integration(self):
        """Check if this service has complete PagerDuty integration (both templates required)"""
        return bool(self.pagerduty_service_definition and self.pagerduty_router_rule)

    @property
    def has_partial_pagerduty_integration(self):
        """Check if this service has partial PagerDuty integration (only one template)"""
        return bool((self.pagerduty_service_definition or self.pagerduty_router_rule) and not self.has_pagerduty_integration)

    def get_pagerduty_service_data(self):
        """Get PagerDuty service definition data in API format"""
        if not self.pagerduty_service_definition:
            return None
        return self.pagerduty_service_definition.pagerduty_config

    def get_pagerduty_router_data(self):
        """Get PagerDuty router rule data in API format"""
        if not self.pagerduty_router_rule:
            return None
        return self.pagerduty_router_rule.pagerduty_config

    @property
    def pagerduty_config(self):
        """Backward compatibility property for templates - returns the service definition config"""
        return self.get_pagerduty_service_data()

    @property
    def pagerduty_template_name(self):
        """Get the name of the PagerDuty service definition template (backward compatibility)"""
        return self.pagerduty_service_definition.name if self.pagerduty_service_definition else None

    @property
    def pagerduty_service_definition_name(self):
        """Get the name of the PagerDuty service definition template"""
        return self.pagerduty_service_definition.name if self.pagerduty_service_definition else None

    @property
    def pagerduty_router_rule_name(self):
        """Get the name of the PagerDuty router rule template"""
        return self.pagerduty_router_rule.name if self.pagerduty_router_rule else None

    def __str__(self):
        return self.name

    def get_pagerduty_routing_key_with_source(self):
        """
        Get PagerDuty routing key by traversing up the service dependency hierarchy.

        Algorithm:
        1. Check if this service has a routing key
        2. If not, find all upstream (parent) services
        3. Recursively check parents until a routing key is found
        4. Returns tuple of (routing_key, source_service_name) or (None, None)

        This ensures that routing keys configured on "root" services
        propagate down to all dependent services.
        """
        visited = set()

        def find_routing_key_upstream(service):
            """Recursively search upstream for routing key."""
            if service.id in visited:
                return None, None
            visited.add(service.id)

            # Check if this service has a routing key
            if service.pagerduty_routing_key:
                return service.pagerduty_routing_key, service.name

            # Get upstream (parent) services and check them
            # upstream_dependencies gives us ServiceDependency objects where this service is downstream
            for dependency in service.upstream_dependencies.all():
                upstream_service = dependency.upstream_service
                routing_key, source = find_routing_key_upstream(upstream_service)
                if routing_key:
                    return routing_key, source

            return None, None

        return find_routing_key_upstream(self)

    def get_root_services(self):
        """
        Get all root services (services with no upstream dependencies) in this service's hierarchy.
        """
        visited = set()
        roots = set()

        def find_roots(service):
            if service.id in visited:
                return
            visited.add(service.id)

            upstream_deps = service.upstream_dependencies.all()
            if not upstream_deps.exists():
                # This is a root service
                roots.add(service)
            else:
                for dep in upstream_deps:
                    find_roots(dep.upstream_service)

        find_roots(self)
        return list(roots)


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
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id     = models.PositiveIntegerField(null=True, blank=True)
    obj           = GenericForeignKey('content_type', 'object_id')
    message       = models.CharField(max_length=255)
    dedup_id      = models.CharField(max_length=128, db_index=True)
    status        = models.CharField(max_length=16, choices=EventStatus)
    criticallity  = models.CharField(max_length=10, choices=EventCrit)
    event_source  = models.ForeignKey('EventSource', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    raw           = models.JSONField()
    is_valid      = models.BooleanField(default=True, help_text='False if target object could not be found')

    @property
    def has_valid_target(self):
        """Check if this event has a valid target object."""
        return self.is_valid and self.content_type and self.object_id

    @property
    def target_display(self):
        """Get a display string for the target object."""
        if not self.has_valid_target:
            return "Invalid Target"
        if self.obj:
            return str(self.obj)
        return f"{self.content_type.model} (ID: {self.object_id})"

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

    # PagerDuty Integration
    pagerduty_dedup_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='PagerDuty deduplication key returned when incident was created'
    )

    class Meta:
        ordering = ['-created_at']

    def get_absolute_url(self):
        return reverse('plugins:business_application:incident_detail', args=[self.pk])

    def __str__(self):
        return self.title