"""Business Process — patient-view CDS hook orchestrator.

Responsibilities (Phase 1 — sequential, read-only):
1. Validate PatientViewContext (patientId, userId already enforced by Pydantic).
2. Inspect prefetch — is the Patient resource present and sufficient?
   If not, call BO.Fhir using fhirServer + fhirAuthorization to retrieve it.
3. Extract HAPI inputs from the available FHIR resources.
4. Delegate to BP.Hapi for risk calculation.
5. Build and return the CdsHookResponse (cards).
"""

from iop import BusinessProcess

from CDS.interop.msg.cds_hooks import PatientViewRequest, PatientViewResponse


class PatientView(BusinessProcess):
    def on_patient_view_request_message(
        self, request: PatientViewRequest
    ) -> PatientViewResponse:
        # TODO Phase 1: implement orchestration
        raise NotImplementedError("PatientView BP not yet implemented")
