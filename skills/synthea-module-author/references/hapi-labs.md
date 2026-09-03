# HAPI DSE Lab Panel Reference

This document serves as a reference guide and knowledge base for an AI skill integrated within a Synthea HAPI (Hospital-Acquired Pressure Injury) module. This document details the clinical data points required for HAPI risk calculation and prevention, including specific measurements (like albumin, BUN, chloride) and assessment scores (like the Braden Scale components). The AI skill reads this document to understand these requirements and potentially enhance or customize the Synthea module's data generation capabilities to accurately reflect the clinical context needed for HAPI prediction and management within the simulation. We will now focus on extending this document to include the Braden Scale components for improved data generation.

Project-specific reference for the `iris-fhir-converter-demo` HAPI risk calculator.
All codes were validated against tx.fhir.org on 2026-07-22.

## HAPI model inputs (`RiskAssessmentInput`)

The DSE calculator (`/dse/hapi`) accepts the following fields.
All fields except `age` have defaults, so Synthea only needs to emit what varies per archetype.

### Patient Demographics

| Field | Type | Default  | Unit  | Source in Synthea | Note                                   |
|-------|------|----------|-------|-------------------|----------------------------------------|
| `age` | int  | required | years | Patient.birthDate | Patient age in years (required, 0-150) |

### Clinical Measurements (lab values with defaults per model)

| Field      | Type  | Default | Unit  | Source in Synthea        | Note                                                      |
|------------|-------|---------|-------|--------------------------|-----------------------------------------------------------|
| `albumin`  | float | 3.6     | g/dL  | Observation LOINC 1751-7 | Albumin level (default: 3.6 if missing)                   |
| `bun`      | float | 16.0    | mg/dL | Observation LOINC 3094-0 | Blood Urea Nitrogen (default: 16 if missing)              |
| `chloride` | float | 105.0   | mEq/L | Observation LOINC 2075-0 | Chloride level (default: 105 if missing)                  |
| `rdw_cv`   | float | 13.9    | %     | Observation LOINC 788-0  | Red cell distribution width CV (default: 13.9 if missing) |

### Braden score components

The HAPI calculator accepts five Braden Scale domains plus a separate gait/transfer
assessment. The standard Braden Scale has six domains and includes Nutrition; this
calculator does not accept a nutrition field. Do not add a nutrition input to a
generated module unless the calculator contract is extended first.

These are nursing assessments, not laboratory measurements. Represent a generated
assessment as a FHIR `Observation` in the `survey` category, using the numeric score
as the observation value. In Synthea JSON, use `exact.quantity` and the unit
`{score}` for a single generated score. Use the LOINC code and canonical display
listed below; do not use a laboratory category. The model input is a categorical
string, so extraction must convert the numeric FHIR value to the documented string
enum. An absent assessment must remain absent so extraction can map it to `missing`;
do not emit the literal string `missing` as an Observation value.

| Field             | Type               | Default   | Score values | LOINC     | Canonical display               |
|-------------------|--------------------|-----------|--------------|-----------|---------------------------------|
| `braden_mobility` | categorical string | `missing` | `1`-`4`      | `38224-2` | Physical mobility Braden scale  |
| `braden_moisture` | categorical string | `missing` | `1`-`4`      | `38229-1` | Moisture exposure Braden scale  |
| `braden_activity` | categorical string | `missing` | `1`-`4`      | `38223-4` | Physical activity Braden scale  |
| `braden_friction` | categorical string | `missing` | `1`-`3`      | `38226-7` | Friction and shear Braden scale |
| `braden_sensory`  | categorical string | `missing` | `1`-`4`      | `38222-6` | Sensory perception Braden scale |

The calculator also accepts this non-Braden assessment:

| Field           | Type               | Default   | Score values    | LOINC     | Canonical display                        |
|-----------------|--------------------|-----------|-----------------|-----------|------------------------------------------|
| `gait_transfer` | categorical string | `missing` | `0`, `10`, `20` | `93015-6` | Gait and turn and tandem gait assessment |

The five Braden LOINC codes and the gait LOINC code above were looked up on
`tx.fhir.org` on 2026-09-03. The LOINC codes identify the assessment concepts; they
do not by themselves establish that an Observation contains a valid score. Keep
the value in the documented range and preserve the assessment time and encounter.

For synthetic data, condition-based derivation may be used only as an explicit
test-data heuristic, not presented as a recorded nursing assessment. If a score
cannot be derived reliably, omit the Observation and let extraction produce
`missing`.

#### Braden Mobility

This component assesses the patient's ability to move, including in bed, transferring, and ambulating. It uses a 4-point scale and is recorded as a single overall mobility score.

- Score values are 1=Completely Immobile, 2=Very Limited, 3=Slightly Limited, and 4=No Limitation.
- The FHIR resource `interpretation` field can provide context for the score (e.g., "Limited", "Very Limited").
- The FHIR resource `performer` field indicates who performed the assessment (e.g., Nurse, Physical Therapist).
- Sometimes, narrative notes or FHIR `Condition` resources might supplement these observations with descriptions of the patient's functional limitations.

#### Braden Moisture

Possible categories:

- 1=Constantly Moist
- 2=Very Moist
- 3=Occasionally Moist
- 4=Rarely Moist

#### Braden Activity

Possible categories:

- 1=Bedfast
- 2=Chairfast
- 3=Walks Occasionally
- 4=Walks Frequently

#### Braden Friction

Possible categories:

- 1=Problem
- 2=Potential Problem
- 3=No Apparent Problem

#### Braden Sensory

Possible categories:

- 1=Completely Limited
- 2=Very Limited
- 3=Slightly Limited
- 4=No Impairment

#### Gait and Transfer

This is a separate model feature, not one of the six Braden domains. The model's
encoded values are:

- 0=Normal gait
- 10=Weak gait
- 20=Impaired gait

Do not encode this assessment as Braden score values 1, 2, and 3.

---

## Validated LOINC codes (lab observations)

| Concept                      | LOINC  | Canonical display (tx.fhir.org)                     | Unit  |
|------------------------------|--------|-----------------------------------------------------|-------|
| Albumin                      | 1751-7 | Albumin [Mass/volume] in Serum or Plasma            | g/dL  |
| Blood Urea Nitrogen (BUN)    | 3094-0 | Urea nitrogen [Mass/volume] in Serum or Plasma      | mg/dL |
| Chloride                     | 2075-0 | Chloride [Moles/volume] in Serum or Plasma          | mEq/L |
| RDW-CV (erythrocyte width %) | 788-0  | Erythrocyte [DistWidth] in Blood by Automated count | %     |

Panel grouping codes (for `DiagnosticReport` states):

| Panel                        | LOINC   | Canonical display (tx.fhir.org)                      |
|------------------------------|---------|------------------------------------------------------|
| Metabolic panel (alb/BUN/Cl) | 24323-8 | Comprehensive metabolic 2000 panel - Serum or Plasma |
| CBC panel (includes RDW-CV)  | 58410-2 | CBC panel - Blood by Automated count                 |

**Design note**: albumin, BUN, and chloride naturally group under a metabolic panel (24323-8). RDW-CV groups under a CBC panel (58410-2). Use two separate `DiagnosticReport` states, or use four individual `Observation` states if panel grouping is not required for downstream extraction.

---

## Validated SNOMED codes (conditions and encounter)

| Concept                     | SNOMED    | Canonical display (tx.fhir.org)                             | Used in module(s)                                                               |
|-----------------------------|-----------|-------------------------------------------------------------|---------------------------------------------------------------------------------|
| Systemic infection (sepsis) | 91302008  | Systemic infection                                          | Lab high-risk guard; vasopressin/central-line/tracheostomy/chest-tube/ICU guard |
| Septic shock                | 76571007  | Septic shock                                                | Same guards + ECMO                                                              |
| Heart failure               | 84114007  | Heart failure                                               | Lab moderate-risk guard; edema/cardio/GIM guard                                 |
| Frailty                     | 248279007 | Frailty                                                     | Edema/GIM guard                                                                 |
| Hospital admission          | 32485007  | Hospital admission                                          | Encounter class (inpatient)                                                     |
| Edema                       | 79654002  | Edema                                                       | hapi_edema ConditionOnset                                                       |
| Spinal cord injury          | 90584004  | Spinal cord injury                                          | hapi_spinal_cord_injury ConditionOnset                                          |
| Intensive care unit         | 309904001 | Intensive care unit                                         | hapi_icu_admit ConditionOnset (avoids collision with CHF module)                |
| Catheterisation of vein     | 392230005 | Catheterisation of vein                                     | hapi_central_line Procedure                                                     |
| Tracheostomy (emergency)    | 55622001  | Tracheostomy, emergency procedure by transtracheal approach | hapi_tracheostomy Procedure                                                     |
| Open pleural drainage       | 177788009 | Open drainage of pleural cavity                             | hapi_chest_tube Procedure                                                       |
| Permanent colostomy         | 4044002   | Permanent colostomy                                         | hapi_ostomy Procedure                                                           |
| ECMO                        | 233573008 | ECMO - Extracorporeal membrane oxygenation                  | hapi_ecmo Procedure                                                             |

**Note on `91302008`**: tx.fhir.org returns canonical display "Systemic infection". Synthea's existing sepsis modules may use display "Sepsis (disorder)" — this is acceptable since Synthea does not validate display strings, but document the discrepancy in the module's `remarks`.

---

## Value ranges per risk archetype

Use these in Synthea `Observation` or `DiagnosticReport` `range` fields.
Ranges reflect clinically realistic values for each population segment.

### Low-risk inpatient (age ≥ 55, no qualifying conditions)

| Lab      | Low  | High | Unit  | Notes                |
|----------|------|------|-------|----------------------|
| Albumin  | 3.2  | 4.0  | g/dL  | Normal to low-normal |
| BUN      | 14   | 22   | mg/dL | Normal               |
| Chloride | 100  | 108  | mEq/L | Normal               |
| RDW-CV   | 12.5 | 14.5 | %     | Normal               |

### Moderate-risk (heart failure or frailty)

| Lab      | Low  | High | Unit  | Notes                                       |
|----------|------|------|-------|---------------------------------------------|
| Albumin  | 2.5  | 3.2  | g/dL  | Mildly low — chronic illness/malnutrition   |
| BUN      | 22   | 35   | mg/dL | Mildly elevated — reduced renal perfusion   |
| Chloride | 96   | 102  | mEq/L | Mildly low — diuretic effect in HF          |
| RDW-CV   | 14.5 | 17.0 | %     | Mildly elevated — anemia of chronic disease |

### High-risk (sepsis / systemic infection / ICU)

| Lab      | Low  | High | Unit  | Notes                                    |
|----------|------|------|-------|------------------------------------------|
| Albumin  | 1.5  | 2.2  | g/dL  | Markedly low — acute phase response      |
| BUN      | 40   | 80   | mg/dL | Elevated — prerenal azotemia, catabolism |
| Chloride | 92   | 99   | mEq/L | Low-normal — dilutional or GI losses     |
| RDW-CV   | 16.0 | 20.0 | %     | Elevated — stress erythropoiesis         |

---

## Braden score derivation (extraction time, not Synthea)

When extracting Synthea FHIR bundles to build `RiskAssessmentInput`, derive the
model's mobility sub-score from active conditions only when the test scenario
explicitly calls for that heuristic:

| Condition (SNOMED)                     | Mobility score    |
|----------------------------------------|-------------------|
| Frailty (248279007)                    | 2                 |
| Systemic infection / sepsis (91302008) | 1                 |
| Heart failure (84114007)               | 2                 |
| No qualifying condition                | 4 (no limitation) |

Do not infer moisture, activity, friction, sensory perception, or gait from a
condition unless a separate test-data rule defines and documents that mapping.
Use `missing` for any model field that cannot be reliably derived.

---

## Synthea modules location

All 12 HAPI augmentation modules live in:

```
iris-fhir-converter-demo/src/DSE/synthea/
  hapi_lab_observations.json        # Observations: albumin/BUN/chloride/RDW-CV
  hapi_edema.json                   # ConditionOnset: SNOMED 79654002
  hapi_vasopressin.json             # MedicationOrder: RxNorm 11149
  hapi_cardio_sympathomimetics.json # MedicationOrder: RxNorm 3628/7512/3992/8163
  hapi_central_line.json            # Procedure: SNOMED 392230005
  hapi_tracheostomy.json            # Procedure: SNOMED 55622001
  hapi_chest_tube.json              # Procedure: SNOMED 177788009
  hapi_ostomy.json                  # Procedure: SNOMED 4044002 (5% prevalence, age>=55)
  hapi_ecmo.json                    # Procedure: SNOMED 233573008
  hapi_spinal_cord_injury.json      # ConditionOnset: SNOMED 90584004 (3% prevalence, age>=55)
  hapi_icu_admit.json               # ConditionOnset: SNOMED 309904001 (sepsis/septic shock)
  hapi_gim_service.json             # Observation: local code gim-service (HF/frailty, 60% branch)
```

**Code collision note**: `hapi_icu_admit` uses `ConditionOnset` with SNOMED `309904001` (Intensive care unit)
instead of `Procedure 305351004` (Admit to ITU) to avoid collision with Synthea's built-in
`congestive_heart_failure` module which already records that procedure.

**GIM service note**: No SNOMED procedure or finding code exists for "on GIM service".
`hapi_gim_service` uses `Observation` with local system `http://hapi-dse.local/CodeSystem`
code `gim-service`. The extraction script detects it by that system URI.

## Synthea run command for HAPI test data

Use `-d` to load the modules from `iris-fhir-converter-demo`. Always `rm output/fhir/*.json` first — Synthea appends, not overwrites.

```bash
cd ~/Developer/misc/synthea
rm -f output/fhir/*.json
./run_synthea -p 1000 -s 42 -a 55-85 --exporter.years_of_history=3 \
  -d ~/Developer/misc/iris-fhir-converter-demo/src/DSE/synthea
```

> [!NOTE]
> The `-p 1000` flag in Synthea specifies the number of **living** patients to generate, not the total. Synthea simulates full life cycles — with an age range of 55–85, a significant portion of generated patients die during the simulation.
> Synthea keeps running until it has 1,000 **alive** patients at export time, but all patients (including deceased ones) are written to output files.
> 
> So: **1,368 total = ~1,000 living + ~368 deceased**.
> 
> The older the age range, the more "extra" patients you get since mortality is higher. If you wanted exactly 1,000 files you'd need to either:
> - Filter to living patients only (check `Patient.deceasedBoolean` / `Patient.deceasedDateTime`), or
> - Use a younger age range with lower mortality



Output: `output/fhir/` — one FHIR Bundle JSON per patient.

Check all HAPI resources in one pass:
```bash
jq -r '
  .entry[].resource |
  if .resourceType == "Condition" then "COND \(.code.coding[0].code) \(.code.coding[0].display)"
  elif .resourceType == "Procedure" then "PROC \(.code.coding[0].code) \(.code.coding[0].display)"
  elif .resourceType == "MedicationRequest" then "MED \(.medicationCodeableConcept.coding[0].code // "ref") \(.medicationCodeableConcept.coding[0].display // "")"
  elif .resourceType == "Observation" then "OBS \(.code.coding[0].code)"
  else empty end
' output/fhir/*.json | grep -E \
  "COND (84114007|248279007|91302008|76571007|79654002|90584004|309904001)|\
PROC (392230005|55622001|177788009|4044002|233573008)|\
MED (11149|3628|7512|3992|8163)|\
OBS gim-service" | sort | uniq -c
```

Expected resource types per module:

| Module                       | Resource type     | Code to grep                                           |
|------------------------------|-------------------|--------------------------------------------------------|
| hapi_lab_observations        | Observation       | 1751-7, 3094-0, 2075-0, 788-0                          |
| hapi_edema                   | Condition         | 79654002                                               |
| hapi_vasopressin             | MedicationRequest | 11149                                                  |
| hapi_cardio_sympathomimetics | MedicationRequest | 3628, 7512, 3992, 8163                                 |
| hapi_central_line            | Procedure         | 392230005                                              |
| hapi_tracheostomy            | Procedure         | 55622001                                               |
| hapi_chest_tube              | Procedure         | 177788009                                              |
| hapi_ostomy                  | Procedure         | 4044002                                                |
| hapi_ecmo                    | Procedure         | 233573008                                              |
| hapi_spinal_cord_injury      | Condition         | 90584004                                               |
| hapi_icu_admit               | Condition         | 309904001                                              |
| hapi_gim_service             | Observation       | gim-service (system: http://hapi-dse.local/CodeSystem) |
