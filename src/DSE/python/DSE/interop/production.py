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

from iop import Production

from bs.hapi import Hapi as BSHapi

from bp.hapi import Hapi as BPHapi

# Define the production topology using IoP 4.0+ API
prod = Production(
    name='DSEPKG.FoundationProduction',
    description='DSE - Decision Support Engine',
    testing_enabled=True,
    log_general_trace_events=False,
)

# Define services
hapi_service = prod.service('BS.Hapi', BSHapi)

# Define processes
hapi_process = prod.process('BP.Hapi', BPHapi)

# Define operations

# Connect the conversion pipeline
prod.connect(hapi_service.process_target, hapi_process)
