"""Epic-specific CDS Hooks extensions and typed request models.

Epic sends vendor extensions under the top-level ``extension`` field of a CDS
Hooks request, using reverse-domain-name keys as required by the CDS Hooks spec
(§1.12). Because those key names contain dots and hyphens they cannot be used as
Python identifiers directly — Pydantic ``Field(alias=...)`` is used instead.

Reference: https://fhir.epic.com/Documentation?docId=cds-hooks (Epic Extensions section)
"""

from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .cds_hooks_models import CdsHookRequest

_EPIC_KEY_PREFIX = "com.epic."


class EpicBpaTriggerAction(IntEnum):
    """Known values for Epic's ``com.epic.cdshooks.request.bpa-trigger-action`` extension.

    Each member carries a human-readable ``label`` alongside its integer value::

        str(EpicBpaTriggerAction.OPEN_PATIENT_CHART)  # "Open patient chart (60)"
        EpicBpaTriggerAction.OPEN_PATIENT_CHART.label  # "Open patient chart"
        int(EpicBpaTriggerAction.OPEN_PATIENT_CHART)   # 60

    Reference: https://fhir.epic.com/Documentation?docId=cds-hooks
    """

    def __new__(cls, value: int, label: str = "") -> "EpicBpaTriggerAction":
        """Trick for attaching extra data.

        This trick is the standard Python enum pattern for attaching extra data — the integer ``_value_`` is set first
        (so IntEnum machinery works), then label is stored as a plain instance attribute.

            t = EpicBpaTriggerAction.OPEN_PATIENT_CHART

            str(t)   # "Open patient chart (60)"
            t.label  # "Open patient chart"
            t.name   # "OPEN_PATIENT_CHART"
            int(t)   # 60
            t == 60  # True
        """
        obj = int.__new__(cls, value)
        obj._value_ = value # consumed by the Enum metaclass machinery
        obj.label = label
        return obj

    GENERAL_OPA        = (5,  "General OPA section")
    ENTER_PROBLEM      = (6,  "Enter problem")
    ENTER_DIAGNOSIS    = (7,  "Enter diagnosis")
    ENTER_ORDER        = (18, "Enter order")
    SIGN_ORDERS        = (23, "Sign orders")
    IP_ADMISSION_OPA   = (26, "IP Admission OPA section")
    IP_DISCHARGE_OPA   = (27, "IP Discharge OPA section")
    IP_TRANSFER_OPA    = (29, "IP Transfer OPA section")
    OPEN_PATIENT_CHART = (60, "Open patient chart")

    def __str__(self) -> str:
        return f"{self.label} ({self.value})"


class EpicExtensions(BaseModel):
    """Typed model for Epic's CDS Hooks request extensions.

    All fields are ``Optional`` because Epic does not guarantee that every
    extension is present on every request. Use ``model_config.extra = "allow"``
    so that unknown or future Epic extension keys are accepted without error.

    Reference: https://fhir.epic.com/Documentation?docId=cds-hooks
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    bpa_trigger_action: Optional[EpicBpaTriggerAction] = Field(
        default=None,
        alias="com.epic.cdshooks.request.bpa-trigger-action",
        description=(
            "The specific trigger action in Epic that is mapped to the hook. "
            "See ``EpicBpaTriggerAction`` for known values."
        ),
    )
    cds_hooks_specification_version: Optional[str] = Field(
        default=None,
        alias="com.epic.cdshooks.request.cds-hooks-specification-version",
        description="The CDS Hooks specification version used by Epic.",
    )
    fhir_version: Optional[str] = Field(
        default=None,
        alias="com.epic.cdshooks.request.fhir-version",
        description="The primary FHIR version of the CDS service as specified during OAuth registration.",
    )
    criteria_id: Optional[str] = Field(
        default=None,
        alias="com.epic.cdshooks.request.criteria-id",
        description="The ID of the OPA criteria record in Epic. Useful during troubleshooting.",
    )
    epic_version: Optional[str] = Field(
        default=None,
        alias="com.epic.cdshooks.request.epic-version",
        description="The version of Epic that the health system is currently using.",
    )
    cds_hooks_implementation_version: Optional[str] = Field(
        default=None,
        alias="com.epic.cdshooks.request.cds-hooks-implementation-version",
        description=(
            "The internal version Epic assigns to CDS Hooks implementations. "
            "Can be used to determine what features are supported."
        ),
    )


class EpicCdsHookRequest(CdsHookRequest):
    """``CdsHookRequest`` with the ``extension`` field narrowed to ``EpicExtensions``.

    Use this as the body type on endpoints that are known to be called by Epic,
    to get typed, documented access to Epic's vendor extensions via
    ``body.epic_extensions`` instead of raw dict lookups on ``body.extension``.

    Example::

        @router.post("/patient-view")
        async def patient_view(body: EpicPatientViewRequest):
            trigger = body.epic_extensions and body.epic_extensions.bpa_trigger_action
    """
    extension: Optional[EpicExtensions] = Field(  # type: ignore[assignment]
        default=None,
        description="Epic vendor extensions. See EpicExtensions for typed field access.",
    )

    @property
    def epic_extensions(self) -> Optional[EpicExtensions]:
        """Convenience alias — same as ``self.extension`` but communicates intent."""
        return self.extension


def get_epic_extensions(request: CdsHookRequest) -> Optional[EpicExtensions]:
    """Parse Epic vendor extensions from any ``CdsHookRequest``.

    Safe to call on requests from any CDS client — returns ``None`` if the
    ``extension`` field is absent or contains no Epic-prefixed keys. This lets
    handlers be vendor-neutral while still accessing typed Epic data when present.

    Example::

        epic_ext = get_epic_extensions(body)
        if epic_ext is not None:
            logger.debug("Epic trigger=%s", epic_ext.bpa_trigger_action)
    """
    if not request.extension:
        return None
    if not any(k.startswith(_EPIC_KEY_PREFIX) for k in request.extension):
        return None
    return EpicExtensions.model_validate(request.extension)
