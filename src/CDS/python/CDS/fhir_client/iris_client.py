"""IrisFhirClient — FHIR client implementation backed by the IRIS native adapter.

TODO: implement using IRIS EnsLib.HealthShare.FHIRClient or equivalent iop
outbound adapter when available.

This stub satisfies the FhirClient protocol so that BO.Fhir can be
instantiated with it without code changes once the implementation is ready.
"""

from typing import Any, Optional


class IrisFhirClient:
    def read(
        self,
        fhir_server: str,
        resource_type: str,
        resource_id: str,
        *,
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        raise NotImplementedError("IrisFhirClient is not yet implemented")
