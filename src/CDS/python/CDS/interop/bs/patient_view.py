"""Business Service — patient-view CDS hook."""

from iop import BusinessService, Director
from CDS.routers.contexts import PatientViewHookInput
from CDS.interop.msg.cds_hooks import PatientViewInputRequest, PatientViewResponse

_bs = None


def get_bs():
    global _bs
    if _bs is None:
        _bs = Director.create_python_business_service('PatientView')
    return _bs


class PatientView(BusinessService):
    def on_process_input(self, message_input: PatientViewHookInput) -> PatientViewResponse:
        msg = PatientViewInputRequest(input=message_input)
        response: PatientViewResponse = self.send_request_sync('PatientView', msg)
        return response
