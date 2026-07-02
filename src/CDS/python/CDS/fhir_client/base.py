"""FhirClient protocol — structural interface for FHIR client implementations."""

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class FhirClient(Protocol):
    def read(
        self,
        fhir_server: str,
        resource_type: str,
        resource_id: str,
        *,
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch a single FHIR resource by type and id.

        Args:
            fhir_server:   Base URL of the FHIR server (e.g. https://epic/api/FHIR/R4).
            resource_type: FHIR resource type (e.g. "Patient", "Observation").
            resource_id:   Logical resource id.
            token:         Bearer token for Authorization header, or None.

        Returns:
            Parsed FHIR resource as a dict.

        Raises:
            httpx.HTTPStatusError / equivalent: on non-2xx response.
        """
        ...
