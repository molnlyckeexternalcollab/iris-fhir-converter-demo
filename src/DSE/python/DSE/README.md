# HAPI risk calculator — model reference

`hapi_calculator.py` implements the Reese et al. (2024) validated logistic
regression model for Hospital-Acquired Pressure Injury (HAC PI) risk.

Reference: https://www.sciencedirect.com/science/article/pii/S2291969424000498

## Algorithm

```
Z = intercept + Σ(coefficient_i × variable_i)      # ~35 coefficients
P = 1 / (1 + exp(-Z))                              # risk probability
95% CI computed via the Delta method
```

`ModelCoefficients` (in `hapi_calculator.py`) holds every coefficient from the
paper's Appendix 1. `calculate_z_score()` sums the intercept with each
variable's contribution; categorical variables (Braden sub-scores, gait
transfer) use a reference category that contributes no coefficient.

## Inputs (`RiskAssessmentInput` in `models.py`)

- **Continuous**: `age` (required, only field without a default), `albumin`,
  `bun`, `chloride`, `rdw_cv`.
- **Braden Scale sub-scores** (categorical, each with a `"missing"` category):
  `braden_mobility`, `braden_moisture`, `braden_activity`, `braden_friction`,
  `braden_sensory`.
- **Gait/transfer assessment**: `gait_transfer` (`"0"`/`"10"`/`"20"`/`"missing"`).
- **Medical devices** (booleans): `has_tracheostomy`, `has_central_line`,
  `has_chest_tube`, `has_ostomy`, `is_on_ecmo`.
- **Clinical conditions** (booleans): edema, spinal cord injury, ICU admission,
  GIM service, vasopressin, cardio-sympathomimetic.

Every field except `age` has a documented model default, so callers can omit
anything they don't have.

## Related docs

- [skills/synthea-module-author/references/hapi-labs.md](../../../../skills/synthea-module-author/references/hapi-labs.md) —
  validated LOINC/SNOMED codes, Braden Scale value tables, per-archetype lab
  value ranges, and how synthetic test data maps to these model inputs.
- [email.md](../../../../email.md) — project narrative motivating this calculator.
- [.github/instructions/dse.instructions.md](../../../../.github/instructions/dse.instructions.md) —
  how this module fits into the DSE namespace and its IRIS production request flow.
