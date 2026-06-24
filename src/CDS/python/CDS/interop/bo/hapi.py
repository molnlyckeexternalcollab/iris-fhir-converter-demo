"""Business Operation — HAPI HTTP outbound adapter.

Retained for backwards compatibility; the original BO placeholder
just returned "Not implemented". Will be extended when an outbound
HAPI/HTTP call is needed.
"""

from iop import BusinessOperation


class Hapi(BusinessOperation):
    def on_http_request(self, message_request: str) -> str:
        response: str = "Not implemented"
        return response
