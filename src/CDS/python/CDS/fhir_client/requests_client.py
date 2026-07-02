"""RequestsFhirClient — FHIR client implementation backed by requests."""

from typing import Any, Optional

import requests


class RequestsFhirClient:
    """Stateless FHIR read client using requests.

    Suitable for any environment where requests is available (dev, Docker,
    non-IRIS deployments). Replace with IrisFhirClient when running inside
    a full IRIS production that provides a native FHIR outbound adapter.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def read(
        self,
        fhir_server: str,
        resource_type: str,
        resource_id: str,
        *,
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {"Accept": "application/fhir+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{fhir_server.rstrip('/')}/{resource_type}/{resource_id}"
        response = requests.get(url, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        return response.json()
