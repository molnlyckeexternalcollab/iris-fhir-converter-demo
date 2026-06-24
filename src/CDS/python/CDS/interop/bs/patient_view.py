"""Business Service — patient-view CDS hook."""

from iop import BusinessService
from CDS.interop.msg.cds_hooks import PatientViewRequest, PatientViewResponse


class PatientView(BusinessService):
    def on_process_input(self, message_input: PatientViewRequest) -> PatientViewResponse:
        response: PatientViewResponse = self.send_request_sync('BP.PatientView', message_input)
        return response
