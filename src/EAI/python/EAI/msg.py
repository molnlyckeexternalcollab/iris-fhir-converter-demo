"""Message definitions for FHIR conversion pipeline.

All messages are dataclass-based for serialization and type safety.
"""

from dataclasses import dataclass, field
from typing import Optional

from iop import Message

@dataclass
class FhirConverterMessage(Message):
    """Request to convert HL7v2 message to FHIR."""
    input_filename: str
    input_data: str
    input_data_type: str = 'Hl7v2'
    root_template: str = 'ADT_CUSTOM'


@dataclass
class FhirConverterResponse(Message):
    """Response containing converted FHIR Bundle."""
    status: int
    output_data: str
    output_filename: str


@dataclass
class FhirFileDropResponse(Message):
    """Response containing the created file path for dropped FHIR payload."""
    status: int
    file_path: str


@dataclass
class FhirRequest(Message):
    """HTTP request to FHIR server."""
    url: Optional[str] = None
    resource: Optional[str] = None
    method: str = 'POST'
    data: str = ''
    headers: dict = field(default_factory=dict)


@dataclass
class FhirResponse(Message):
    """HTTP response from FHIR server."""
    status_code: int
    content: str
    headers: dict = field(default_factory=dict)
    resource: str = ''