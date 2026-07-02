"""
HL7 CDS Hooks server production.

Implements the HL7 CDS Hooks specification with Epic-specific nuances.
Receives hook requests and routes them through the IRIS production:

  BS.PatientView  → BP.PatientView  → BO.Fhir
  BS.OrderSelect  → BP.OrderSelect
  BS.OrderSign    → BP.OrderSign

Each Business Service is a thin bridge between the FastAPI WSGI layer and the
production message graph. Business Processes implement hook-specific logic
(prefetch resolution, card building). BO.Fhir handles outbound FHIR reads.

Decision support computation (risk scoring, DMN rules) can live in another namespace (e.g., DSE)
and be called over HTTP from the relevant Business Process.
"""

from iop import Production

from bs.patient_view import PatientView as BSPatientView
from bs.order_select import OrderSelect as BSOrderSelect
from bs.order_sign import OrderSign as BSOrderSign

from bp.patient_view import PatientView as BPPatientView
from bp.order_select import OrderSelect as BPOrderSelect
from bp.order_sign import OrderSign as BPOrderSign

from bo.fhir import Fhir as BOFhir
from bo.hapi import HttpOperation as BOHapiRisk

# Define the production topology using IoP 4.0+ API
prod = Production(
    name='CDSPKG.FoundationProduction',
    description='HL7 CDS Hooks server implementation',
    testing_enabled=True,
    log_general_trace_events=False,
)

# Define services
patient_view_service = prod.service('BS.PatientView', BSPatientView)
order_select_service = prod.service('BS.OrderSelect', BSOrderSelect)
order_sign_service = prod.service('BS.OrderSign', BSOrderSign)

# Define processes
patient_view_process = prod.process('BP.PatientView', BPPatientView)
order_select_process = prod.process('BP.OrderSelect', BPOrderSelect)
order_sign_process = prod.process('BP.OrderSign', BPOrderSign)

# Define operations
hapi_risk_operation = prod.operation('HapiRiskOperation', BOHapiRisk)
fhir_operation = prod.operation('BO.Fhir', BOFhir)

# Connect the conversion pipeline
prod.connect(patient_view_service.process_target, patient_view_process)
prod.connect(order_select_service.process_target, order_select_process)
prod.connect(order_sign_service.process_target, order_sign_process)

prod.connect(patient_view_process.hapi_risk_target, hapi_risk_operation)
prod.connect(patient_view_process.fhir_target, fhir_operation)
