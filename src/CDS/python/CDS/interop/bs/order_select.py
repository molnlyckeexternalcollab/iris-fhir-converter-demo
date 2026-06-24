"""Business Service — order-select CDS hook."""

from iop import BusinessService
from CDS.interop.msg.cds_hooks import OrderSelectRequest, OrderSelectResponse


class OrderSelect(BusinessService):
    def on_process_input(self, message_input: OrderSelectRequest) -> OrderSelectResponse:
        response: OrderSelectResponse = self.send_request_sync('BP.OrderSelect', message_input)
        return response
