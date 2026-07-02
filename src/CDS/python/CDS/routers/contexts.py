"""Hook-specific context and input models shared across the router and interop layers.

Kept in a dedicated module to avoid circular imports between routers/ and interop/.
"""

from typing import Optional

from pydantic import ConfigDict, Field

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
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "hookInstance": "a3b4c5d6-e7f8-11ea-bf16-460231621f93",
                "fhirServer": "https://example.com/interconnect-instance-oauth/api/FHIR/R4",
                "hook": "order-select",
                "context": {
                    "userId": "PractitionerRole/e-QokEGUJIzyynNdkCFrs9w3",
                    "patientId": "eXoGxqgBaJuNkuahMYmiDhg3",
                    "encounterId": "eFyoeOuWgXtlQmOQzPdkQWwy3s8a49yrUc-LtjwhWT6g3",
                    "selections": ["MedicationRequest/order-dressing-001"],
                    "draftOrders": {
                        "resourceType": "Bundle",
                        "type": "collection",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "MedicationRequest",
                                    "id": "order-dressing-001",
                                    "status": "draft",
                                    "intent": "order",
                                    "priority": "routine",
                                    "medicationReference": {
                                        "reference": "Medication/med-ibuprofen-001",
                                        "display": "IBUPROFEN 200 MG PO TABS",
                                    },
                                    "subject": {"reference": "Patient/eXoGxqgBaJuNkuahMYmiDhg3"},
                                }
                            },
                            {
                                "resource": {
                                    "resourceType": "Medication",
                                    "id": "med-ibuprofen-001",
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                                "code": "5640",
                                                "display": "Ibuprofen",
                                            }
                                        ],
                                        "text": "Ibuprofen 200 MG Oral Tablet",
                                    },
                                }
                            },
                        ],
                    },
                },
            }
        ]
    })
    context: OrderSelectContext  # type: ignore[assignment]


class OrderSignContext(HookContext):
    """Context for the ``order-sign`` hook."""
    userId: str = Field(description="The id of the current user.")
    patientId: str = Field(description="The FHIR Patient.id of the current patient.")
    encounterId: Optional[str] = Field(default=None, description="The FHIR Encounter.id. OPTIONAL.")
    draftOrders: dict = Field(description="FHIR Bundle of draft orders.")


class OrderSignHookInput(CdsHookRequest):
    """CDS Hooks request body for the ``order-sign`` hook."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "hookInstance": "b1c2d3e4-f5a6-11ea-bf16-460231621f93",
                "fhirServer": "https://example.com/interconnect-instance-oauth/api/FHIR/R4",
                "hook": "order-sign",
                "context": {
                    "userId": "PractitionerRole/e-QokEGUJIzyynNdkCFrs9w3",
                    "patientId": "eXoGxqgBaJuNkuahMYmiDhg3",
                    "encounterId": "eFyoeOuWgXtlQmOQzPdkQWwy3s8a49yrUc-LtjwhWT6g3",
                    "draftOrders": {
                        "resourceType": "Bundle",
                        "type": "collection",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "MedicationRequest",
                                    "id": "order-ibuprofen-001",
                                    "status": "draft",
                                    "intent": "order",
                                    "priority": "routine",
                                    "medicationReference": {
                                        "reference": "Medication/med-ibuprofen-001",
                                        "display": "IBUPROFEN 200 MG PO TABS",
                                    },
                                    "subject": {"reference": "Patient/eXoGxqgBaJuNkuahMYmiDhg3"},
                                }
                            },
                            {
                                "resource": {
                                    "resourceType": "Medication",
                                    "id": "med-ibuprofen-001",
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                                "code": "5640",
                                                "display": "Ibuprofen",
                                            }
                                        ],
                                        "text": "Ibuprofen 200 MG Oral Tablet",
                                    },
                                }
                            },
                            {
                                "resource": {
                                    "resourceType": "ServiceRequest",
                                    "id": "order-wound-care-001",
                                    "status": "draft",
                                    "intent": "order",
                                    "priority": "routine",
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://snomed.info/sct",
                                                "code": "182531007",
                                                "display": "Dressing of wound",
                                            }
                                        ],
                                        "text": "Wound dressing change",
                                    },
                                    "subject": {"reference": "Patient/eXoGxqgBaJuNkuahMYmiDhg3"},
                                }
                            },
                        ],
                    },
                },
            }
        ]
    })
    context: OrderSignContext  # type: ignore[assignment]
