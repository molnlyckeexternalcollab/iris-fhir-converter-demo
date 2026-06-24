"""Business Process — order-select CDS hook orchestrator."""

from iop import BusinessProcess

from CDS.interop.msg.cds_hooks import OrderSelectRequest, OrderSelectResponse


class OrderSelect(BusinessProcess):
    def on_order_select_request_message(
        self, request: OrderSelectRequest
    ) -> OrderSelectResponse:
        # TODO Phase 1: implement orchestration
        raise NotImplementedError("OrderSelect BP not yet implemented")
