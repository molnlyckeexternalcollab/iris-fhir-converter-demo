"""Business Processes for HL7v2 → FHIR conversion pipeline."""

import os
import json
import uuid
from datetime import date, datetime, timezone

from iop import BusinessProcess, target
import iris

from EAI.msg import FhirRequest, FhirConverterMessage, FhirConverterResponse
import jwt

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.riskassessment import RiskAssessment, RiskAssessmentPrediction
from CDS.models import RiskAssessmentInput, RiskCalculationResult
from CDS.interop.msg import RiskAssessmentInputRequest, RiskAssessmentResultResponse

class FhirConverterProcess(BusinessProcess):
    """Routes HL7v2 messages through FHIR conversion and submission."""

    converter_target = target()
    file_target = target()
    fhir_target = target()
    cds_hapi_risk_target = target()

    def on_enslib_message(self, request: 'iris.EnsLib.HL7.Message') -> None:
        """
        Handle native IRIS HL7 message.
        
        Args:
            request: Native IRIS HL7 message
        """
        try:
            fcm = FhirConverterMessage(
                input_filename=os.path.basename(request.Source),
                input_data=request.RawContent,
                input_data_type='Hl7v2',
                root_template=request.Name
            )
            converted_rsp: FhirConverterResponse = self.submit_fhir_converter_message(fcm)

            # Enhance the converted FHIR bundle with a HAPI pressure injury RiskAssessment
            try:
                fhir_data = json.loads(converted_rsp.output_data)
                hapi_input, patient_ref = self._extract_hapi_input(fhir_data)
                risk_request = RiskAssessmentInputRequest(input=hapi_input)
                risk_response: RiskAssessmentResultResponse = self.send_request_sync(self.cds_hapi_risk_target, risk_request)
                risk_assessment = self._build_risk_assessment(risk_response.result, patient_ref)
                fhir_data = self._add_to_bundle(fhir_data, risk_assessment)
                converted_rsp.output_data = json.dumps(fhir_data)
            except Exception as e:
                self.log_warning(f"HAPI risk enhancement failed, sending original bundle: {e}")

            # send this to the FHIR server
            fhir_request = FhirRequest(
                url='https://webgateway',
                resource='fhir/r4/',
                method='POST',
                data=converted_rsp.output_data,
                headers={'Accept': 'application/json', 'Content-Type': 'application/json+fhir'}
            )

            # Drop converted payload to misc/data/fhir via dedicated operation.
            self.send_request_sync(self.file_target, converted_rsp)
            self.send_request_sync(self.fhir_target, fhir_request)


        except Exception as e:
            self.log_error(f'Failed to process HL7 message: {str(e)}')
            raise

    def submit_fhir_converter_message(self, request: FhirConverterMessage) -> FhirConverterResponse:
        """
        Submit message to converter, then post result to FHIR server.
        
        Args:
            request: FhirConverterMessage with HL7 data
        """
        # Normalize template names (force custom template for ADT_Z99)
        request.root_template = (
            'ADT_CUSTOM' if request.root_template == 'ADT_Z99'
            else request.root_template
        )

        # Convert HL7v2 to FHIR
        response: FhirConverterResponse = self.send_request_sync(
            self.converter_target,
            request
        )
        response.output_filename = request.input_filename.replace('.hl7', '.json')
        self.log_info(f'Converted {request.input_filename} → {response.output_filename}')

        return response

    def _extract_hapi_input(self, fhir_data: dict) -> tuple:
        """Extract patient data from a FHIR Bundle/Patient for HAPI risk input.
        Returns (input_dict, patient_reference).
        """
        patient = None
        patient_ref = "Patient/unknown"

        if fhir_data.get("resourceType") == "Bundle":
            for entry in fhir_data.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    patient = resource
                    patient_ref = f"Patient/{resource.get('id', 'unknown')}"
                    break
        elif fhir_data.get("resourceType") == "Patient":
            patient = fhir_data
            patient_ref = f"Patient/{fhir_data.get('id', 'unknown')}"

        age = self._calculate_age(patient.get("birthDate") if patient else None)
        return RiskAssessmentInput(age=age), patient_ref

    def _calculate_age(self, birth_date_str: str) -> int:
        """Calculate age in years from a FHIR birthDate string (YYYY-MM-DD or YYYY)."""
        if not birth_date_str:
            return 65  # fallback when birthDate is absent
        try:
            parts = birth_date_str.split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            today = date.today()
            age = today.year - year - ((today.month, today.day) < (month, day))
            return max(0, age)
        except (ValueError, IndexError):
            return 65

    def _build_risk_assessment(self, risk_result: RiskCalculationResult, patient_ref: str) -> dict:
        """Build a validated FHIR R4 RiskAssessment resource from a HAPI risk calculation result."""
        ra = RiskAssessment(
            status="final",
            subject=Reference(reference=patient_ref),
            occurrenceDateTime=datetime.now(timezone.utc).isoformat(),
            performer=Reference(display="IRIS CDS HAPI Risk Calculator"),
            method=CodeableConcept(
                coding=[Coding(
                    system="http://snomed.info/sct",
                    code="225338004",
                    display="Risk assessment (procedure)",
                )],
                text="Reese et al. (2024) HAPI logistic regression model",
            ),
            code=CodeableConcept(
                coding=[Coding(
                    system="http://snomed.info/sct",
                    code="225392000",
                    display="Assessment of risk of pressure injury (procedure)",
                )],
            ),
            prediction=[RiskAssessmentPrediction(
                outcome=CodeableConcept(
                    coding=[Coding(
                        system="http://snomed.info/sct",
                        code="709511002",
                        display="Assessment of risk for hospital acquired complication (procedure)",
                    )],
                ),
                probabilityDecimal=risk_result.risk_percentage,
                qualitativeRisk=CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/risk-probability",
                        code=risk_result.risk_category,
                        display=risk_result.risk_category.capitalize(),
                    )],
                ),
                rationale=(
                    f"95% CI: {risk_result.ci_lower:.2f}%\u2013{risk_result.ci_upper:.2f}%, "
                    f"Z-score: {risk_result.z_score:.3f}"
                ),
            )],
            mitigation=(
                "Implement pressure injury prevention protocol: reposition every 2 hours, "
                "use pressure-relieving mattress, maintain skin integrity assessment."
            ),
        )
        return ra.model_dump(mode='json', exclude_none=True, by_alias=True)

    def _add_to_bundle(self, fhir_data: dict, risk_assessment: dict) -> dict:
        """Add the RiskAssessment to a FHIR Bundle, or wrap it in one if needed."""
        entry = {
            "fullUrl": f"urn:uuid:{uuid.uuid4()}",
            "resource": risk_assessment,
            # required by IRIS DefaultBundleProcessor for transaction bundles
            "request": {
                "method": "POST",
                "url": "RiskAssessment"
            }
        }
        if fhir_data.get("resourceType") == "Bundle":
            fhir_data.setdefault("entry", []).append(entry)
        else:
            fhir_data = {
                "resourceType": "Bundle",
                "type": "transaction",
                "entry": [
                    {"resource": fhir_data},
                    entry
                ]
            }
        return fhir_data


class FhirMainProcess(BusinessProcess):

    target = 'FHIR_MAIN_HTTP'

    def on_fhir_request(self, request:'iris.HS.FHIRServer.Interop.Request'):
        # Do something with the request
        self.log_info('Received a FHIR request')

        self.logger.debug(f'Request: {request}')

        token_id = request.Request.AdditionalInfo.GetAt("USER:TokenId")

        token = self.get_token_string(token_id)

        # before sending the request, check to a random rest api call
        random_rest_response = self.send_request_sync('RANDOM_REST_HTTP', FhirRequest(
            url=None,
            resource=None,
            method='GET',
            data='',
            headers={}
        ))

        self.log_info(f'Response from random rest api: {random_rest_response}')

        # pass it to the target
        rsp = self.send_request_sync(self.target, request)

        # Do something with the response
        if self.check_token(token):
            self.log_info('Filtering the response')
            # Filter the response
            payload_str = self.quick_stream_to_string(rsp.QuickStreamId)

            # if the payload is empty, return the response
            if payload_str == '':
                return rsp

            filtered_payload_string = self.filter_resources(json.loads(payload_str))

            # write the json string to a quick stream
            quick_stream = self.string_to_quick_stream(json.dumps(filtered_payload_string))

            rsp = rsp._ConstructClone(1)
            # return the response
            rsp.QuickStreamId = quick_stream._Id()

        return rsp
    
    def get_token_string(self, token_id:str) -> str:
        """
        Returns the token string from the JWT token.
        """
        ## ##class(HS.HC.Util.InfoCache).GetTokenInfoItem(tokenCacheId, "token_string")
        token_info = iris.cls('HS.HC.Util.InfoCache').GetTokenInfoItem(token_id, 'token_string')
        if not token_info:
            raise ValueError(f'Token with ID {token_id} not found in the cache.')
        return token_info

    def check_token(self, token:str) -> bool:

        # decode the token
        try:
            decoded_token= jwt.decode(token, options={"verify_signature": False})
        except jwt.exceptions.DecodeError:
            return False

        # check if the token is valid
        if 'VIP' in decoded_token['scope']:
            return True
        else:
            return False

    def filter_patient_resource(self, patient_dict:dict) -> dict:
        # filter the patient
        # remove the name
        del patient_dict['name']
        # remove the address
        patient_dict['address'] = None
        # remove the telecom
        patient_dict['telecom'] = []
        # remove the birthdate
        patient_dict['birthDate'] = None

        return patient_dict

    def filter_resources(self, resource_dict:dict) -> dict:
        # what is the resource type?
        resource_type = resource_dict['resourceType'] if 'resourceType' in resource_dict else 'None'
        self.log_info('Resource type: ' + resource_type)

        # is it a bundle?
        if resource_type == 'Bundle':
            # filter the bundle
            for entry in resource_dict['entry']:
                if entry['resource']['resourceType'] == 'Patient':
                    self.log_info('Filtering a patient')
                    entry['resource'] = self.filter_patient_resource(entry['resource'])

        elif resource_type == 'Patient':
            # filter the patient
            payload_dict = self.filter_patient_resource(resource_dict)
        else:
            self.log_info('Resource type is not supported for filtering: ' + resource_type)
            return resource_dict

        return resource_dict

    def quick_stream_to_string(self, quick_stream_id) -> str:
        quick_stream = iris.cls('HS.SDA3.QuickStream')._OpenId(quick_stream_id)
        json_payload = ''
        while quick_stream.AtEnd == 0:
            json_payload += quick_stream.Read()

        return json_payload
    
    def string_to_quick_stream(self, json_string:str):
        quick_stream = iris.cls('HS.SDA3.QuickStream')._New()

        # write the json string to the payload
        n = 3000
        chunks = [json_string[i:i+n] for i in range(0, len(json_string), n)]
        for chunk in chunks:
            quick_stream.Write(chunk)

        return quick_stream