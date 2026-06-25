"""Hook-specific context and input models shared across the router and interop layers.

Kept in a dedicated module to avoid circular imports between routers/ and interop/.
"""

from typing import Optional

from pydantic import Field

from .cds_hooks_models import CdsHookRequest, HookContext


class PatientViewContext(HookContext):
    """Context for the ``patient-view`` hook.

    See: <a href="https://build.fhir.org/ig/HL7/cds-hooks-library/en/patient-view.html">patient-view hook spec</a>
    """
    userId: str = Field(
        description="The id of the current user in [ResourceType]/[id] format. "
                    "For this hook, expected to be Practitioner, PractitionerRole, Patient, or RelatedPerson. "
                    "For example: Practitioner/abc or Patient/123.",
    )
    patientId: str = Field(
        description="The FHIR Patient.id of the current patient in context.",
    )
    encounterId: Optional[str] = Field(
        default=None,
        description="The FHIR Encounter.id of the current encounter in context. OPTIONAL.",
    )


class PatientViewHookInput(CdsHookRequest):
    """CDS Hooks request body for the ``patient-view`` hook.

    Vendor-neutral: accepts requests from any CDS client (Epic, Cerner, etc.).
    Epic vendor extensions, if present, can be accessed via
    ``get_epic_extensions(body)`` inside the handler.
    """
    context: PatientViewContext  # type: ignore[assignment]


class OrderSelectContext(HookContext):
    """Context for the ``order-select`` hook."""
    userId: str = Field(description="The id of the current user.")
    patientId: str = Field(description="The FHIR Patient.id of the current patient.")
    encounterId: Optional[str] = Field(default=None, description="The FHIR Encounter.id. OPTIONAL.")
    selections: list[str] = Field(description="The FHIR ids of the newly selected orders.")
    draftOrders: dict = Field(description="FHIR Bundle of draft orders.")


class OrderSelectHookInput(CdsHookRequest):
    """CDS Hooks request body for the ``order-select`` hook."""
    context: OrderSelectContext  # type: ignore[assignment]


class OrderSignContext(HookContext):
    """Context for the ``order-sign`` hook."""
    userId: str = Field(description="The id of the current user.")
    patientId: str = Field(description="The FHIR Patient.id of the current patient.")
    encounterId: Optional[str] = Field(default=None, description="The FHIR Encounter.id. OPTIONAL.")
    draftOrders: dict = Field(description="FHIR Bundle of draft orders.")


class OrderSignHookInput(CdsHookRequest):
    """CDS Hooks request body for the ``order-sign`` hook."""
    context: OrderSignContext  # type: ignore[assignment]
