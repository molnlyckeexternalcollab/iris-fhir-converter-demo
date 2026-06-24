"""Business Operation — FHIR outbound adapter.

Responsible for making authenticated FHIR read requests on behalf of a BP
when the required resources are absent from the CDS Hooks prefetch payload.

The actual HTTP transport is delegated to a FhirClient implementation so that
the client can be swapped (e.g. HttpxFhirClient → IrisFhirClient) without
changing this class or any of the BPs above it.
"""

from iop import BusinessOperation

from CDS.fhir_client.base import FhirClient
from CDS.fhir_client.requests_client import RequestsFhirClient
from CDS.interop.msg.cds_hooks import FhirReadRequest, FhirReadResponse


class Fhir(BusinessOperation):
    def on_init(self) -> None:
        # Swap HttpxFhirClient for IrisFhirClient here when ready.
        self._client: FhirClient = RequestsFhirClient()

    def on_fhir_read_request_message(
        self, request: FhirReadRequest
    ) -> FhirReadResponse:
        resource = self._client.read(
            request.fhir_server,
            request.resource_type,
            request.resource_id,
            token=request.token,
        )
        return FhirReadResponse(resource=resource)
