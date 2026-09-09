"""Pure FHIR Bundle → RiskAssessmentInput extractor for the HAC PI calculator.

This module never fetches anything itself — it only reads resources out of a
Bundle (or single resource) that the caller already has, e.g. a Synthea
patient export, a CDS Hooks prefetch bundle, or an EAI-converted FHIR Bundle.
DSE must not talk to a live FHIR server; see dse.instructions.md.

Field-to-code mapping is documented in
skills/synthea-module-author/references/hapi-labs.md — keep both in sync.
"""

from datetime import date
from typing import Any, Optional

from DSE.models import (
    BradenActivityScore,
    BradenFrictionScore,
    BradenMobilityScore,
    BradenMoistureScore,
    BradenSensoryScore,
    GaitTransferScore,
    RiskAssessmentInput,
)

_SNOMED = "http://snomed.info/sct"
_RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
_GIM_SERVICE_SYSTEM = "http://hapi-dse.local/CodeSystem"

_ALBUMIN_LOINC = "1751-7"
_BUN_LOINC = "3094-0"
_CHLORIDE_LOINC = "2075-0"
_RDW_CV_LOINC = "788-0"

_BRADEN_MOBILITY_LOINC = "38224-2"
_BRADEN_MOISTURE_LOINC = "38229-1"
_BRADEN_ACTIVITY_LOINC = "38223-4"
_BRADEN_FRICTION_LOINC = "38226-7"
_BRADEN_SENSORY_LOINC = "38222-6"
_GAIT_TRANSFER_LOINC = "93015-6"

_TRACHEOSTOMY_SNOMED = "55622001"
_CENTRAL_LINE_SNOMED = "392230005"
_CHEST_TUBE_SNOMED = "177788009"
_OSTOMY_SNOMED = "4044002"
_ECMO_SNOMED = "233573008"

_EDEMA_SNOMED = "79654002"
_SPINAL_CORD_INJURY_SNOMED = "90584004"
_ICU_ADMISSION_SNOMED = "309904001"
_GIM_SERVICE_CODE = "gim-service"

_VASOPRESSIN_RXNORM = "11149"
_CARDIO_SYMPATHOMIMETIC_RXNORM = {"3628", "7512", "3992", "8163"}


def extract_risk_input_from_bundle(bundle: dict[str, Any]) -> RiskAssessmentInput:
    """Build a RiskAssessmentInput from an already-fetched FHIR Bundle or resource.

    Every field except ``age`` falls back to the model's documented default
    when the corresponding resource is absent from the bundle. ``age`` has no
    model default, so a missing ``Patient.birthDate`` raises ``ValueError``
    rather than silently fabricating a clinically meaningful value.
    """
    resources = _resources(bundle)

    kwargs: dict[str, Any] = {"age": _age_from_patient(_first(resources, "Patient"))}

    labs = _numeric_observations_by_loinc(resources)
    if _ALBUMIN_LOINC in labs:
        kwargs["albumin"] = labs[_ALBUMIN_LOINC]
    if _BUN_LOINC in labs:
        kwargs["bun"] = labs[_BUN_LOINC]
    if _CHLORIDE_LOINC in labs:
        kwargs["chloride"] = labs[_CHLORIDE_LOINC]
    if _RDW_CV_LOINC in labs:
        kwargs["rdw_cv"] = labs[_RDW_CV_LOINC]

    if _BRADEN_MOBILITY_LOINC in labs:
        kwargs["braden_mobility"] = BradenMobilityScore(str(int(labs[_BRADEN_MOBILITY_LOINC])))
    if _BRADEN_MOISTURE_LOINC in labs:
        kwargs["braden_moisture"] = BradenMoistureScore(str(int(labs[_BRADEN_MOISTURE_LOINC])))
    if _BRADEN_ACTIVITY_LOINC in labs:
        kwargs["braden_activity"] = BradenActivityScore(str(int(labs[_BRADEN_ACTIVITY_LOINC])))
    if _BRADEN_FRICTION_LOINC in labs:
        kwargs["braden_friction"] = BradenFrictionScore(str(int(labs[_BRADEN_FRICTION_LOINC])))
    if _BRADEN_SENSORY_LOINC in labs:
        kwargs["braden_sensory"] = BradenSensoryScore(str(int(labs[_BRADEN_SENSORY_LOINC])))
    if _GAIT_TRANSFER_LOINC in labs:
        kwargs["gait_transfer"] = GaitTransferScore(str(int(labs[_GAIT_TRANSFER_LOINC])))

    procedure_codes = _codes(resources, "Procedure", _SNOMED)
    kwargs["has_tracheostomy"] = _TRACHEOSTOMY_SNOMED in procedure_codes
    kwargs["has_central_line"] = _CENTRAL_LINE_SNOMED in procedure_codes
    kwargs["has_chest_tube"] = _CHEST_TUBE_SNOMED in procedure_codes
    kwargs["has_ostomy"] = _OSTOMY_SNOMED in procedure_codes
    kwargs["is_on_ecmo"] = _ECMO_SNOMED in procedure_codes

    condition_codes = _codes(resources, "Condition", _SNOMED)
    kwargs["has_edema"] = _EDEMA_SNOMED in condition_codes
    kwargs["has_spinal_cord_injury"] = _SPINAL_CORD_INJURY_SNOMED in condition_codes
    kwargs["is_icu_admitted"] = _ICU_ADMISSION_SNOMED in condition_codes

    gim_codes = _codes(resources, "Observation", _GIM_SERVICE_SYSTEM)
    kwargs["is_on_gim_service"] = _GIM_SERVICE_CODE in gim_codes

    medication_codes = _codes(resources, "MedicationRequest", _RXNORM)
    kwargs["is_on_vasopressin"] = _VASOPRESSIN_RXNORM in medication_codes
    kwargs["is_on_cardio_sympathomimetic"] = bool(medication_codes & _CARDIO_SYMPATHOMIMETIC_RXNORM)

    return RiskAssessmentInput(**kwargs)


def _resources(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the resources in a Bundle, or ``[bundle]`` if a single resource was passed."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry", []) if entry.get("resource")]
    return [bundle]


def _first(resources: list[dict[str, Any]], resource_type: str) -> Optional[dict[str, Any]]:
    return next((r for r in resources if r.get("resourceType") == resource_type), None)


def _codes(resources: list[dict[str, Any]], resource_type: str, system: str) -> set[str]:
    """Collect every ``code.coding[].code`` for a resource type, filtered to one code system."""
    found: set[str] = set()
    for resource in resources:
        if resource.get("resourceType") != resource_type:
            continue
        concept = resource.get("code") or resource.get("medicationCodeableConcept") or {}
        for coding in concept.get("coding", []):
            if coding.get("system") == system and coding.get("code"):
                found.add(coding["code"])
    return found


def _numeric_observations_by_loinc(resources: list[dict[str, Any]]) -> dict[str, float]:
    """Map LOINC code → numeric value for every Observation with a quantity/integer value."""
    values: dict[str, float] = {}
    for resource in resources:
        if resource.get("resourceType") != "Observation":
            continue
        value = resource.get("valueQuantity", {}).get("value")
        if value is None:
            value = resource.get("valueInteger")
        if value is None:
            continue
        for coding in resource.get("code", {}).get("coding", []):
            if coding.get("system") == "http://loinc.org" and coding.get("code"):
                values[coding["code"]] = float(value)
    return values


def _age_from_patient(patient: Optional[dict[str, Any]]) -> int:
    """Calculate age in years from Patient.birthDate.

    Raises:
        ValueError: if ``patient`` is absent or has no ``birthDate`` — age has
            no model default, so it cannot be silently fabricated.
    """
    birth_date_str = patient.get("birthDate") if patient else None
    if not birth_date_str:
        raise ValueError(
            "Cannot extract RiskAssessmentInput.age: bundle has no Patient "
            "with a birthDate"
        )
    parts = [int(p) for p in birth_date_str.split("-")]
    birth = date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
