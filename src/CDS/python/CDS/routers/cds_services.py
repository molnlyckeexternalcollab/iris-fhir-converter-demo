from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field, RootModel, ConfigDict

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks"])


class PrefetchTemplate(RootModel[dict[str, str]]):
    """Key/value pairs of FHIR queries for the CDS Client to prefetch on each hook invocation.

    - **key**: string that describes the type of data being requested (e.g. `patient`, `medications`)
    - **value**: string representing the FHIR query (e.g. `Patient/{{context.patientId}}`)

    See: <a href="https://cds-hooks.hl7.org/#prefetch-template">CDS Hooks Prefetch Template</a>
    """


class CdsService(BaseModel):
    """Represents a CDS Service as defined in the CDS Hooks specification.

    See: <a href="https://cds-hooks.hl7.org/#response">CDS Hooks Response</a>
    """

    hook: str = Field(description="The hook this service is invoked on (e.g. 'patient-view').")
    title: Optional[str] = Field(default=None, description="The human-friendly name of this service. RECOMMENDED.")
    description: str = Field(description="The description of this service.")
    id: str = Field(description="The {id} portion of the URL to this service which is available at {baseUrl}/cds-services/{id}")
    prefetch: Optional[PrefetchTemplate] = Field(
        default=None,
        description="An object containing key/value pairs of FHIR queries that this service is requesting the CDS Client to perform and provide on each service call.",
    )
    usageRequirements: Optional[str] = Field(
        default=None,
        description="Human-friendly description of any preconditions for using this service.",
    )


class DiscoveryResponse(BaseModel):
    """Represents the response from the CDS Service discovery endpoint.
    
    List of available CDS Services that the CDS Client can invoke, along with metadata about each service and any requested prefetch data.
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "hook": "patient-view",
                "title": "Static CDS Service Example",
                "description": "An example of a CDS Service that returns a static set of cards",
                "id": "static-patient-greeter",
                "prefetch": {
                    "patientToGreet": "Patient/{{context.patientId}}"
                }
            },
            {
                "hook": "order-select",
                "title": "Order Echo CDS Service",
                "description": "An example of a CDS Service that simply echoes the order(s) being placed",
                "id": "order-echo",
                "prefetch": {
                    "patient": "Patient/{{context.patientId}}",
                    "medications": "MedicationRequest?patient={{context.patientId}}"
                }
            },
            {
                "hook": "order-sign",
                "title": "Pharmacogenomics CDS Service",
                "description": "An example of a more advanced, precision medicine CDS Service",
                "id": "pgx-on-order-sign",
                "usageRequirements": "Note: functionality of this CDS Service is degraded without access to a FHIR Restful API as part of CDS recommendation generation."
            }
        ]
    })
    services: list[CdsService]


# Hardcoded list of available CDS Services returned by the discovery endpoint.
# In the future this could be loaded dynamically (e.g. from a database or config file).
_SERVICES: list[CdsService] = [
    CdsService(
        hook="patient-view",
        title="Static CDS Service Examples",
        description="An example of a CDS Service that returns a static set of cards",
        id="static-patient-greeter",
        prefetch={
            "patientToGreet": "Patient/{{context.patientId}}"
        },
    ),
    CdsService(
        hook="order-select",
        title="Order Echo CDS Service",
        description="An example of a CDS Service that simply echoes the order(s) being placed",
        id="order-echo",
        prefetch={
            "patient": "Patient/{{context.patientId}}",
            "medications": "MedicationRequest?patient={{context.patientId}}"
        },
    ),
    CdsService(
        hook="order-sign",
        title="Pharmacogenomics CDS Service",
        description="An example of a more advanced, precision medicine CDS Service",
        id="pgx-on-order-sign",
        usageRequirements="Note: functionality of this CDS Service is degraded without access to a FHIR Restful API as part of CDS recommendation generation."
    )
]


@router.get("", response_model=DiscoveryResponse)
async def discovery():
    return DiscoveryResponse(services=_SERVICES)
