from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def event_status_badge(status, display_name=None):
    """
    Render an event status as a colored badge with icon.
    """
    if display_name is None:
        display_name = status.replace('_', ' ').title()

    badge_configs = {
        'triggered': {
            'class': 'bg-danger text-light',
            'icon': 'mdi-alert-circle',
            'label': 'Triggered'
        },
        'ok': {
            'class': 'bg-success text-light',
            'icon': 'mdi-check-circle',
            'label': 'OK'
        },
        'suppressed': {
            'class': 'bg-secondary text-light',
            'icon': 'mdi-volume-off',
            'label': 'Suppressed'
        }
    }

    config = badge_configs.get(status, {
        'class': 'bg-light text-dark',
        'icon': 'mdi-help-circle',
        'label': display_name or status
    })

    return mark_safe(
        f'<span class="badge {config["class"]}">'
        f'<i class="mdi {config["icon"]}"></i> {config["label"]}'
        f'</span>'
    )

@register.filter
def event_criticality_badge(criticality, display_name=None):
    """
    Render an event criticality as a colored badge with icon.
    """
    if display_name is None:
        display_name = criticality.replace('_', ' ').title()

    badge_configs = {
        'critical': {
            'class': 'bg-danger text-light',
            'icon': 'mdi-alert',
            'label': 'Critical'
        },
        'warning': {
            'class': 'bg-warning text-dark',
            'icon': 'mdi-alert-outline',
            'label': 'Warning'
        },
        'info': {
            'class': 'bg-info text-light',
            'icon': 'mdi-information',
            'label': 'Info'
        }
    }

    config = badge_configs.get(criticality, {
        'class': 'bg-light text-dark',
        'icon': 'mdi-help-circle',
        'label': display_name or criticality
    })

    return mark_safe(
        f'<span class="badge {config["class"]}">'
        f'<i class="mdi {config["icon"]}"></i> {config["label"]}'
        f'</span>'
    )

@register.filter
def event_validity_badge(is_valid):
    """
    Render an event validity status as a colored badge with icon.
    """
    if is_valid:
        return mark_safe(
            '<span class="badge bg-success text-light">'
            '<i class="mdi mdi-check-circle"></i> Valid'
            '</span>'
        )
    else:
        return mark_safe(
            '<span class="badge bg-danger text-light">'
            '<i class="mdi mdi-alert-circle"></i> Invalid'
            '</span>'
        )

@register.filter
def event_target_display(event):
    """
    Display the target object for an event, with special handling for invalid events.
    """
    if not event.has_valid_target:
        return mark_safe(
            '<span class="text-danger">'
            '<i class="mdi mdi-alert-circle-outline"></i> Invalid Target'
            '</span>'
        )
    return event.target_display

@register.filter
def maintenance_status_badge(status, display_name=None):
    """
    Render a maintenance status as a colored badge with icon.
    """
    if display_name is None:
        display_name = status.replace('_', ' ').title()

    badge_configs = {
        'planned': {
            'class': 'bg-primary text-light',
            'icon': 'mdi-calendar-clock',
            'label': 'Planned'
        },
        'started': {
            'class': 'bg-warning text-dark',
            'icon': 'mdi-wrench',
            'label': 'Started'
        },
        'finished': {
            'class': 'bg-success text-light',
            'icon': 'mdi-check-circle',
            'label': 'Finished'
        },
        'canceled': {
            'class': 'bg-secondary text-light',
            'icon': 'mdi-cancel',
            'label': 'Canceled'
        }
    }

    config = badge_configs.get(status, {
        'class': 'bg-light text-dark',
        'icon': 'mdi-help-circle',
        'label': display_name or status
    })

    return mark_safe(
        f'<span class="badge {config["class"]}">'
        f'<i class="mdi {config["icon"]}"></i> {config["label"]}'
        f'</span>'
    )

@register.filter
def incident_status_badge(status, display_name=None):
    """
    Render an incident status as a colored badge with icon.
    """
    if display_name is None:
        display_name = status.replace('_', ' ').title()

    badge_configs = {
        'new': {
            'class': 'bg-danger text-light',
            'icon': 'mdi-alert-circle',
            'label': 'New'
        },
        'investigating': {
            'class': 'bg-warning text-dark',
            'icon': 'mdi-magnify',
            'label': 'Investigating'
        },
        'identified': {
            'class': 'bg-info text-light',
            'icon': 'mdi-lightbulb',
            'label': 'Identified'
        },
        'monitoring': {
            'class': 'bg-primary text-light',
            'icon': 'mdi-monitor',
            'label': 'Monitoring'
        },
        'resolved': {
            'class': 'bg-success text-light',
            'icon': 'mdi-check-circle',
            'label': 'Resolved'
        },
        'closed': {
            'class': 'bg-secondary text-light',
            'icon': 'mdi-close-circle',
            'label': 'Closed'
        }
    }

    config = badge_configs.get(status, {
        'class': 'bg-light text-dark',
        'icon': 'mdi-help-circle',
        'label': display_name or status
    })

    return mark_safe(
        f'<span class="badge {config["class"]}">'
        f'<i class="mdi {config["icon"]}"></i> {config["label"]}'
        f'</span>'
    )

@register.filter
def incident_severity_badge(severity, display_name=None):
    """
    Render an incident severity as a colored badge with icon.
    """
    if display_name is None:
        display_name = severity.replace('_', ' ').title()

    badge_configs = {
        'critical': {
            'class': 'bg-danger text-light',
            'icon': 'mdi-alert',
            'label': 'Critical'
        },
        'high': {
            'class': 'bg-warning text-dark',
            'icon': 'mdi-alert-outline',
            'label': 'High'
        },
        'medium': {
            'class': 'bg-info text-light',
            'icon': 'mdi-information-outline',
            'label': 'Medium'
        },
        'low': {
            'class': 'bg-success text-light',
            'icon': 'mdi-information',
            'label': 'Low'
        }
    }

    config = badge_configs.get(severity, {
        'class': 'bg-light text-dark',
        'icon': 'mdi-help-circle',
        'label': display_name or severity
    })

    return mark_safe(
        f'<span class="badge {config["class"]}">'
        f'<i class="mdi {config["icon"]}"></i> {config["label"]}'
        f'</span>'
    )