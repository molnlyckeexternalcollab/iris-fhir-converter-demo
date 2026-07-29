"""Business Service — FHIR file import scheduler.

Owns scheduling and manual triggering only. Source acquisition and FHIR
submission are delegated to FHIRDataLoaderOperation via the Output target.

Scheduling
----------
Controlled by the inherited ``call_interval`` setting (seconds between polls).
Set it in the production UI under "CallInterval".

Manual trigger
--------------
Send a ``FHIRImportRequest`` message to this service from the production UI
(right-click → Test, or via Director) to trigger an immediate run outside the
normal schedule. The message is forwarded to the operation unchanged.
"""

from iop import PollingBusinessService, target

from EAI.msg import FHIRDataLoaderRequest


class FHIRDataLoaderService(PollingBusinessService):
    """Polls on a schedule and forwards import triggers to FHIRDataLoaderOperation."""

    Output = target("BO.FHIRDataLoader")
    """Route to the operation that calls SubmitResourceFiles."""

    def on_poll(self) -> None:
        """Called by the adapter on each scheduled tick."""
        self.send_request_sync(self.Output, FHIRDataLoaderRequest(reason="scheduled"))

    def on_message(self, request: FHIRDataLoaderRequest) -> None:
        """Called when a FHIRImportRequest is sent manually from the production UI."""
        self.send_request_sync(self.Output, request)


