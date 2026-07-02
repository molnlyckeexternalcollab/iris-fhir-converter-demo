"""Business Operations for FHIR conversion and HTTP interactions."""

import os
import json
from pathlib import Path

import requests
from liquid import FileSystemLoader
from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader

from iop import BusinessOperation

from EAI.msg import (
    FhirConverterMessage,
    FhirConverterResponse,
    FhirFileDropResponse,
    FhirRequest,
    FhirResponse
)

from DSE.models import RiskCalculationResult
from DSE.interop.msg import RiskAssessmentInputRequest, RiskAssessmentResultResponse

class FhirConverterOperation(BusinessOperation):
    """Converts HL7v2 messages to FHIR using Liquid templates."""

    def on_init(self) -> None:
        """Initialize template renderer."""
        self._init_template_path()
        self._init_renderer()

    def _init_template_path(self) -> None:
        """Initialize and validate template path."""
        if not hasattr(self, 'template_path'):
            default_path = os.path.join(
                os.environ.get('APP_HOME', '/app'),
                'templates'
            )
            self.log_warning(
                f'template_path not configured. Using default: {default_path}. '
                'Set %settings "template_path" to suppress this warning.'
            )
            self.template_path = default_path

        if not os.path.isdir(self.template_path):
            raise ValueError(
                f'Template path does not exist: {self.template_path}'
            )

    def _init_renderer(self) -> None:
        """Initialize Liquid template renderer."""
        try:
            self.renderer = Hl7v2Renderer(
                env=make_environment(
                    loader=FileSystemLoader(
                        search_path=self.template_path,
                        ext=".liquid"
                    ),
                    additional_loaders=[hl7v2_default_loader],
                )
            )
            self.log_info(f'Renderer initialized with templates: {self.template_path}')
        except Exception as e:
            raise RuntimeError(
                f'Failed to initialize template renderer: {str(e)}'
            )

    def on_fhir_converter_message(
        self,
        request: FhirConverterMessage
    ) -> FhirConverterResponse:
        """
        Convert HL7v2 message to FHIR Bundle.
        
        Args:
            request: FhirConverterMessage with HL7 data
            
        Returns:
            FhirConverterResponse with converted FHIR Bundle
            
        Raises:
            Exception: If conversion fails
        """
        try:
            self.log_info(
                f'Converting {request.input_filename} '
                f'(template: {request.root_template})'
            )

            # Render FHIR from HL7 template
            output_data = self.renderer.render_fhir_string(
                request.root_template,
                request.input_data
            )

            self.log_info(
                f'Successfully converted {request.input_filename} '
                f'→ {len(output_data)} bytes'
            )

            return FhirConverterResponse(
                status=200,
                output_data=output_data,
                output_filename=request.input_filename.replace('.hl7', '.json')
            )
        except Exception as e:
            self.log_error(f'Conversion failed: {str(e)}')
            raise

class FhirFileDropOperation(BusinessOperation):
    """Drops converted FHIR payloads to filesystem."""

    output_dir: str = ''

    def on_init(self) -> None:
        """Initialize output directory."""
        if not self.output_dir:
            app_home = os.getenv('APP_HOME', os.getcwd())
            self.output_dir = str(Path(app_home) / 'misc' / 'data' / 'fhir')

    def on_fhir_converter_response(
        self,
        msg: FhirConverterResponse
    ) -> FhirFileDropResponse:
        """Write converted payload to data/fhir folder."""
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / msg.output_filename
        file_path.write_text(msg.output_data, encoding='utf-8')
        self.log_info(f'Dropped converted FHIR file: {file_path}')

        return FhirFileDropResponse(status=200, file_path=str(file_path))

class HttpOperation(BusinessOperation):
    # Direct IRIS port — bypasses webgateway, no TLS for internal calls
    url = 'http://localhost:52773/dse/hapi'

    def on_risk_assessment_input_request(self, request: RiskAssessmentInputRequest) -> RiskAssessmentResultResponse:
        response = requests.post(
            self.url,
            json=json.loads(request.input.model_dump_json()),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        result = RiskCalculationResult.model_validate(response.json())
        return RiskAssessmentResultResponse(result=result)

class FhirHttpOperation(BusinessOperation):
    """Posts FHIR resources to FHIR server via HTTP."""

    url: str = 'http://localhost:52773/fhir/r4'
    credential: str = 'SuperUser'

    def on_init(self) -> None:
        """Initialize HTTP session with credentials."""
        self.session = requests.Session()
        self.session.auth = self._get_credentials()
        self.log_info(
            f'FhirHttpOperation initialized: {self.url} '
            f'(auth: {self.credential})'
        )

    def _get_credentials(self) -> tuple:
        """
        Get HTTP Basic Auth credentials.
        
        Returns:
            (username, password) tuple
        """
        if self.credential == 'SuperUser':
            return ('SuperUser', 'SYS')
        return ('', '')

    def on_fhir_request(self, msg: FhirRequest) -> FhirResponse:
        """
        Submit FHIR request to server.
        
        Args:
            msg: FhirRequest with resource and method
            
        Returns:
            FhirResponse with server response
            
        Raises:
            Exception: If request fails or response contains errors
        """
        try:
            # Construct full URI
            base_url = msg.url or self.url
            uri = base_url.rstrip('/') + '/' + msg.resource.lstrip('/')

            self.log_info(f'FHIR {msg.method} {uri}')

            # Execute request
            response = self.session.request(
                method=msg.method,
                url=uri,
                data=msg.data,
                headers=msg.headers,
                timeout=60,
                verify=False
            )
            response.raise_for_status()

            # Validate bundle response entries
            self._validate_bundle_response(response)

            self.log_info(f'FHIR {msg.method} successful: {response.status_code}')
            return FhirResponse(
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                resource=msg.resource
            )
        except Exception as e:
            self.log_error(f'FHIR {msg.method} failed: {str(e)}')
            raise

    @staticmethod
    def _validate_bundle_response(response) -> None:
        """
        Validate FHIR Bundle response entries for errors.
        
        Args:
            response: HTTP response object
            
        Raises:
            Exception: If any Bundle entry has error status
        """
        try:
            data = response.json()
            if data.get('resourceType') != 'Bundle':
                return

            for entry in data.get('entry', []):
                entry_response = entry.get('response', {})
                status = entry_response.get('status', '')
                
                # Check for error status codes
                if status and not status.startswith(('200', '201')):
                    raise Exception(
                        f'Bundle entry error: {status} - {entry_response}'
                    )
        except ValueError:
            # Not JSON, skip validation
            pass