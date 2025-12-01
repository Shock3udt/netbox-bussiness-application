# business_application/templatetags/pagerduty_filters.py
"""
Template filters for PagerDuty integration.
Includes filters for masking sensitive values like routing keys.
"""

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def mask_routing_key(value):
    """
    Mask a routing key for display, showing only first 4 and last 4 characters.

    Example:
        Input:  "abc123def456ghi789"
        Output: "abc1••••••••i789"

    Usage in template:
        {{ object.pagerduty_routing_key|mask_routing_key }}
    """
    if not value:
        return None

    value = str(value)

    if len(value) <= 8:
        return "••••••••"

    visible_start = value[:4]
    visible_end = value[-4:]
    masked_middle = "•" * min(len(value) - 8, 8)  # Max 8 dots in middle

    return f"{visible_start}{masked_middle}{visible_end}"


@register.filter
def mask_routing_key_html(value):
    """
    Mask a routing key for display with HTML formatting.
    Shows a badge indicating the key is set, with masked value.

    Usage in template:
        {{ object.pagerduty_routing_key|mask_routing_key_html|safe }}
    """
    if not value:
        return format_html(
            '<span class="text-muted"><i class="mdi mdi-key-remove"></i> Not configured</span>'
        )

    masked = mask_routing_key(value)
    return format_html(
        '<code class="text-success"><i class="mdi mdi-key"></i> {}</code>',
        masked
    )


@register.filter
def has_routing_key(obj):
    """
    Check if an object has a pagerduty_routing_key set.

    Usage in template:
        {% if object|has_routing_key %}...{% endif %}
    """
    return bool(getattr(obj, 'pagerduty_routing_key', None))


@register.simple_tag
def routing_key_status_badge(obj):
    """
    Display a status badge for routing key configuration.

    Usage in template:
        {% routing_key_status_badge object %}
    """
    routing_key = getattr(obj, 'pagerduty_routing_key', None)

    if routing_key:
        masked = mask_routing_key(routing_key)
        return format_html(
            '<span class="badge bg-success" title="Routing key configured: {}">'
            '<i class="mdi mdi-key"></i> Configured</span>',
            masked
        )
    else:
        return format_html(
            '<span class="badge bg-secondary" title="No routing key - will inherit from parent services">'
            '<i class="mdi mdi-key-chain"></i> Inherited</span>'
        )


@register.inclusion_tag('business_application/includes/routing_key_display.html')
def routing_key_display(obj, show_inheritance=True):
    """
    Display routing key information with inheritance details.

    Usage in template:
        {% routing_key_display object %}
        {% routing_key_display object show_inheritance=False %}
    """
    routing_key = getattr(obj, 'pagerduty_routing_key', None)

    effective_key = None
    effective_source = None

    if hasattr(obj, 'get_pagerduty_routing_key_with_source'):
        effective_key, effective_source = obj.get_pagerduty_routing_key_with_source()
    elif routing_key:
        effective_key = routing_key
        effective_source = f"{obj._meta.verbose_name}: {obj}"

    return {
        'obj': obj,
        'has_own_key': bool(routing_key),
        'own_key_masked': mask_routing_key(routing_key) if routing_key else None,
        'effective_key_masked': mask_routing_key(effective_key) if effective_key else None,
        'effective_source': effective_source,
        'show_inheritance': show_inheritance,
    }