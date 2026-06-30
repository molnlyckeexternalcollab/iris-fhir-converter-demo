"""Business Service — order-sign CDS hook."""

from iop import BusinessService, Director, target
from CDS.interop.msg.cds_hooks import OrderSignRequest, OrderSignResponse
from CDS.routers.contexts import OrderSignHookInput

_bs = None


def get_bs():
    global _bs
    if _bs is None:
        _bs = Director.create_python_business_service('OrderSign')
    return _bs


class OrderSign(BusinessService):
    
    process_target = target('Process')

    def on_process_input(self, message_input: OrderSignHookInput) -> OrderSignResponse:
        msg = OrderSignRequest(input=message_input)
        response: OrderSignResponse = self.send_request_sync(self.process_target, msg)
        return response
