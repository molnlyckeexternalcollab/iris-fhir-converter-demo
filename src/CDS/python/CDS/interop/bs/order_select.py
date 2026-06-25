"""Business Service — order-select CDS hook."""

from iop import BusinessService, Director
from CDS.interop.msg.cds_hooks import OrderSelectRequest, OrderSelectResponse
from CDS.routers.contexts import OrderSelectHookInput

_bs = None


def get_bs():
    global _bs
    if _bs is None:
        _bs = Director.create_python_business_service('BS.OrderSelect')
    return _bs


class OrderSelect(BusinessService):
    def on_process_input(self, message_input: OrderSelectHookInput) -> OrderSelectResponse:
        msg = OrderSelectRequest(input=message_input)
        response: OrderSelectResponse = self.send_request_sync('BP.OrderSelect', msg)
        return response
