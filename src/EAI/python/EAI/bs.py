"""Business Service — FHIR file import scheduler.

Owns scheduling, live progress logging, and manual triggering only.
Source acquisition and FHIR submission are delegated to FHIRDataLoaderOperation
via the Output target.

Why async dispatch
------------------
SubmitResourceFiles blocks the BO process for the full duration of a bulk
import (potentially many minutes). Using send_request_sync here would block
this service's process too, making it impossible to stop the BS gracefully
and preventing periodic progress logs from being emitted.

send_request_async fires and forgets: the BO receives the trigger in its
queue and the BS remains free to be stopped, restarted, or to emit the next
progress log on the following poll tick. Overlap protection lives in the BO.

Scheduling
----------
Controlled by the inherited ``call_interval`` setting (seconds between polls).
Set it in the production UI under "CallInterval".

Manual trigger
--------------
Send a ``FHIRDataLoaderRequest`` message to this service via Director to
trigger an immediate run outside the normal schedule. The message is
forwarded asynchronously to the operation.
"""

import iris
from iop import PollingBusinessService, target

from EAI.msg import FHIRDataLoaderRequest


class FHIRDataLoaderService(PollingBusinessService):
    """Polls on a schedule, logs live progress, and forwards triggers to FHIRDataLoaderOperation."""

    Output = target("BO.FHIRDataLoader")
    """Route to the operation that calls SubmitResourceFiles."""

    job_id: str = "EAIFHIRImport"
    """
    DataLoader job ID to poll for live progress reporting.
    Must match the job_id setting on FHIRDataLoaderOperation.
    """

    def on_poll(self) -> None:
        """Log live progress if running, otherwise fire the scheduled trigger."""
        status_obj = self._get_dataloader_status()
        if status_obj is not None and status_obj._Get("status") == "Running":
            self._log_dataloader_progress(status_obj)
        else:
            self.send_request_async(self.Output, FHIRDataLoaderRequest(reason="scheduled"))

    def on_message(self, request: FHIRDataLoaderRequest) -> None:
        """Forward a manually sent trigger to the operation without blocking."""
        self.send_request_async(self.Output, request)

    # ------------------------------------------------------------------ helpers

    def _get_dataloader_status(self):
        """Return the DataLoader.Status() DynamicObject, or None on failure."""
        try:
            return iris.cls("HS.FHIRServer.Tools.DataLoader").Status(self.job_id)
        except Exception:
            return None

    def _log_dataloader_progress(self, status_obj) -> None:
        """Emit a progress log entry for a currently running DataLoader job."""
        try:
            self.log_info(
                f"DataLoader '{self.job_id}' in progress — "
                f"files={status_obj._Get('filesTotal')} "
                f"resources={status_obj._Get('resourcesTotal')} "
                f"elapsed={status_obj._Get('elapsedTotal')}s "
                f"errors={status_obj._Get('errorCount')}"
            )
        except Exception:
            pass


