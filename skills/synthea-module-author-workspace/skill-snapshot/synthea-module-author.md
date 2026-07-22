---
name: synthea-module-author
description: Create valid Synthea disease modules with grounded medical codes. Every code is validated against a real terminology server — never hallucinated from training data.
---

# Synthea Module Author

A skill for creating new Synthea modules or extending existing ones. It generates valid JSON for Synthea's module engine, with grounded medical codes from SNOMED, LOINC, and RxNorm.

## When to use this skill

- "Create a Synthea module for celiac disease"
- "Add a rare condition to Synthea"
- "Write a module for [condition] with labs, meds, and encounters"
- "Extend the diabetes module to include CKD progression"

## Before you start

You need a cloned and built copy of Synthea:

```bash
git clone https://github.com/synthetichealth/synthea.git
cd synthea
./gradlew build -x test   # Java 11+ required, ~45 seconds
```

## Module JSON Schema

Every Synthea module is a JSON file in `src/main/resources/modules/` with keys:

- `name`,
- `states` object,
- `remarks` array of strings describing the module
- and a `gmf_version`.

Each state object has a `type` and a `transition`.
Example of top-level structure:

```json
{
  "name": "Module Display Name",
  "remarks": [
    "An explanation of what this module models",
    "Another remark about prevalence, data sources, or assumptions"
  ],
  "states": {
    "Initial": {
      "type": "Initial",
      "distributed_transition": [
        { "distribution": 0.01, "transition": "Onset" },
        { "distribution": 0.99, "transition": "Terminal" }
      ]
    },
    "Onset": {
      "type": "ConditionOnset",
      "codes": [{ "system": "SNOMED-CT", "code": "??????", "display": "??????" }],
      "direct_transition": "Terminal"
    },
    "...": "...",
    "Terminal": { "type": "Terminal" }
  },
  "gmf_version": 2
}
```

### State types

The table below lists all state types in Synthea, extracted from [State class documentation](https://synthetichealth.github.io/synthea/build/javadoc/org/mitre/synthea/engine/State.html).
Each state type has a specific purpose and may require medical codes from SNOMED, LOINC, or RxNorm and can be used or must not be used in a module.
The "Can be used?" column indicates whether the state type can be used in a module or must not be used.
The "Requires codes?" column indicates whether the state type requires medical codes to function correctly.

| Type                        | Can be used? | Purpose                                                                                                                                                     | Requires codes?             |
|-----------------------------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------|
| `AllergyEnd`                | No           | Indicates a point in the module where a currently active allergy should be ended, for example if the patient's allergy subsides with time.                  | TBD                         |
| `AllergyOnset`              | No           | Indicates a point in the module where the patient acquires an allergy.                                                                                      | TBD                         |
| `CallSubmodule`             | Yes          | Immediately processes a reusable series of states contained in a submodule.                                                                                 | No                          |
| `CarePlanEnd`               | Yes          | Indicates a point in the module where a currently prescribed care plan should be ended.                                                                     | No                          |
| `CarePlanStart`             | Yes          | Indicates a point in the module where a care plan should be prescribed.                                                                                     | Yes (SNOMED)                |
| `ConditionEnd`              | Yes          | Indicates a point in the module where a currently active condition should be ended, for example if the patient has been cured of a disease.                 | No (references prior onset) |
| `ConditionOnset`            | Yes          | Indicates a point in the module where the patient acquires a condition.                                                                                     | Yes (SNOMED)                |
| `Counter`                   | Yes          | Increments or decrements a specified numeric attribute on the patient entity.                                                                               | No                          |
| `Death`                     | Yes          | Indicates a point in the module at which the patient dies or the patient is given a terminal diagnosis (e.g. "you have 3 months to live")                   | No                          |
| `Delay`                     | Yes          | Introduces a pre-configured temporal delay in the module's timeline.                                                                                        | No                          |
| `Delayable`                 | No           | Represents a state that can be delayed.                                                                                                                     | TBD                         |
| `Device`                    | No           | Indicates the point that a permanent or semi-permanent device (for example, a prosthetic, or pacemaker) is associated to a person.                          | TBD                         |
| `DeviceEnd`                 | No           | Indicates the point that a permanent or semi-permanent device (for example, a prosthetic, or pacemaker) is removed from a person.                           | TBD                         |
| `DiagnosticReport`          | Yes          | Indicates that some number of Observations should be grouped together within a single Diagnostic Report.                                                    | Yes (LOINC)                 |
| `Encounter`                 | Yes          | Indicates a point in the module where an encounter should take place.                                                                                       | Yes (SNOMED)                |
| `EncounterEnd`              | Yes          | Indicates the end of the encounter the patient is currently in, for example when the patient leaves a clinician's office, or is discharged from a hospital. | No                          |
| `Guard`                     | Yes          | Indicates a point in the module through which a patient can only pass if they meet certain logical conditions.                                              | No                          |
| `ImagingStudy`              | No           | Indicates a point in the module when an imaging study was performed.                                                                                        | TBD                         |
| `Initial`                   | Yes          | First state that is processed in a generic module.                                                                                                          | No                          |
| `LegacyStateWithUnitlessRV` | No           | Represents a legacy state with unitless random variables.                                                                                                   | TBD                         |
| `MedicationEnd`             | Yes          | Indicates a point in the module where a currently prescribed medication should be ended.                                                                    | No (references prior order) |
| `MedicationOrder`           | Yes          | Indicates a point in the module where a medication is prescribed.                                                                                           | Yes (RxNorm)                |
| `MultiObservation`          | No           | Indicates that some number of Observations should be grouped together as a single observation.                                                              | TBD                         |
| `Observation`               | Yes          | Indicates a point in the module where an observation is recorded.                                                                                           | Yes (LOINC)                 |
| `Physiology`                | No           | Executes a physiology simulation according to the provided configuration options.                                                                           | TBD                         |
| `Procedure`                 | Yes          | Indicates a point in the module where a procedure should be performed.                                                                                      | Yes (SNOMED)                |
| `SetAttribute`              | Yes          | Sets a specified attribute on the patient entity.                                                                                                           | Store a patient variable.   |
| `Simple`                    | Yes          | Indicates a state that performs no additional actions, adds no additional information to the patient entity, and just transitions to the next state.        | No                          |
| `SupplyList`                | No           | Includes a list of supplies that are needed for the current encounter.                                                                                      | TBD                         |
| `Symptom`                   | No           | Adds or updates a patient's symptom.                                                                                                                        | TBD                         |
| `TelemedicinePossibility`   | No           | Enum for telemedicine encounter possibilities.                                                                                                              | TBD                         |
| `Terminal`                  | Yes          | Indicates the end of the module progression.                                                                                                                | No                          |
| `Vaccine`                   | No           | Indicates a point in the module where the patient is vaccinated.                                                                                            | TBD                         |
| `VitalSign`                 | No           | Indicates a point in the module where a patient's vital sign is set.                                                                                        | TBD                         |

### Transition types

**Direct** — always go to one state:

```json
"direct_transition": "Next_State"
```

**Conditional** — branch on a condition:

```json
"conditional_transition": [
  { "condition": { "condition_type": "Age", "operator": ">", "quantity": 50, "unit": "years" }, "transition": "Older_Path" },
  { "transition": "Default_Path" }
]
```

**Distributed** — probabilistic branching:

```json
"distributed_transition": [
  { "distribution": 0.01, "transition": "Gets_Disease" },
  { "distribution": 0.99, "transition": "No_Disease" }
]
```

**Complex** — conditions with distributions:

```json
"complex_transition": [
  {
    "condition": { "condition_type": "Attribute", "attribute": "risk_factor", "operator": "is not nil" },
    "distributions": [
      { "distribution": 0.05, "transition": "Gets_Disease" },
      { "distribution": 0.95, "transition": "No_Disease" }
    ]
  },
  { "transition": "No_Disease" }
]
```

### Condition types for transitions and guards

| Condition type       | Example                                                                                                           |
|----------------------|-------------------------------------------------------------------------------------------------------------------|
| `Age`                | `{ "condition_type": "Age", "operator": ">", "quantity": 18, "unit": "years" }`                                   |
| `Gender`             | `{ "condition_type": "Gender", "gender": "F" }`                                                                   |
| `Date`               | `{ "condition_type": "Date", "operator": ">=", "year": 2000 }`                                                    |
| `Attribute`          | `{ "condition_type": "Attribute", "attribute": "some_flag", "operator": "is not nil" }`                           |
| `PriorState`         | `{ "condition_type": "PriorState", "name": "Some_State" }`                                                        |
| `Active Condition`   | `{ "condition_type": "Active Condition", "codes": [{ "system": "SNOMED-CT", "code": "...", "display": "..." }] }` |
| `And` / `Or` / `Not` | Nest other conditions with boolean logic                                                                          |

## Code Systems

Every medical code in a module uses this format:

```json
{
  "system": "SNOMED-CT",
  "code": "396331005",
  "display": "Celiac disease (disorder)"
}
```

| System    | URI                                           | Used for                                                      |
|-----------|-----------------------------------------------|---------------------------------------------------------------|
| SNOMED-CT | `http://snomed.info/sct`                      | Conditions, procedures, findings, body sites, encounter types |
| LOINC     | `http://loinc.org`                            | Lab observations, vital signs, diagnostic reports             |
| RxNorm    | `http://www.nlm.nih.gov/research/umls/rxnorm` | Medications                                                   |
| CVX       | `http://hl7.org/fhir/sid/cvx`                 | Vaccines                                                      |

## CRITICAL: Code Grounding Rules

**ALWAYS use Pascal_Snake_Case for the state names** — e.g., `Induction_Medication`, `Isoflurane_End`, `Allergist_Guard`, `General_Allergy_CarePlan`.

**NEVER generate a medical code from memory.** LLMs pattern-match codes from training data. Sometimes they're correct, sometimes they're plausible but don't exist. You cannot tell by looking at a code whether it's real.

**ALWAYS validate every code** against the public FHIR terminology server at tx.fhir.org before writing it into a module.

### Validate a code

```bash
# Validate a SNOMED code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://snomed.info/sct&code=396331005" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'

# Validate a LOINC code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://loinc.org&code=31017-7" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'

# Validate an RxNorm code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://www.nlm.nih.gov/research/umls/rxnorm&code=328383" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'
```

A valid code returns `"valueBoolean": true` and a `"display"` parameter with the canonical name. An invalid code returns `"valueBoolean": false`.

**CRITICAL: Validating existence is not enough.** A code can be valid but mean something completely different from what you intended. `12866006` is a valid SNOMED code — it's pneumococcal vaccination, not duodenal biopsy. After validating, **always compare the canonical display from tx.fhir.org against what you wrote in the module.** If they don't match, the code is wrong even though it's "valid."

```bash
# Example: check that the display matches your intent
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://snomed.info/sct&code=12866006" \
  | jq '.parameter[] | select(.name=="display") | .valueString'
# Returns: "Pneumococcal vaccination" — NOT "Biopsy of duodenum"
```

For every code: validate it exists, then read the display and confirm it describes what you think it describes. This is the step that catches LLM hallucinations.

### Search for codes

When you need to find the right code for a concept:

```bash
# Search SNOMED for a term
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://snomed.info/sct?fhir_vs&filter=celiac+disease&count=5" \
  | jq '.expansion.contains[] | {code, display}'

# Search LOINC for a term
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://loinc.org/vs&filter=tissue+transglutaminase&count=5" \
  | jq '.expansion.contains[] | {code, display}'

# Search RxNorm for a medication
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://www.nlm.nih.gov/research/umls/rxnorm?fhir_vs&filter=ferrous+sulfate&count=5" \
  | jq '.expansion.contains[] | {code, display}'
```

### Rate limiting

tx.fhir.org is a public, free service. Be respectful:

- Add a brief pause between requests (0.5-1 second)
- Cache results within the session — don't re-validate the same code twice
- If you get rate limited (HTTP 429), wait 5 seconds and retry

## Workflow

When asked to create a module:

### Step 1: Check existing modules

```bash
ls synthea/src/main/resources/modules/ | grep -i "<condition>"
grep -rl "<condition>" synthea/src/main/resources/modules/ 2>/dev/null
```

If a module already exists, read it and tell the user what's there. Ask whether they want to extend it or create a new one.

### Step 2: Research the condition

Before writing any JSON, understand:

- Prevalence by age and sex (for transition probabilities)
- Diagnostic criteria (what labs, imaging, or procedures confirm the diagnosis)
- Standard treatment pathway (first-line meds, escalation, monitoring)
- Condition progression (does it resolve? is it lifelong? what complications?)

Use WebSearch if available. If not, state what you know and flag uncertainty.

### Step 3: Look up every code

For each clinical concept in the module, search tx.fhir.org and validate the code. Do this BEFORE writing the module JSON. Build a code inventory:

```text
Concept                    System      Code        Display (from tx.fhir.org)
─────────────────────────  ──────────  ──────────  ─────────────────────────────
Celiac disease             SNOMED-CT   396331005   Celiac disease (disorder)
tTG IgA antibody           LOINC       31017-7     Tissue transglutaminase IgA Ab
Endoscopy of duodenum      SNOMED-CT   386813002   Endoscopy of duodenum
...
```

### Step 4: Generate the module JSON

Write the module following the schema above. Place it in `synthea/src/main/resources/modules/`. Use validated codes only.

Key patterns:

- Start with an `Initial` state and an age/prevalence gate
- Use `distributed_transition` for prevalence-based onset (calibrate against CDC/CMS data)
- Wrap clinical actions (labs, meds, procedures) inside `Encounter`/`EncounterEnd` pairs
- Use `SetAttribute` to track patient state across module cycles
- End chronic conditions with a monitoring loop (`Delay` → `Encounter` → `Delay`)
- Use `target_encounter` on `ConditionOnset`, `Observation`, `Procedure`, `MedicationOrder` to link them to the encounter

### Step 5: Validate the module

```bash
# Structural validation — Synthea's build catches bad JSON
cd synthea && ./gradlew build -x test

# Functional test — generate a patient using only this module
./run_synthea -m <module_name> -p 1 -s 42 -a 30-60

# Check output
jq '.entry[].resource.resourceType' output/fhir/*.json | sort | uniq -c | sort -rn
```

If the build fails, read the error — it usually points to the exact JSON issue (missing required field, invalid state type, bad transition target).

### Step 6: Inspect the generated FHIR

Verify the module produced the expected resources:

```bash
# Check conditions
jq -r '.entry[].resource | select(.resourceType=="Condition") | .code.coding[0].display' output/fhir/*.json

# Check observations/labs
jq -r '.entry[].resource | select(.resourceType=="Observation") | .code.coding[0].display' output/fhir/*.json

# Check medications
jq -r '.entry[].resource | select(.resourceType=="MedicationRequest") | .medicationCodeableConcept.coding[0].display' output/fhir/*.json

# Check procedures
jq -r '.entry[].resource | select(.resourceType=="Procedure") | .code.coding[0].display' output/fhir/*.json
```

## Common pitfalls

1. **Forgetting `target_encounter`** — ConditionOnset, Observation, Procedure, and MedicationOrder states need `"target_encounter": "Encounter_State_Name"` to link them to the active encounter. Without it, the resource is orphaned.

2. **Not ending encounters** — Every `Encounter` state needs a corresponding `EncounterEnd`. Without it, Synthea will error or produce corrupt bundles.

3. **Prevalence miscalibration** — A `distributed_transition` with `0.01` means 1% of the population per timestep (default 1 week). Over a 70-year life, that's not 1% prevalence. Use Synthea's `"remarks"` to document your prevalence math.

4. **Missing Terminal** — Every execution path must eventually reach a `Terminal` state or the module loops forever.

5. **Code system names** — Synthea uses `"SNOMED-CT"` not `"http://snomed.info/sct"` in the `system` field. The URI goes in FHIR export, not in the module JSON.

6. **`exporter.years_of_history` hides older events** — By default Synthea filters exported resources to recent history. If your module's procedures or early encounters are missing from the output, run with `--exporter.years_of_history=0` to keep everything.

7. **Procedures need `duration`** — Add `"duration": { "low": N, "high": M, "unit": "minutes" }` to Procedure states. Without it, some exporters may skip them.

8. **`assign_to_attribute` on ConditionOnset** — If procedures or medications reference the condition via `reason`, add `"assign_to_attribute": "condition_name"` to the ConditionOnset state so the reference resolves.

## Related tools

- **[Synthea Module Builder](https://synthetichealth.github.io/module-builder/)** — GUI for visual module authoring
- **[tx.fhir.org](https://tx.fhir.org)** — public FHIR terminology server (no account needed)
