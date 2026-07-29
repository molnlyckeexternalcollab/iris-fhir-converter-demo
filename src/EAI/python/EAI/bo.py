"""Business Operations for FHIR conversion and HTTP interactions."""

import os
import json
from pathlib import Path

import iris
import requests
from liquid import FileSystemLoader
from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader

from iop import BusinessOperation

from EAI.msg import (
    FhirConverterMessage,
    FhirConverterResponse,
    FhirFileDropResponse,
    FhirRequest,
    FhirResponse,
    FHIRDataLoaderRequest
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

class FHIRDataLoaderOperation(BusinessOperation):
    """FHIR file import via HS.FHIRServer.Tools.DataLoader.

    Owns the destination effect: submitting FHIR files from a directory to the
    IRIS FHIR server. All SubmitResourceFiles parameters are exposed as production
    settings configurable from the UI.

    Overlap protection
    ------------------
    Uses the IRIS global specified by ``log_global`` + ``job_id`` to check whether
    the previous run is still "Running" before starting a new one. Works correctly
    with async multi-worker runs and survives IRIS restarts.
    When ``log_global`` is empty, overlap protection is disabled (safe for
    synchronous single-worker runs because SubmitResourceFiles then blocks).

    Statistics (when log_global is set)
    ------------------------------------
        @<log_global>@(<job_id>, "Status")              — Running / Complete / ERROR
        @<log_global>@(<job_id>, "FilesTotal")           — files processed
        @<log_global>@(<job_id>, "ResourcesTotal")       — resources submitted
        @<log_global>@(<job_id>, "ErrorCount")           — non-fatal errors
        @<log_global>@(<job_id>, "RunDuration")          — wall-clock time
        @<log_global>@(<job_id>, "ElapsedAvgPerFile")    — avg time per file
        @<log_global>@(<job_id>, "ElapsedAvgPerResource")
        (see HS.FHIRServer.Tools.DataLoader docs for full list)
    """

    # ------------------------------------------------------------------ settings

    input_directory: str = "/fhir-samples/references"
    """Folder to scan for FHIR JSON/NDJSON/XML files (absolute path inside the container)."""

    service_type: str = "HTTP"
    """
    "HTTP" (default) = cross-namespace load via a Service Registry HTTP service.
        Use this when the FHIR server is in a different namespace (e.g. FHIRSERVER).
    "FHIRServer" = direct in-process load — only works when running in the same
        namespace as the FHIR server. Faster but namespace-restricted.
    """

    service_name: str = "fhir-internal-webgateway"
    """
    For service_type="HTTP": name of the Service Registry HTTP service entry that
        points to the FHIR server endpoint.
        Licensed IRIS 2023.2+ has no private web server; register the entry with
        Host=webgateway Port=80 so that %Net.HttpRequest routes via the webgateway
        container (intra-Docker-network, no TLS overhead).
    For service_type="FHIRServer": the FHIR server endpoint path (e.g. /fhir/r4),
        only valid when running in the same namespace as the FHIR server.
    """

    file_limit: str = ""
    """Limit to the first N files per run. Empty string = no limit (pFileLimit)."""

    num_workers: int = 1
    """
    Number of parallel work queue jobs.
    1 (default) = synchronous — SubmitResourceFiles blocks until all files are loaded.
    >1 = async workers — method returns immediately; overlap is detected via log_global.
    """

    recursive: bool = False
    """Recurse into sub-directories of input_directory (pRecursive)."""

    clean_up: bool = False
    """
    WARNING: deletes the entire input_directory when the run completes (pCleanUp).
    Do NOT enable on a bind-mounted host directory unless you intend to delete it.
    """

    translate_table: str = "UTF8"
    """Character encoding of input files (pTranslateTable)."""

    log_global: str = "^EAIFHIRImport"
    """
    Name of the IRIS global used to record run statistics and status.
    Also used for overlap detection: a run is skipped if job_id still shows
    Status="Running" in this global.
    Set to "" to disable logging and overlap detection.
    """

    job_id: str = "EAIFHIRImport"
    """
    Fixed key written into log_global for each run (pJobId).
    Each run overwrites the previous stats, enabling reliable overlap detection
    across IRIS restarts. Change this to distinguish multiple import operations.
    """

    # ------------------------------------------------------------------ handler

    def on_message(self, request: FHIRDataLoaderRequest) -> None:
        """Triggered by FHIRDataLoaderService (scheduled or manual)."""
        status_obj = self._get_job_status()
        if status_obj is not None and status_obj._Get("status") == "Running":
            self.log_warning(
                f"Import job '{self.job_id}' is still running "
                f"(trigger={request.reason!r}) — skipping. "
                f"Progress so far: files={status_obj._Get('filesTotal')} "
                f"resources={status_obj._Get('resourcesTotal')} "
                f"elapsed={status_obj._Get('elapsedTotal')}s "
                f"started={status_obj._Get('started')}. "
                "Increase CallInterval or reduce file count / num_workers."
            )
            return

        if status_obj is not None:
            self._log_last_run_stats(status_obj)

        self.log_info(
            f"Starting FHIR file import (trigger={request.reason!r}) "
            f"dir='{self.input_directory}' service_type='{self.service_type}' "
            f"service_name='{self.service_name}' workers={self.num_workers} "
            f"recursive={self.recursive} clean_up={self.clean_up} "
            f"file_limit={self.file_limit!r}"
        )
        try:
            sc = iris.cls("HS.FHIRServer.Tools.DataLoader").SubmitResourceFiles(
                self.input_directory,   # pInputDirectory
                self.service_type,      # pServiceType  ("FHIRSERVER" | "HTTP")
                self.service_name,      # pServiceName
                1,                      # pDisplayProgress
                self.log_global,        # pLogGlobal    (stats + overlap tracking)
                self.file_limit,        # pFileLimit    ("" = no limit)
                self.translate_table,   # pTranslateTable
                self.num_workers,       # pNumWorkers
                self.job_id,            # pJobId        (user-specified fixed key)
                self.recursive,         # pRecursive
                self.clean_up,          # pCleanUp      (WARNING: deletes InputDirectory!)
                                        # pTransactionId omitted (internal use only)
            )
            if sc == 1:  # $$$OK
                self.log_info(f"FHIR file import completed (job='{self.job_id}').")
            else:
                self.log_warning(f"FHIR file import finished with status: {sc}")
        except Exception as exc:
            self.log_error(f"FHIR file import failed: {exc}")

    # ------------------------------------------------------------------ helpers

    def _get_job_status(self):
        """Return the DataLoader.Status() DynamicObject for job_id, or None on failure."""
        if not self.job_id:
            return None
        try:
            return iris.cls("HS.FHIRServer.Tools.DataLoader").Status(self.job_id)
        except Exception:
            return None

    def _log_last_run_stats(self, status_obj) -> None:
        """Log statistics from the previous completed DataLoader run."""
        try:
            job_status = status_obj._Get("status")
            if not job_status or job_status == "Not found":
                return
            self.log_info(
                f"Previous run '{self.job_id}': status={job_status} "
                f"files={status_obj._Get('filesTotal')} "
                f"resources={status_obj._Get('resourcesTotal')} "
                f"duration={status_obj._Get('runDuration')}s "
                f"errors={status_obj._Get('errorCount')}"
            )
        except Exception:
            pass
