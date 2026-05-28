"""JSON-RPC streaming: workflow.run and system.feed."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import importlib.util
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.database import AsyncSessionLocal
from app.models.durgasos_desktop import WorkflowDefinitionModel, WorkflowRunModel
from sqlalchemy import select
from app.utils.helpers import utc_now
from app.services.orbit.codegen import generate
from app.services.orbit.runner_state import (
    register_run,
    unregister_run,
    get_pause_event,
)
from app.services.kafka import publish_json
from app.services.kafka.topics import (
    SYSTEM_FEED,
    WORKFLOW_RUN_EVENT,
    WORKFLOW_RUN_REQUESTED,
)

logger = logging.getLogger(__name__)


async def handle_workflow_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    p = params or {}
    workflow_id = str(p.get("workflow_id") or p.get("id") or "").strip()
    if not workflow_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing workflow_id")

    owner = None
    if user and user.get("sub"):
        owner = str(user["sub"])
    run_id = str(uuid4())

    # 1. Load workflow graph definition from database
    async with AsyncSessionLocal() as db:
        stmt = select(WorkflowDefinitionModel).where(
            WorkflowDefinitionModel.id == workflow_id
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                f"Workflow definition {workflow_id} not found",
            )
        graph_data: dict[str, Any] = row.spec or {}

    # 2. Register run queue and pause event in shared registry
    queue = register_run(run_id)
    pause_event = get_pause_event(run_id)

    # 3. Create run-specific directory under data/orbit_runs
    run_dir = os.path.abspath(f"./data/orbit_runs/{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "run.log").replace("\\", "/")

    # 4. Generate workflow.py and state.py code
    try:
        inputs = p.get("inputs") or {}
        code = generate(graph_data, log_file_path=log_path, inputs=inputs)
        with open(os.path.join(run_dir, "workflow.py"), "w", encoding="utf-8") as f:
            f.write(code)

        state_code = f"""import asyncio
import time
from app.services.orbit.runner_state import get_queue, get_pause_event

run_id = "{run_id}"
pause_event = get_pause_event(run_id)

def report_node(node_id: str, status: str) -> None:
    q = get_queue(run_id)
    if q:
        q.put_nowait({{"type": "node_status", "node_id": node_id, "status": status}})

def report_node_output(node_id: str, output: object) -> None:
    q = get_queue(run_id)
    if q:
        q.put_nowait({{"type": "node_output", "node_id": node_id, "output": output}})

def report_node_log(node_id: str, line: str) -> None:
    entry = {{"t": round(time.time() * 1000), "msg": str(line)[:600]}}
    q = get_queue(run_id)
    if q:
        q.put_nowait({{"type": "node_log", "node_id": node_id, "entry": entry}})
"""
        with open(os.path.join(run_dir, "state.py"), "w", encoding="utf-8") as f:
            f.write(state_code)
    except Exception as e:
        unregister_run(run_id)
        logger.error(f"Codegen failed for run {run_id}: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Workflow compilation failed: {str(e)}"
        )

    # 5. Insert run_dir into sys.path and load dynamic modules
    sys.path.insert(0, run_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            "workflow", os.path.join(run_dir, "workflow.py")
        )
        if spec is None or spec.loader is None:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to create workflow module spec"
            )
        workflow_mod = importlib.util.module_from_spec(spec)
        sys.modules[f"workflow_{run_id}"] = workflow_mod
        spec.loader.exec_module(workflow_mod)
    except Exception as e:
        if run_dir in sys.path:
            sys.path.remove(run_dir)
        unregister_run(run_id)
        logger.error(
            f"Failed to load generated module for run {run_id}: {e}", exc_info=True
        )
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Module load failed: {str(e)}"
        )

    # 6. Publish request event to Kafka (backward compatibility / logging)
    await publish_json(
        WORKFLOW_RUN_REQUESTED,
        {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "owner_id": owner,
            "connection_id": connection_id,
        },
        key=run_id,
    )

    # 7. Create Workflow Run record in DB
    async with AsyncSessionLocal() as db:
        now = utc_now()
        run_row = WorkflowRunModel(
            id=run_id,
            workflow_id=workflow_id,
            owner_id=owner,
            status="running",
            events=[],
            created_at=now,
            updated_at=now,
        )
        db.add(run_row)
        await db.commit()

    # Yield started indicator
    yield {"type": "started", "run_id": run_id, "workflow_id": workflow_id}

    # 8. Start compiled workflow task and consume reports from the memory queue
    workflow_task = asyncio.create_task(workflow_mod.main(pause_event))
    recorded_events = []
    final_status = "success"

    try:
        while not workflow_task.done() or not queue.empty():
            try:
                # Wait for reports with timeout
                event = await asyncio.wait_for(queue.get(), timeout=0.1)

                out_msg = None
                if event["type"] == "node_status":
                    out_msg = {
                        "type": "event",
                        "message": f"[{event['node_id']}] Status: {event['status']}",
                        "node_id": event["node_id"],
                        "status": event["status"],
                    }
                elif event["type"] == "node_log":
                    out_msg = {
                        "type": "node_log",
                        "message": event["entry"]["msg"],
                        "node_id": event["node_id"],
                        "entry": event["entry"],
                    }
                elif event["type"] == "node_output":
                    out_msg = {
                        "type": "node_output",
                        "message": f"[{event['node_id']}] Output",
                        "node_id": event["node_id"],
                        "output": event["output"],
                    }

                if out_msg:
                    recorded_events.append(out_msg)
                    # Yield to client over WebSocket JSON-RPC
                    yield out_msg
                    # Optional duplicate back-compat Kafka logging
                    await publish_json(WORKFLOW_RUN_EVENT, out_msg, key=run_id)
            except asyncio.TimeoutError:
                continue

        # Raise exception if task crashed
        if workflow_task.done():
            task_exc = workflow_task.exception()
            if task_exc is not None:
                raise task_exc

    except asyncio.CancelledError:
        final_status = "stopped"
        workflow_task.cancel()
        try:
            await workflow_task
        except asyncio.CancelledError:
            pass
        yield {
            "type": "event",
            "message": "Workflow run stopped by user",
            "status": "stopped",
        }
        raise
    except Exception as e:
        final_status = "error"
        logger.error(f"Error during workflow run {run_id}: {e}", exc_info=True)
        yield {"type": "event", "message": f"Run error: {str(e)}", "status": "error"}
    finally:
        # Yield finished event
        yield {"type": "done", "run_id": run_id, "workflow_id": workflow_id}

        # Cleanup run context
        unregister_run(run_id)
        if run_dir in sys.path:
            sys.path.remove(run_dir)
        sys.modules.pop(f"workflow_{run_id}", None)

        # Update run record status and logs in the database
        async with AsyncSessionLocal() as db:
            run_stmt = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id)
            row_run = (await db.execute(run_stmt)).scalar_one_or_none()
            if row_run:
                row_run.status = final_status
                row_run.events = recorded_events
                row_run.updated_at = utc_now()
                await db.commit()


async def handle_system_feed(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    p = params or {}
    topic = str(p.get("topic") or "default")
    owner = user.get("sub") if user else None

    for i in range(6):
        await asyncio.sleep(0.1)
        line: Dict[str, Any] = {
            "type": "event",
            "topic": topic,
            "seq": i,
            "message": f"[{topic}] tick {i + 1}",
        }
        await publish_json(
            SYSTEM_FEED,
            {"connection_id": connection_id, "owner_id": owner, **line},
            key=connection_id or "anon",
        )
        yield line

    yield {"type": "done", "topic": topic}


def get_methods() -> Dict[str, Any]:
    return {
        "workflow.run": handle_workflow_run,
        "system.feed": handle_system_feed,
    }
