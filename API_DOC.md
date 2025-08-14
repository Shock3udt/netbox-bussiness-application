[utils](../../netbox-bussiness-application/business_application/utils)# NetBox AIOPS Alert Ingestion API Documentation

## Overview

The NetBox AIOPS plugin provides several API endpoints for ingesting alerts from various monitoring and alerting systems. All endpoints require authentication using NetBox API tokens.

## Authentication

All API requests must include a valid NetBox API token in the Authorization header:

```
Authorization: Token <your-netbox-api-token>
```

### Required Permissions

The API token must have the following permissions:
- `business_application.add_event` - Create new events
- `business_application.add_incident` - Create new incidents  
- `business_application.change_incident` - Update existing incidents

## Base URL

All endpoints are available under:
```
https://<netbox-instance>/api/plugins/business-application/
```

## Endpoints

### 1. Generic Alert Endpoint

**URL:** `POST /api/plugins/business-application/alerts/generic/`

**Description:** Accept standardized alert payloads from any monitoring system.

**Request Headers:**
```
Content-Type: application/json
Authorization: Token <your-api-token>
```

**Request Body:**
```json
{
  "source": "monitoring-system",
  "timestamp": "2025-01-10T10:00:00Z",
  "severity": "critical",
  "status": "triggered",
  "message": "High CPU usage detected on production server",
  "dedup_id": "cpu-alert-prod-server-001",
  "target": {
    "type": "device",
    "identifier": "prod-server-01.example.com"
  },
  "raw_data": {
    "cpu_usage": 95.5,
    "threshold": 90,
    "duration": "5 minutes"
  }
}
```

**Field Descriptions:**
- `source` (string, required): Name of the monitoring system
- `timestamp` (ISO 8601 datetime, optional): When the alert was triggered. Defaults to current time
- `severity` (string, required): One of: `critical`, `high`, `medium`, `low`
- `status` (string, required): One of: `triggered`, `ok`, `suppressed`
- `message` (string, required): Human-readable alert description
- `dedup_id` (string, required): Unique identifier for deduplication
- `target` (object, required):
  - `type` (string): One of: `device`, `vm`, `service`
  - `identifier` (string): Hostname, VM name, or service identifier
- `raw_data` (object, optional): Original alert data for reference

**Success Response:**
```json
{
  "status": "success",
  "event_id": 123,
  "incident_id": 45,
  "message": "Alert processed successfully"
}
```

**Error Response:**
```json
{
  "errors": {
    "severity": ["Invalid choice. Choose from: critical, high, medium, low"],
    "dedup_id": ["This field is required"]
  }
}
```

### 2. Capacitor Alert Endpoint

**URL:** `POST /api/plugins/business-application/alerts/capacitor/`

**Description:** Specialized endpoint for Capacitor monitoring alerts.

**Request Body:**
```json
{
  "alert_id": "CAP-2025-001",
  "device_name": "router-core-01",
  "description": "Interface eth0 down",
  "priority": 1,
  "state": "ALARM",
  "alert_time": "2025-01-10T10:00:00Z",
  "metric_name": "interface_status",
  "metric_value": 0,
  "threshold": 1
}
```

**Field Descriptions:**
- `alert_id` (string, required): Capacitor alert identifier
- `device_name` (string, required): Target device name
- `description` (string, required): Alert description
- `priority` (integer, required): 1-5, where 1 is most critical
- `state` (string, required): One of: `ALARM`, `OK`, `INSUFFICIENT_DATA`
- `alert_time` (ISO 8601 datetime, optional): Alert timestamp
- `metric_name` (string, optional): Metric that triggered the alert
- `metric_value` (float, optional): Current metric value
- `threshold` (float, optional): Threshold value

### 3. SignalFX Alert Endpoint

**URL:** `POST /api/plugins/business-application/alerts/signalfx/`

**Description:** Webhook endpoint for SignalFX alerts.

**Request Body:**
```json
{
  "incidentId": "SFX123456",
  "alertState": "TRIGGERED",
  "alertMessage": "Memory usage above 90% for 5 minutes",
  "severity": "critical",
  "timestamp": 1736510400000,
  "dimensions": {
    "host": "app-server-01",
    "environment": "production",
    "service": "web-api"
  },
  "detectorName": "High Memory Usage",
  "detectorUrl": "https://app.signalfx.com/detector/ABC123",
  "rule": "memory.utilization > 90 for 5m"
}
```

**Field Descriptions:**
- `incidentId` (string, required): SignalFX incident ID
- `alertState` (string, required): One of: `TRIGGERED`, `RESOLVED`, `STOPPED`
- `alertMessage` (string, required): Alert description
- `severity` (string, optional): Alert severity
- `timestamp` (integer, optional): Unix timestamp in milliseconds
- `dimensions` (object, optional): SignalFX dimensions/tags
- `detectorName` (string, optional): Name of the SignalFX detector
- `detectorUrl` (string, optional): Link to detector in SignalFX
- `rule` (string, optional): Detection rule that triggered

### 4. Email Alert Endpoint

**URL:** `POST /api/plugins/business-application/alerts/email/`

**Description:** Process alerts received via email (typically from N8N).

**Request Body:**
```json
{
  "message_id": "<unique-email-id@example.com>",
  "subject": "ALERT: Database connection pool exhausted",
  "body": "The database connection pool for app-db-01 has been exhausted. Current connections: 100/100",
  "sender": "monitoring@example.com",
  "timestamp": "2025-01-10T10:00:00Z",
  "severity": "high",
  "target_type": "service",
  "target_identifier": "app-db-01",
  "headers": {
    "X-Priority": "1",
    "X-Alert-Source": "database-monitor"
  }
}
```

**Field Descriptions:**
- `message_id` (string, required): Email message ID for deduplication
- `subject` (string, required): Email subject line
- `body` (string, required): Email body content
- `sender` (string, required): Email sender address
- `timestamp` (ISO 8601 datetime, optional): When email was received
- `severity` (string, optional): Parsed severity level
- `target_type` (string, optional): Type of target system
- `target_identifier` (string, optional): Target system identifier
- `headers` (object, optional): Additional email headers
- `attachments` (array, optional): List of attachment metadata

## Examples

### Example 1: Generic Alert with cURL

```bash
curl -X POST https://netbox.example.com/api/plugins/business-application/alerts/generic/ \
  -H "Authorization: Token abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "prometheus",
    "timestamp": "2025-01-10T10:00:00Z",
    "severity": "high",
    "status": "triggered",
    "message": "Disk space low on /var partition",
    "dedup_id": "disk-alert-prod-app-01-var",
    "target": {
      "type": "device",
      "identifier": "prod-app-01"
    },
    "raw_data": {
      "filesystem": "/var",
      "usage_percent": 95,
      "free_gb": 2.5
    }
  }'
```

### Example 2: Python Script for Capacitor Integration

```python
import requests
import json
from datetime import datetime

NETBOX_URL = "https://netbox.example.com"
API_TOKEN = "your-api-token"

def send_capacitor_alert(alert_data):
    """Send a Capacitor alert to NetBox AIOPS."""
    
    url = f"{NETBOX_URL}/api/plugins/business-application/alerts/capacitor/"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "alert_id": alert_data["id"],
        "device_name": alert_data["device"],
        "description": alert_data["message"],
        "priority": alert_data["priority"],
        "state": alert_data["state"],
        "alert_time": datetime.now().isoformat(),
        "metric_name": alert_data.get("metric"),
        "metric_value": alert_data.get("value"),
        "threshold": alert_data.get("threshold")
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        result = response.json()
        print(f"Alert processed: Event ID {result['event_id']}")
        if result.get("incident_id"):
            print(f"Incident created/updated: ID {result['incident_id']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

# Example usage
alert = {
    "id": "CAP-001",
    "device": "switch-core-01",
    "message": "Port 24 flapping detected",
    "priority": 2,
    "state": "ALARM",
    "metric": "port_status_changes",
    "value": 15,
    "threshold": 5
}

send_capacitor_alert(alert)
```

### Example 3: SignalFX Webhook Configuration

Configure your SignalFX detector to send webhooks to:
```
https://netbox.example.com/api/plugins/business-application/alerts/signalfx/
```

Add custom headers:
```
Authorization: Token your-api-token
Content-Type: application/json
```

### Example 4: N8N Workflow for Email Processing

```json
{
  "nodes": [
    {
      "name": "Email Trigger",
      "type": "n8n-nodes-base.emailReadImap",
      "parameters": {
        "mailbox": "INBOX",
        "filters": {
          "subject": ["ALERT:", "WARNING:", "CRITICAL:"]
        }
      }
    },
    {
      "name": "Parse Alert",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": `
          const subject = $input.item.json.subject;
          const body = $input.item.json.text;
          const messageId = $input.item.json.messageId;
          
          // Extract severity from subject
          let severity = 'medium';
          if (subject.includes('CRITICAL')) severity = 'critical';
          else if (subject.includes('WARNING')) severity = 'high';
          
          // Extract target from body (customize based on your format)
          const targetMatch = body.match(/Server: (\\S+)/);
          const target = targetMatch ? targetMatch[1] : 'unknown';
          
          return {
            message_id: messageId,
            subject: subject,
            body: body,
            sender: $input.item.json.from.text,
            severity: severity,
            target_type: 'device',
            target_identifier: target
          };
        `
      }
    },
    {
      "name": "Send to NetBox",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://netbox.example.com/api/plugins/business-application/alerts/email/",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "httpHeaderAuth": {
          "name": "Authorization",
          "value": "Token your-api-token"
        },
        "bodyParametersUi": {
          "parameter": "={{ $json }}"
        }
      }
    }
  ]
}
```

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "errors": {
    "field_name": ["Error description"]
  }
}
```

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**500 Internal Server Error:**
```json
{
  "error": "Failed to process alert",
  "details": "Error description"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Default: 100 requests per minute per API token
- Burst: Up to 200 requests allowed
- Response header: `X-RateLimit-Remaining`

## Best Practices

1. **Use Deduplication IDs:** Always provide unique, consistent `dedup_id` values to prevent duplicate alerts
2. **Include Raw Data:** Preserve original alert data in `raw_data` for debugging
3. **Accurate Timestamps:** Provide accurate timestamps to ensure proper correlation
4. **Target Resolution:** Use exact NetBox device/VM names for proper correlation
5. **Error Handling:** Implement retry logic with exponential backoff
6. **Monitoring:** Monitor API response times and success rates

## Webhook Security (Optional)

For additional security, you can implement webhook signature validation:

1. **Capacitor:** Include `X-Capacitor-Signature` header
2. **SignalFX:** Include `X-SignalFx-Signature` header
3. **Custom:** Use HMAC-SHA256 with shared secret

Example signature validation:
```python
import hmac
import hashlib

def validate_webhook_signature(request, secret):
    """Validate webhook signature."""
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        return False
    
    expected = hmac.new(
        secret.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, f"sha256={expected}")
```