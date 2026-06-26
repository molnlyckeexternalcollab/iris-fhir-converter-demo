"""Shared Pydantic models, constants, and helpers for CDS Hooks endpoints."""

import logging
import os
from typing import Any, Literal, Optional
from urllib.parse import urlencode, urlparse, urlunparse

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MOLNLYCKE_ICON = (
    "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmci"
    "IHdpZHRoPSI5MiIgaGVpZ2h0PSI0NCIgZmlsbD0ibm9uZSIgY2xhc3M9ImxvZ28iPjwvc3ZnPg=="
)

_MOLNLYCKE_SOURCE = {
    "label": "Mölnlycke Health Care",
    "url": "https://www.molnlycke.com/en-us",
    "icon": _MOLNLYCKE_ICON,
}

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class HookContext(BaseModel):
    """Base class for hook-specific context data.

    Each hook defines its own context fields. This base class accepts any
    additional fields (``extra='allow'``) so that hook-specific subclasses
    and unknown future hooks are not rejected at deserialization.

    See: <a href="https://cds-hooks.hl7.org/#hooks">CDS Hooks — Hooks</a>
    """
    model_config = ConfigDict(extra="allow")

    userId: Optional[str] = Field(
        default=None,
        description="The id of the current user in [ResourceType]/[id] format "
                    "(e.g. Practitioner/abc). Present on most standard hooks.",
    )


class FhirAuthorization(BaseModel):
    """A structure holding an OAuth 2.0 bearer access token granting the CDS Service access to FHIR resources.

    See: <a href="https://cds-hooks.hl7.org/#fhir-resource-access">FHIR Resource Access</a>
    """
    access_token: str = Field(description="This is the <a href='https://oauth.net/2/'>OAuth 2.0</a> access token that provides access to the FHIR server.")
    token_type: Literal["Bearer"] = Field(default="Bearer", description="Fixed value: Bearer.")
    expires_in: int = Field(description="The lifetime in seconds of the access token.")
    scope: str = Field(description="The scopes the access token grants the CDS Service.")
    subject: str = Field(description="The <a href='https://oauth.net/2/'>OAuth 2.0</a> client identifier of the CDS Service, as registered with the CDS Client's authorization server.")
    patient: Optional[str] = Field(default=None, description="If the granted SMART scopes include patient scopes (i.e. \"patient/\"), the access token is restricted to a specific patient. This field SHOULD be populated to identify the FHIR id of that patient.")


class PatientName(BaseModel):
    given: Optional[list[str]] = None
    family: Optional[str] = None


class PatientPrefetch(BaseModel):
    name: Optional[list[PatientName]] = None
    birthDate: Optional[str] = None


class PrefetchData(BaseModel):
    patient: Optional[PatientPrefetch] = None


class CdsHookRequest(BaseModel):
    """The request body POSTed by a CDS Client to invoke a CDS Service.

    See: <a href="https://cds-hooks.hl7.org/#http-request-1">CDS Hooks HTTP Request</a>
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "hookInstance": "d1577c69-dfbe-44ad-ba6d-3e05e953b2ea",
                "fhirServer": "http://hooks.smarthealthit.org:9080",
                "hook": "patient-view",
                "fhirAuthorization": {
                    "access_token": "some-opaque-fhir-access-token",
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "scope": "user/Patient.read user/Observation.read",
                    "subject": "cds-service4",
                },
                "context": {
                    "userId": "Practitioner/example",
                    "patientId": "1288992",
                    "encounterId": "89284",
                },
                "prefetch": {
                    "patient": {
                        "resourceType": "Patient",
                        "gender": "male",
                        "birthDate": "1925-12-23",
                        "id": "1288992",
                        "active": True,
                    }
                },
            }
        ]
    })

    hook: str = Field(description="The hook that triggered this CDS Service call. See <a href='https://cds-hooks.hl7.org/#hooks'>CDS Hooks</a>.")
    hookInstance: str = Field(description="A universally unique identifier (UUID) for this particular hook call (see more information below).")
    fhirServer: Optional[str] = Field(default=None, description="The base URL of the CDS Client's <a href='https://www.hl7.org/fhir/'>FHIR</a> server. If fhirAuthorization is provided, this field is REQUIRED. The scheme MUST be https when production data is exchanged.")
    fhirAuthorization: Optional[FhirAuthorization] = Field(default=None, description="A structure holding an <a href='https://oauth.net/2/'>OAuth 2.0</a> bearer access token granting the CDS Service access to FHIR resources, along with supplemental information relating to the token. See the <a href='https://cds-hooks.hl7.org/#fhir-resource-access'>FHIR Resource Access</a> section for more information.")
    context: HookContext = Field(description="Hook-specific contextual data that the CDS service will need. For example, with the patient-view hook this will include the FHIR id of the <a href='https://www.hl7.org/fhir/patient.html'>Patient</a> being viewed. For details, see the Hooks specific specification page (example: <a href='https://build.fhir.org/ig/HL7/cds-hooks-library/patient-view.html'>patient-view</a>).")
    prefetch: Optional[PrefetchData] = Field(default=None, description="The FHIR data that was prefetched by the CDS Client.")
    extension: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional vendor-specific extensions. The CDS Hooks specification reserves this key "
                    "and requires that extension names use reverse-domain-name notation "
                    "(e.g. com.example.my-extension). "
                    "See: <a href='https://cds-hooks.hl7.org/#extensions'>CDS Hooks Extensions</a>.",
    )

    @model_validator(mode="after")
    def fhir_server_required_with_authorization(self) -> "CdsHookRequest":
        """Per CDS Hooks spec: fhirServer is REQUIRED when fhirAuthorization is provided."""
        if self.fhirAuthorization is not None and self.fhirServer is None:
            raise ValueError(
                "fhirServer is required when fhirAuthorization is provided "
                "(spec: https://cds-hooks.hl7.org/#http-request-1)."
            )
        return self


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class Coding(BaseModel):
    """The Coding data type captures the concept of a code.

    A code is understood only when the given code, code-system, and a optionally a human readable display are available.
    his coding type is a standalone data type in CDS Hooks modeled after a trimmed down version of the <a href="http://hl7.org/fhir/datatypes.html#Coding">FHIR Coding data type</a>.
    See: <a href="https://cds-hooks.hl7.org/#coding">CDS Hooks Coding</a>
    """
    code: str = Field(description="The code for what is being represented.")
    system: str = Field(description="The codesystem for this code.")
    display: Optional[str] = Field(description="A short, human-readable label to display. REQUIRED for <a href='https://cds-hooks.hl7.org/#overridereason'>Override Reasons</a> provided by the CDS Service, OPTIONAL for <a href='https://cds-hooks.hl7.org/#source'>Topic.</a>")


class CdsSource(BaseModel):
    """The source of information displayed on a card.

    See: <a href="https://cds-hooks.hl7.org/#source">CDS Hooks Source</a>
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "label": "Zika Virus Management",
                "url": "https://example.com/cdc-zika-virus-mgmt",
                "icon": "https://example.com/cdc-zika-virus-mgmt/100.png",
                "topic": {
                    "system": "http://example.org/cds-services/fhir/CodeSystem/topics",
                    "code": "12345",
                    "display": "Mosquito born virus",
                },
            }
        ]
    })

    label: str = Field(description="A short, human-readable label to display for the source of the information displayed on this card. If a url is also specified, this MAY be the text for the hyperlink.")
    url: Optional[str] = Field(default=None, description="An optional absolute URL to load (via GET, in a browser context) when a user clicks on this link to learn more about the organization or data set that provided the information on this card. Note that this URL should not be used to supply a context-specific \"drill-down\" view of the information on this card. For that, use card.link.url instead.")
    icon: Optional[str] = Field(default=None, description="An absolute URL to an icon for the source of this card. The icon returned by this URL SHOULD be a 100x100 pixel PNG image without any transparent regions. The CDS Client may ignore or scale the image during display as appropriate for user experience.")
    topic: Optional[Coding] = Field(default=None, description="A topic describes the content of the card by providing a high-level categorization that can be useful for filtering, searching or ordered display of related cards in the CDS client's UI. This specification does not prescribe a standard set of topics.")


class CdsAction(BaseModel):
    """An action proposed inside a suggestion.

    See: <a href="https://cds-hooks.hl7.org/#action">CDS Hooks Action</a>
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "type": "create",
                "description": "Create a prescription for Acetaminophen 250 MG",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "medrx001",
                    "...": "<snipped for brevity>"
                }
            },
            {
                "type": "update",
                "description": "Update the order to record the appropriateness score",
                "resource": {
                    "resourceType": "ServiceRequest",
                    "id": "procedure-request-1",
                    "...": "<snipped for brevity>"
                }
            },
            {
                "type": "delete",
                "description": "Remove the inappropriate order",
                "resourceId": "ServiceRequest/procedure-request-1"
            }
        ]
    })

    type: Literal["create", "update", "delete"] = Field(description=("HL7: The type of action being performed. Allowed values are: create, update, delete."
                                                                    "Epic: For a given resource, confirm the action types supported in the <a href='https://fhir.epic.com/Sandbox'>API Library</a>."))
    description: str = Field(description=("HL7: Human-readable description of the suggested action MAY be presented to the end-user."
                                           "Epic: This value is the primary content of the OPA. A CDS Service may return content as plain text."))
    resource: Optional[Any] = Field(default=None,
                                    description=("HL7: A FHIR resource. When the type attribute is create, the resource attribute SHALL contain a new FHIR resource to be created. For update, this holds the updated resource in its entirety and not just the changed fields. Use of this field to communicate a string of a FHIR id for delete suggestions is DEPRECATED and resourceId SHOULD be used instead."
                                                 "Epic: The FHIR resource provided by the CDS Service representing the action to be suggested to the user. Check the <a href='https://fhir.epic.com/Sandbox'>API Library</a> to see what resources (and action types) are supported."))
    resourceId: Optional[str] = Field(default=None, description="A relative reference to the relevant resource. SHOULD be provided when the type attribute is delete.")

    @model_validator(mode="after")
    def validate_resource_fields(self) -> "CdsAction":
        """Enforce CDS Hooks spec resource/resourceId rules per action type."""
        if self.type in ("create", "update") and self.resource is None:
            raise ValueError(
                f"resource is required when type is '{self.type}' "
                "(spec: https://cds-hooks.hl7.org/#action)."
            )
        if self.type == "delete":
            if self.resourceId is None and self.resource is None:
                raise ValueError(
                    "resourceId must be provided when type is 'delete' "
                    "(spec: https://cds-hooks.hl7.org/#action)."
                )
            if self.resource is not None and self.resourceId is None:
                raise ValueError(
                    "Use resourceId (not resource) when type is 'delete' — "
                    "passing resource for delete is deprecated "
                    "(spec: https://cds-hooks.hl7.org/#action)."
                )
        return self


class CdsSuggestion(BaseModel):
    """A suggested action set that can be accepted by the clinician.

    See: <a href="https://cds-hooks.hl7.org/#suggestion">CDS Hooks Suggestion</a>
    """
    label: str = Field(description=("HL7: Human-readable label to display for this suggestion (e.g. the CDS Client might render this as the text on a button tied to this suggestion)."
                                     "Epic: This field is not used, but is required."))
    uuid: Optional[str] = Field(default=None, description=("HL7: Unique identifier, used for auditing and logging suggestions."
                                                           "Epic: This field is optional. However, it is required if you intend to receive feedback."))
    isRecommended: Optional[bool] = Field(default=None, description=("HL7: When there are multiple suggestions, allows a service to indicate that a specific suggestion is recommended from all the available suggestions on the card. CDS Hooks clients may choose to influence their UI based on this value, such as pre-selecting, or highlighting recommended suggestions. Multiple suggestions MAY be recommended, if card.selectionBehavior is any."
                                                                     "Epic: In Epic, this is used to control whether the suggested action is pre-selected or not."))
    actions: Optional[list[CdsAction]] = Field(default=None, description=("HL7: Array of objects, each defining a suggested action. Within a suggestion, all actions are logically AND'd together, such that a user selecting a suggestion selects all of the actions within it. When a suggestion contains multiple actions, the actions SHOULD be processed as per FHIR's rules for processing transactions with the CDS Client's fhirServer as the base url for the inferred full URL of the transaction bundle entries. (Specifically, deletes happen first, then creates, then updates)."
                                                                          "Epic: Epic only supports a single action per suggestion."))


class CdsLink(BaseModel):
    """A link to an external resource or a SMART app launch URL.

    See: <a href="https://cds-hooks.hl7.org/#link">CDS Hooks Link</a>
    """
    label: str = Field(description="Human-readable label to display for this link (e.g. the CDS Client might render this as the underlined text of a clickable link).")
    url: str = Field(description="URL to load (via GET, in a browser context) when a user clicks on this link. Note that this MAY be a 'deep link' with context embedded in path segments, query parameters, or a hash.")
    type: Literal["absolute", "smart"] = Field(description="The type of the given URL. There are two possible values for this field. A type of absolute indicates that the URL is absolute and should be treated as-is. A type of smart indicates that the URL is a SMART app launch URL and the CDS Client should ensure the SMART app launch URL is populated with the appropriate SMART launch parameters.")
    appContext: Optional[str] = Field(default=None, description="An optional field that allows the CDS Service to share information from the CDS card with a subsequently launched SMART app. The appContext field should only be valued if the link type is smart and is not valid for absolute links. The appContext field and value will be sent to the SMART app as part of the OAuth 2.0 access token response, alongside the other SMART launch parameters when the SMART app is launched. Note that appContext could be escaped JSON, base64 encoded XML, or even a simple string, so long as the SMART app can recognize it. CDS Client support for appContext requires additional coordination with the authorization server that is not described or specified in CDS Hooks nor SMART.")
    autolaunchable: Optional[bool] = Field(default=None, description="This field serves as a hint to the CDS Client suggesting this link be immediately launched, without displaying the card and without manual user interaction. Note that CDS Hooks cards which contain links with this field set to true, may not be shown to the user. Sufficiently advanced CDS Clients may support automatically launching multiple links or multiple cards. Implementer guidance is requested to determine if the specification should preclude these advanced scenarios.")


class CdsCard(BaseModel):
    """A card returned by a CDS Service.

    See: <a href="https://cds-hooks.hl7.org/#card-attributes">CDS Hooks Card Attributes</a>
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "summary": "Example Card",
                "indicator": "info",
                "source": {
                    "label": "Static CDS Service Example",
                    "url": "https://example.com",
                    "icon": "https://example.com/img/icon-100px.png",
                },
                "links": [
                    {
                        "label": "SMART Example App",
                        "url": "https://smart.example.com/launch",
                        "type": "smart",
                    },
                    {
                        "label": "An Absolute Link",
                        "url": "https://example.com",
                        "type": "absolute",
                    },
                ],
            }
        ]
    })

    uuid: Optional[str] = Field(default=None,
                                description=("HL7:Unique identifier of the card. MAY be used for auditing and logging cards and SHALL be included in any subsequent calls to the CDS service's feedback endpoint."
                                             "Epic: Unique identifier, used for auditing and logging suggestions. This field is optional. However, it is required if you intend to receive feedback."))
    summary: str = Field(max_length=140, description="One-sentence, <140-character summary message for display to the user inside of this card.")
    detail: Optional[str] = Field(default=None,
                                  description=("HL7: Optional detailed information to display; if provided MUST be represented in <a href='https://github.github.com/gfm/'>(GitHub Flavored) Markdown</a>. (For non-urgent cards, the CDS Client MAY hide these details until the user clicks a link like 'view more details…')."
                                               "Epic: A CDS Service may return content as mere plain text, as GitHub flavored markdown, or, with an Epic-specific extension, as html. (See \"com.epic.cdshooks.card.detail.content-type\" extension, below)."))
    indicator: Literal["info", "warning", "critical"] = Field(default='info',
                                                              description=("HL7: Urgency/importance of what this card conveys. Allowed values, in order of increasing urgency, are: info, warning, critical. The CDS Client MAY use this field to help make UI display decisions such as sort order or coloring."
                                                                           "Epic: The info, warning, and critical values can be mapped to Epic-specific values by the Epic application team for display."))
    source: CdsSource = Field(description=("HL7: Grouping structure for the Source of the information displayed on this card. The source should be the primary source of guidance for the decision support the card represents. "
                                           "Epic: Epic only supports alpha-numeric strings as the code of source.topic, for example: \"Card123\" or \"869e7c5587e04d0da96a60a84b5b8eac\". The value returned in source.topic.code is used for logging and auditing, and is returned to the CDS Service in the feedback request. **Maximum Length: 100 Characters**. Source.topic.code should be a static identifier representing the particular topic of a card. When an end user overrides a given card, their acknowledgment is associated with this identifier. If you want the end user's override to be respected on subsequent requests to your CDS service, the topic identifier should remain static if sending the same card content."))
    suggestions: Optional[list[CdsSuggestion]] = Field(default=None, description="Allows a service to suggest a set of changes in the context of the current activity (e.g. changing the dose of a medication currently being prescribed, for the order-sign activity). If suggestions are present, selectionBehavior MUST also be provided.")
    selectionBehavior: Optional[Literal["at-most-one", "any"]] = Field(default=None,
                                                                       description=("HL7: Describes the intended selection behavior of the suggestions in the card. Allowed values are: at-most-one, indicating that the user may choose none or at most one of the suggestions; any, indicating that the end user may choose any number of suggestions including none of them and all of them. CDS Clients that do not understand the value MUST treat the card as an error. REQUIRED when suggestions are present."
                                                                                    "Epic: Only the value \"any\" is currently supported."))
    overrideReasons: Optional[list[Coding]] = Field(default=None, description="Override reasons can be selected by the end user when overriding a card without taking the suggested recommendations. The CDS service MAY return a list of override reasons to the CDS client. If override reasons are present, the CDS Service MUST populate a display value for each reason's Coding. The CDS Client SHOULD present these reasons to the clinician when they dismiss a card. A CDS Client MAY augment the override reasons presented to the user with its own reasons.")
    links: Optional[list[CdsLink]] = Field(default=None,
                                           description=("HL7: Allows a service to suggest a link to an app that the user might want to run for additional information or to help guide a decision."
                                                        "Epic: Allows your service to suggest a link to a user for additional information or a SMART app. Allowed links are allow-listed by the health system."))

    @model_validator(mode="after")
    def validate_card_constraints(self) -> "CdsCard":
        """Enforce CDS Hooks spec and Epic-specific card constraints."""
        # HL7: selectionBehavior is REQUIRED when suggestions are present.
        if self.suggestions and self.selectionBehavior is None:
            raise ValueError(
                "selectionBehavior is required when suggestions are present "
                '(spec: https://cds-hooks.hl7.org/#card-attributes). '
                'Use "at-most-one" or "any".'
            )
        # Epic: source.topic.code must be alphanumeric and ≤ 100 characters.
        if self.source.topic is not None:
            code = self.source.topic.code
            if len(code) > 100:
                raise ValueError(
                    "source.topic.code must be at most 100 characters (Epic constraint)."
                )
            if not re.fullmatch(r"[A-Za-z0-9]+", code):
                raise ValueError(
                    f"source.topic.code must be alphanumeric only (Epic constraint): got {code!r}."
                )
        return self


class CdsHookResponse(BaseModel):
    """Response returned by a CDS Service after a hook invocation.

    See: <a href="https://cds-hooks.hl7.org/#cds-service-response">CDS Hooks Response</a>
    """
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "cards": [
                    {
                        "summary": "Example Card",
                        "indicator": "info",
                        "source": {
                            "label": "Static CDS Service Example",
                            "url": "https://example.com",
                            "icon": "https://example.com/img/icon-100px.png",
                        },
                        "links": [
                            {
                                "label": "SMART Example App",
                                "url": "https://smart.example.com/launch",
                                "type": "smart",
                            },
                            {
                                "label": "An Absolute Link",
                                "url": "https://example.com",
                                "type": "absolute",
                            },
                        ],
                    }
                ]
            }
        ]
    })

    cards: list[CdsCard]
    systemActions: Optional[list[CdsAction]] = None


# ---------------------------------------------------------------------------
# Feedback models
# ---------------------------------------------------------------------------


class AcceptedSuggestion(BaseModel):
    id: str


class OverrideReason(BaseModel):
    reason: Optional[Coding] = None
    userComment: Optional[str] = None


class FeedbackItem(BaseModel):
    card: str
    outcome: Literal["accepted", "overridden"]
    outcomeTimestamp: str
    acceptedSuggestions: Optional[list[AcceptedSuggestion]] = None
    overrideReason: Optional[OverrideReason] = None


class FeedbackRequest(BaseModel):
    feedback: list[FeedbackItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_smart_launch_url(fhir_server: Optional[str], patient_id: str) -> str:
    """Build the SMART app launch URL, appending iss and launch query params."""
    origin = os.environ.get("SMART_APP_ORIGIN", "http://localhost:3001")
    base = f"{origin}/launch"
    params: dict[str, str] = {"launch": f"demo-{patient_id}"}
    if fhir_server:
        params["iss"] = fhir_server
    query = urlencode(params)
    parsed = urlparse(base)
    return urlunparse(parsed._replace(query=query))


def log_feedback(hook_id: str, feedback: list[FeedbackItem]) -> None:
    """Log clinician feedback details."""
    separator = "=" * 60
    logger.info("%s", separator)
    logger.info("FEEDBACK RECEIVED — %s", hook_id)
    logger.info("%s", separator)
    for i, item in enumerate(feedback, start=1):
        outcome_marker = "ACCEPTED" if item.outcome == "accepted" else "OVERRIDDEN"
        logger.info("Feedback #%d | card=%s | outcome=%s | ts=%s",
                    i, item.card, outcome_marker, item.outcomeTimestamp)
        if item.acceptedSuggestions:
            for s in item.acceptedSuggestions:
                logger.info("  accepted suggestion id=%s", s.id)
        if item.overrideReason:
            r = item.overrideReason
            if r.reason:
                logger.info("  override reason: code=%s system=%s display=%s",
                            r.reason.code, r.reason.system, r.reason.display)
            if r.userComment:
                logger.info("  user comment: %s", r.userComment)
    logger.info("%s", separator)
