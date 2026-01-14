"""
Shared workflow execution logic for AAP and N8N workflows.

This module provides a unified interface for executing external workflows,
used by both API endpoints (manual execution) and automation engine (auto-triggering).
"""
import logging
from typing import Optional
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import requests as http_requests

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Executes external workflows (AAP/N8N) and manages execution logs.

    This class centralizes all workflow execution logic to prevent code duplication
    between API views and the automation engine.
    """

    def __init__(self):
        from business_application.config import external_workflow_config
        self.config = external_workflow_config

    def execute(
        self,
        workflow,
        source_obj,
        params: dict = None,
        user=None,
        trigger_meta: dict = None
    ) -> dict:
        """
        Execute a workflow and create an execution log.

        Args:
            workflow: ExternalWorkflow instance
            source_obj: The source object (Device, Incident, etc.)
            params: Pre-computed parameters (if None, will be computed from attribute_mapping)
            user: Optional user who triggered the execution
            trigger_meta: Optional metadata about what triggered the execution

        Returns:
            dict with keys: success, message, execution_id, execution_log_id, details, error
        """
        from business_application.models import WorkflowExecution, WorkflowExecutionStatus

        content_type = ContentType.objects.get_for_model(source_obj)

        # Generate parameters if not provided
        if params is None:
            params = workflow.get_mapped_parameters(source_obj)

        # Add trigger metadata if provided
        if trigger_meta:
            params['_trigger_meta'] = trigger_meta

        # Create execution log
        execution_log = WorkflowExecution.objects.create(
            workflow=workflow,
            user=user,
            content_type=content_type,
            object_id=source_obj.pk,
            status=WorkflowExecutionStatus.RUNNING,
            parameters_sent=params
        )

        try:
            # Execute based on workflow type
            if workflow.workflow_type == 'aap':
                result = self._execute_aap(workflow, params, source_obj)
            elif workflow.workflow_type == 'n8n':
                result = self._execute_n8n(workflow, params, source_obj)
            else:
                result = {
                    'success': False,
                    'message': f'Unknown workflow type: {workflow.workflow_type}',
                    'error_message': f'Unknown workflow type: {workflow.workflow_type}',
                    'details': {}
                }

            # Update execution log with result
            execution_log.status = (
                WorkflowExecutionStatus.SUCCESS if result.get('success')
                else WorkflowExecutionStatus.FAILED
            )
            execution_log.execution_id = result.get('execution_id')
            execution_log.response_data = result.get('details', {})
            execution_log.error_message = result.get('error_message') if not result.get('success') else None

        except Exception as e:
            logger.exception(f'Error executing workflow {workflow.name}: {e}')
            execution_log.status = WorkflowExecutionStatus.FAILED
            execution_log.error_message = str(e)
            result = {
                'success': False,
                'message': f'Execution failed: {str(e)}',
                'error_message': str(e),
                'details': {}
            }

        execution_log.completed_at = timezone.now()
        execution_log.save()

        logger.info(
            f"Workflow '{workflow.name}' execution {execution_log.status} "
            f"for {source_obj.__class__.__name__} {source_obj.pk}"
        )

        return {
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'execution_id': result.get('execution_id'),
            'execution_log_id': execution_log.pk,
            'details': result.get('details', {}),
            'error': result.get('error_message')
        }

    def _execute_aap(self, workflow, params: dict, source_obj) -> dict:
        """Execute an AAP workflow or job template."""
        from requests.auth import HTTPBasicAuth

        try:
            # Get AAP configuration
            aap_auth_type = self.config.AAP_AUTH_TYPE
            aap_token = self.config.AAP_TOKEN
            aap_username = self.config.AAP_USERNAME
            aap_password = self.config.AAP_PASSWORD
            verify_ssl = self.config.AAP_VERIFY_SSL
            timeout = self.config.AAP_TIMEOUT

            # Use workflow-specific URL or fall back to default
            aap_url = workflow.aap_url or self.config.AAP_DEFAULT_URL

            if not aap_url:
                return {
                    'success': False,
                    'message': 'AAP URL not configured. Set aap_url on the workflow or aap_default_url in plugin config.',
                    'error_message': 'AAP URL not configured',
                    'details': {}
                }

            # Determine the API endpoint based on resource type
            if workflow.aap_resource_type == 'workflow':
                endpoint = f"{aap_url.rstrip('/')}/api/v2/workflow_job_templates/{workflow.aap_resource_id}/launch/"
            else:  # job_template
                endpoint = f"{aap_url.rstrip('/')}/api/v2/job_templates/{workflow.aap_resource_id}/launch/"

            # Build payload
            payload = {}

            # Add extra_vars if present in mapped params
            if 'extra_vars' in params:
                payload['extra_vars'] = params['extra_vars']
            elif params:
                # If no explicit extra_vars, use all params as extra_vars
                # But filter out internal metadata
                filtered_params = {k: v for k, v in params.items() if not k.startswith('_')}
                if filtered_params:
                    payload['extra_vars'] = filtered_params

            # Add limit if present
            if 'limit' in params:
                payload['limit'] = params['limit']

            logger.info(
                f'Executing AAP {workflow.aap_resource_type} {workflow.aap_resource_id} '
                f'at {aap_url} using {aap_auth_type} auth'
            )

            # Determine authentication method
            auth = None
            headers = {'Content-Type': 'application/json'}

            if aap_auth_type == 'basic':
                if not aap_username or not aap_password:
                    logger.warning('AAP basic auth credentials not configured - running in simulation mode')
                    return {
                        'success': True,
                        'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully (simulation mode)',
                        'execution_id': f'aap-sim-{workflow.aap_resource_id}-{source_obj.pk}',
                        'details': {
                            'note': 'AAP basic auth credentials not configured.',
                            'endpoint': endpoint,
                            'payload': payload,
                            'simulation': True
                        }
                    }
                auth = HTTPBasicAuth(aap_username, aap_password)
            else:
                # Token authentication (default)
                if not aap_token:
                    logger.warning('AAP token not configured - running in simulation mode')
                    return {
                        'success': True,
                        'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully (simulation mode)',
                        'execution_id': f'aap-sim-{workflow.aap_resource_id}-{source_obj.pk}',
                        'details': {
                            'note': 'AAP token not configured.',
                            'endpoint': endpoint,
                            'payload': payload,
                            'simulation': True
                        }
                    }
                headers['Authorization'] = f'Bearer {aap_token}'

            # Make the actual API call
            response = http_requests.post(
                endpoint,
                json=payload,
                headers=headers,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout
            )

            if response.status_code in [200, 201, 202]:
                data = response.json()
                job_id = data.get('id') or data.get('job') or data.get('workflow_job')
                return {
                    'success': True,
                    'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully',
                    'execution_id': str(job_id) if job_id else None,
                    'details': {
                        'job_id': job_id,
                        'status': data.get('status'),
                        'url': data.get('url'),
                        'created': data.get('created'),
                        'response_status_code': response.status_code
                    }
                }
            else:
                error_detail = response.text[:500] if response.text else 'No error details'
                logger.error(f'AAP API error: {response.status_code} - {error_detail}')
                return {
                    'success': False,
                    'message': f'AAP API returned error: {response.status_code}',
                    'error_message': error_detail,
                    'details': {
                        'status_code': response.status_code,
                        'error': error_detail
                    }
                }

        except http_requests.exceptions.Timeout:
            logger.exception('AAP request timeout')
            return {
                'success': False,
                'message': f'AAP request timed out after {timeout} seconds',
                'error_message': 'Request timeout',
                'details': {'timeout': timeout}
            }
        except http_requests.exceptions.ConnectionError as e:
            logger.exception(f'AAP connection error: {e}')
            return {
                'success': False,
                'message': f'Failed to connect to AAP: {e}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }
        except Exception as e:
            logger.exception(f'AAP execution error: {e}')
            return {
                'success': False,
                'message': f'Failed to execute AAP workflow: {e}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }

    def _execute_n8n(self, workflow, params: dict, source_obj) -> dict:
        """Execute an N8N webhook."""
        try:
            # Get N8N configuration
            n8n_api_key = self.config.N8N_API_KEY
            verify_ssl = self.config.N8N_VERIFY_SSL
            timeout = self.config.N8N_TIMEOUT

            webhook_url = workflow.n8n_webhook_url

            if not webhook_url:
                return {
                    'success': False,
                    'message': 'N8N webhook URL not configured on the workflow.',
                    'error_message': 'Webhook URL not configured',
                    'details': {}
                }

            # Build payload with object information
            # Filter out internal metadata keys from params
            filtered_params = {k: v for k, v in params.items() if not k.startswith('_')}

            payload = {
                'source': 'netbox',
                'object_type': workflow.object_type,
                'object_id': source_obj.pk,
                'object_name': str(source_obj),
                'workflow_name': workflow.name,
                **filtered_params
            }

            # Add trigger metadata separately if present
            if '_trigger_meta' in params:
                payload['trigger_meta'] = params['_trigger_meta']

            logger.info(f'Executing N8N webhook for workflow {workflow.name}')

            # Build headers
            headers = {'Content-Type': 'application/json'}

            # Add API key if configured
            if n8n_api_key:
                headers['X-N8N-API-KEY'] = n8n_api_key

            # Make the actual API call
            response = http_requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                verify=verify_ssl,
                timeout=timeout
            )

            if response.status_code in [200, 201, 202]:
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {'response_text': response.text[:500] if response.text else 'No response body'}

                execution_id = (
                    response.headers.get('X-Execution-Id') or
                    response.headers.get('X-N8N-Execution-Id')
                )

                return {
                    'success': True,
                    'message': 'N8N webhook triggered successfully',
                    'execution_id': execution_id,
                    'details': {
                        'response_status_code': response.status_code,
                        'execution_id': execution_id,
                        'response': response_data
                    }
                }
            else:
                error_detail = response.text[:500] if response.text else 'No error details'
                logger.error(f'N8N webhook error: {response.status_code} - {error_detail}')
                return {
                    'success': False,
                    'message': f'N8N webhook returned error: {response.status_code}',
                    'error_message': error_detail,
                    'details': {
                        'status_code': response.status_code,
                        'error': error_detail
                    }
                }

        except http_requests.exceptions.Timeout:
            logger.exception('N8N request timeout')
            return {
                'success': False,
                'message': f'N8N request timed out after {timeout} seconds',
                'error_message': 'Request timeout',
                'details': {'timeout': timeout}
            }
        except http_requests.exceptions.ConnectionError as e:
            logger.exception(f'N8N connection error: {e}')
            return {
                'success': False,
                'message': f'Failed to connect to N8N: {e}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }
        except Exception as e:
            logger.exception(f'N8N execution error: {e}')
            return {
                'success': False,
                'message': f'Failed to execute N8N webhook: {e}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }


# Singleton instance for easy access
workflow_executor = WorkflowExecutor()

