"""
FHIR HL7v2 Converter Production.

Orchestrates HL7v2 → FHIR conversion with the following flow:
  1. HL7v2 messages → FhirConverterProcess
  2. FhirConverterProcess → FhirConverterOperation (conversion)
  3. Converted FHIR → FhirHttpOperation (POST to FHIR server)
  4. FHIR requests → FhirMainProcess (with token validation & filtering)
  5. FhirMainProcess → FhirHttpOperation (forward to FHIR server)

The production also includes a RandomRestOperation for testing external API integration.
"""

import os

from iop import Production

from bs.hapi import Hapi as BSHapi
from bs.patient_view import PatientView as BSPatientView
from bs.order_select import OrderSelect as BSOrderSelect
from bs.order_sign import OrderSign as BSOrderSign

from bp.hapi import Hapi as BPHapi
from bp.patient_view import PatientView as BPPatientView
from bp.order_select import OrderSelect as BPOrderSelect
from bp.order_sign import OrderSign as BPOrderSign

from bo.hapi import Hapi as BOHapi
from bo.fhir import Fhir as BOFhir

# Define the production topology using IoP 4.0+ API
prod = Production(
    name='CDSPKG.FoundationProduction',
    description='HL7 CDS Hooks server implementation',
    testing_enabled=True,
    log_general_trace_events=False,
)

# Define services
hapi_service = prod.service('Hapi', BSHapi)
patient_view_service = prod.service('PatientView', BSPatientView)
order_select_service = prod.service('OrderSelect', BSOrderSelect)
order_sign_service = prod.service('OrderSign', BSOrderSign)

# Define processes
hapi_process = prod.process('Hapi', BPHapi)
patient_view_process = prod.process('PatientView', BPPatientView)
order_select_process = prod.process('OrderSelect', BPOrderSelect)
order_sign_process = prod.process('OrderSign', BPOrderSign)

# Define operations
hapi_operation = prod.operation('Hapi', BOHapi)
fhir_operation = prod.operation('Fhir', BOFhir)


# Connect the conversion pipeline
prod.connect(hapi_service, hapi_process)

prod.connect(patient_view_service, patient_view_process)
prod.connect(order_select_service, order_select_process)
prod.connect(order_sign_service, order_sign_process)

prod.connect(patient_view_process.hapi_target, hapi_process)
prod.connect(patient_view_process.fhir_target, fhir_operation)
