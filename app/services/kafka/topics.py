"""Kafka topic names for the DurgasOS event fabric.

Kernel analogy: Interrupt Request (IRQ) lines — each topic is a dedicated
channel for a class of system events.
"""

# Workflow lifecycle
WORKFLOW_RUN_REQUESTED = "workflow.run.requested"
WORKFLOW_RUN_EVENT = "workflow.run.event"
WORKFLOW_RUN_COMPLETED = "workflow.run.completed"
WORKFLOW_RUN_FAILED = "workflow.run.failed"

# File / document events
FILE_UPLOADED = "file.uploaded"
FILE_EMBEDDED = "file.embedded"
FILE_DELETED = "file.deleted"

# AI / agent events
AGENT_STEP = "agent.step"
AGENT_COMPLETED = "agent.completed"
LLM_REQUEST = "llm.request"
LLM_RESPONSE = "llm.response"

# User / auth events
USER_CREATED = "user.created"
USER_LOGIN = "user.login"
SESSION_EXPIRED = "session.expired"

# OS desktop events
OS_DESKTOP_EVENT = "os.desktop.event"
NOTIFICATION_SENT = "notification.sent"
SYSTEM_FEED = "system.feed"

# Infrastructure monitoring
SYSTEM_HEALTH_ALERT = "system.health.alert"
METRIC_RECORDED = "metric.recorded"

# All topics — used to pre-create them at startup
ALL_TOPICS = [
    WORKFLOW_RUN_REQUESTED,
    WORKFLOW_RUN_EVENT,
    WORKFLOW_RUN_COMPLETED,
    WORKFLOW_RUN_FAILED,
    FILE_UPLOADED,
    FILE_EMBEDDED,
    FILE_DELETED,
    AGENT_STEP,
    AGENT_COMPLETED,
    LLM_REQUEST,
    LLM_RESPONSE,
    USER_CREATED,
    USER_LOGIN,
    SESSION_EXPIRED,
    OS_DESKTOP_EVENT,
    NOTIFICATION_SENT,
    SYSTEM_FEED,
    SYSTEM_HEALTH_ALERT,
    METRIC_RECORDED,
]
