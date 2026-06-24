"""Business Service — order-sign CDS hook."""

from iop import BusinessService
from CDS.interop.msg.cds_hooks import OrderSignRequest, OrderSignResponse


class OrderSign(BusinessService):
    def on_process_input(self, message_input: OrderSignRequest) -> OrderSignResponse:
        response: OrderSignResponse = self.send_request_sync('BP.OrderSign', message_input)
        return response
