"""Business Process — order-sign CDS hook orchestrator."""

from iop import BusinessProcess

from CDS.interop.msg.cds_hooks import OrderSignRequest, OrderSignResponse


class OrderSign(BusinessProcess):
    def on_order_sign_request_message(
        self, request: OrderSignRequest
    ) -> OrderSignResponse:
        # TODO Phase 1: implement orchestration
        raise NotImplementedError("OrderSign BP not yet implemented")
