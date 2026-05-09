"""
Queue management for fal.ai asynchronous jobs
Handles polling with exponential backoff and webhook support
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from app.config import settings
from .client import FalClient
from .models import JobStatus

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manages asynchronous job queue operations including polling and webhook handling.
    """

    def __init__(self, client: FalClient):
        """
        Initialize queue manager.

        Args:
            client: FalClient instance for API calls
        """
        self.client = client
        self.polling_interval = settings.fal_polling_interval
        self.max_attempts = settings.fal_max_polling_attempts
        # In-memory storage for webhook callbacks (can be replaced with Redis)
        self._webhook_callbacks: Dict[str, Callable] = {}

    async def wait_for_completion(
        self,
        status_url: str,
        response_url: str,
        callback: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Poll job status until completion or failure.
        Uses exponential backoff for polling intervals.

        Args:
            status_url: URL to check job status
            response_url: URL to retrieve final result
            callback: Optional callback function(status, result) called when job completes

        Returns:
            Final job result (images, video, audio, etc.)

        Raises:
            TimeoutError: If job doesn't complete within max attempts
            Exception: If job fails
        """
        attempt = 0
        current_interval = self.polling_interval

        while attempt < self.max_attempts:
            try:
                status_response = await self.client.get_status(status_url)
                status = status_response.get("status")
                request_id = status_response.get("request_id")

                logger.debug(
                    f"Job {request_id} status: {status} (attempt {attempt + 1}/{self.max_attempts})"
                )

                if status == JobStatus.COMPLETED:
                    # Job completed, fetch result
                    result = await self.client.get_result(response_url)

                    if callback:
                        try:
                            await callback(status_response, result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                    return result

                elif status == JobStatus.FAILED:
                    error_msg = status_response.get("error", "Job failed")
                    logger.error(f"Job {request_id} failed: {error_msg}")
                    raise Exception(f"Job failed: {error_msg}")

                # Job still in queue or processing
                queue_position = status_response.get("queue_position")
                if queue_position is not None:
                    logger.debug(
                        f"Job {request_id} in queue at position {queue_position}"
                    )

                # Exponential backoff: start with polling_interval, max at 30s
                await asyncio.sleep(min(current_interval, 30.0))
                current_interval = min(
                    current_interval * 1.2, 30.0
                )  # Increase by 20%, cap at 30s
                attempt += 1

            except Exception as e:
                # Retry on transient errors
                if attempt < self.max_attempts - 1:
                    logger.warning(
                        f"Status check error (attempt {attempt + 1}): {e}, retrying..."
                    )
                    await asyncio.sleep(current_interval)
                    attempt += 1
                else:
                    raise

        # Timeout
        raise TimeoutError(
            f"Job did not complete within {self.max_attempts} attempts "
            f"(~{self.max_attempts * self.polling_interval}s)"
        )

    def register_webhook(
        self, job_id: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]
    ) -> bool:
        """
        Register a webhook callback for job completion.

        Args:
            job_id: Job request ID
            callback: Async callback function(status, result) to call when job completes

        Returns:
            True if registered successfully
        """
        self._webhook_callbacks[job_id] = callback
        logger.info(f"Registered webhook callback for job {job_id}")
        return True

    def unregister_webhook(self, job_id: str) -> bool:
        """
        Unregister a webhook callback.

        Args:
            job_id: Job request ID

        Returns:
            True if unregistered successfully
        """
        if job_id in self._webhook_callbacks:
            del self._webhook_callbacks[job_id]
            logger.info(f"Unregistered webhook callback for job {job_id}")
            return True
        return False

    async def handle_webhook(
        self, job_id: str, status: JobStatus, response_url: Optional[str] = None
    ) -> bool:
        """
        Handle incoming webhook notification.

        Args:
            job_id: Job request ID
            status: Job status
            response_url: Response URL if job completed

        Returns:
            True if webhook was handled
        """
        if job_id not in self._webhook_callbacks:
            logger.debug(f"No webhook callback registered for job {job_id}")
            return False

        callback = self._webhook_callbacks[job_id]

        try:
            status_data = {"request_id": job_id, "status": status}

            result = None
            if status == JobStatus.COMPLETED and response_url:
                result = await self.client.get_result(response_url)

            await callback(status_data, result)
            logger.info(f"Webhook callback executed for job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Webhook callback error for job {job_id}: {e}")
            return False
