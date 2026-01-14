"""
Automatic workflow triggering for incidents.

This module provides the automation engine that:
1. Finds applicable workflows based on incident's affected services
2. Traverses service hierarchy to find workflows on upstream (parent) services
3. Evaluates workflow conditions
4. Executes matching workflows automatically
"""
import logging
from typing import List, Tuple, Set, Optional

logger = logging.getLogger(__name__)


class IncidentWorkflowEngine:
    """
    Engine for auto-triggering workflows on incident lifecycle events.

    This engine handles:
    - Service hierarchy traversal (finding workflows on upstream services)
    - Workflow condition evaluation
    - Automatic execution via the shared WorkflowExecutor
    """

    # Valid trigger events for incidents
    VALID_TRIGGER_EVENTS = [
        'on_create',
        'on_update',
        'on_resolve',
        'on_acknowledge',
        'on_status_change',
    ]

    def find_workflows_for_incident(
        self,
        incident,
        trigger_event: str,
        context: dict = None
    ) -> List[Tuple['ExternalWorkflow', Optional['TechnicalService']]]:
        """
        Find all workflows that should trigger for an incident.

        Strategy:
        1. Traverse affected services + their upstream services
        2. Find global workflows (no service association)
        3. Evaluate conditions for each candidate

        Args:
            incident: Incident instance
            trigger_event: Event that occurred ('on_create', 'on_resolve', etc.)
            context: Additional context for condition evaluation

        Returns:
            List of (workflow, source_service_or_none) tuples
        """
        from business_application.models import ExternalWorkflow

        results = []
        seen_ids = set()

        # 1. Service hierarchy traversal
        for service in incident.affected_services.all():
            service_workflows = self._traverse_upstream_for_workflows(
                service, trigger_event, set()
            )
            for workflow, source_service in service_workflows:
                if workflow.id in seen_ids:
                    continue

                # Evaluate conditions
                should_trigger, reason = workflow.should_auto_trigger(
                    incident, trigger_event, context
                )
                if should_trigger:
                    seen_ids.add(workflow.id)
                    results.append((workflow, source_service))
                    logger.debug(
                        f"Workflow '{workflow.name}' matched via service '{source_service.name}'"
                    )
                else:
                    logger.debug(f"Workflow '{workflow.name}' skipped: {reason}")

        # 2. Global workflows (no service association)
        global_workflows = ExternalWorkflow.objects.filter(
            enabled=True,
            auto_trigger=True,
            object_type='incident'
        ).exclude(id__in=seen_ids)

        for workflow in global_workflows:
            # Skip if workflow has services associated (already handled above)
            if workflow.services.exists():
                continue

            # Check trigger event
            if trigger_event not in (workflow.trigger_events or []):
                continue

            # Evaluate conditions
            should_trigger, reason = workflow.should_auto_trigger(
                incident, trigger_event, context
            )
            if should_trigger:
                results.append((workflow, None))
                logger.debug(f"Global workflow '{workflow.name}' matched")
            else:
                logger.debug(f"Global workflow '{workflow.name}' skipped: {reason}")

        return results

    def _traverse_upstream_for_workflows(
        self,
        service,
        trigger_event: str,
        visited: Set[int]
    ) -> List[Tuple['ExternalWorkflow', 'TechnicalService']]:
        """
        Recursively find workflows from service and its upstream (parent) services.

        Args:
            service: TechnicalService to start from
            trigger_event: Event to match
            visited: Set of already visited service IDs (circular dependency protection)

        Returns:
            List of (workflow, source_service) tuples
        """
        if service.id in visited:
            return []
        visited.add(service.id)

        results = []

        # Get workflows directly on this service
        for workflow in service.workflows.filter(
            enabled=True,
            auto_trigger=True,
            object_type='incident'
        ):
            if trigger_event in (workflow.trigger_events or []):
                results.append((workflow, service))

        # Traverse upstream services
        for dep in service.upstream_dependencies.all():
            upstream = dep.upstream_service

            # Get workflows on upstream that propagate to downstream
            for workflow in upstream.workflows.filter(
                enabled=True,
                auto_trigger=True,
                object_type='incident',
                propagate_to_downstream=True
            ):
                if trigger_event in (workflow.trigger_events or []):
                    results.append((workflow, upstream))

            # Continue traversing upstream
            upstream_results = self._traverse_upstream_for_workflows(
                upstream, trigger_event, visited.copy()
            )
            results.extend(upstream_results)

        return results

    def determine_trigger_events(
        self,
        created: bool,
        old_status: str,
        new_status: str
    ) -> List[str]:
        """
        Determine which trigger events apply to this incident change.

        Args:
            created: Whether the incident was just created
            old_status: Previous status (None if created)
            new_status: New status

        Returns:
            List of applicable trigger events
        """
        events = []

        if created:
            events.append('on_create')
            return events

        events.append('on_update')

        if old_status != new_status:
            events.append('on_status_change')

            # Check for specific status transitions
            resolved_statuses = ('resolved', 'closed')
            if new_status in resolved_statuses and old_status not in resolved_statuses:
                events.append('on_resolve')

            if new_status == 'investigating' and old_status == 'new':
                events.append('on_acknowledge')

        return events

    def execute_for_incident(
        self,
        incident,
        created: bool,
        old_status: str = None,
        new_status: str = None,
        user=None
    ) -> List[dict]:
        """
        Main entry point: Find and execute all applicable workflows for an incident.

        Args:
            incident: Incident instance
            created: Whether incident was just created
            old_status: Previous status
            new_status: Current status
            user: Optional user who triggered the change

        Returns:
            List of execution result dicts
        """
        from business_application.utils.workflow_executor import workflow_executor

        # Determine which trigger events apply
        trigger_events = self.determine_trigger_events(created, old_status, new_status)

        logger.info(
            f"Checking incident workflows: incident={incident.pk}, "
            f"events={trigger_events}, status={old_status}->{new_status}"
        )

        # Build context for condition evaluation
        context = {
            'old_status': old_status,
            'new_status': new_status,
            'created': created,
        }

        results = []
        executed_workflow_ids = set()  # Prevent duplicate executions in same batch

        for trigger_event in trigger_events:
            workflows = self.find_workflows_for_incident(incident, trigger_event, context)

            for workflow, source_service in workflows:
                # Skip if already executed in this batch
                if workflow.id in executed_workflow_ids:
                    continue
                executed_workflow_ids.add(workflow.id)

                try:
                    # Build trigger metadata
                    trigger_meta = {
                        'trigger_event': trigger_event,
                        'source_service': source_service.name if source_service else None,
                        'source_service_id': source_service.id if source_service else None,
                        'auto_triggered': True,
                        'old_status': old_status,
                        'new_status': new_status,
                    }

                    # Execute via shared executor
                    result = workflow_executor.execute(
                        workflow=workflow,
                        source_obj=incident,
                        user=user,
                        trigger_meta=trigger_meta
                    )

                    results.append({
                        'workflow': workflow.name,
                        'workflow_id': workflow.id,
                        'execution_log_id': result.get('execution_log_id'),
                        'success': result.get('success', False),
                        'source_service': source_service.name if source_service else None,
                        'trigger_event': trigger_event,
                        'error': result.get('error'),
                    })

                    logger.info(
                        f"Workflow '{workflow.name}' {'succeeded' if result.get('success') else 'failed'} "
                        f"for incident {incident.pk} (trigger: {trigger_event})"
                    )

                except Exception as e:
                    logger.exception(f"Failed to execute workflow '{workflow.name}': {e}")
                    results.append({
                        'workflow': workflow.name,
                        'workflow_id': workflow.id,
                        'success': False,
                        'source_service': source_service.name if source_service else None,
                        'trigger_event': trigger_event,
                        'error': str(e),
                    })

        return results


# Singleton instance for easy access
incident_workflow_engine = IncidentWorkflowEngine()

