"""Unit tests for FhirConverterProcess business process.

Tests the HL7v2 message handling and FHIR conversion pipeline.
"""

import os
from unittest.mock import MagicMock, Mock, patch, call
import pytest

from EAI.bp import FhirConverterProcess
from EAI.msg import FhirConverterMessage, FhirConverterResponse, FhirRequest


class TestFhirConverterProcess:
    """Test suite for FhirConverterProcess."""

    @pytest.fixture
    def process(self):
        """Create a FhirConverterProcess instance with mocked base class."""
        process = FhirConverterProcess()
        # Mock inherited methods from BusinessProcess
        process.log_info = Mock()
        process.log_error = Mock()
        process.log_warning = Mock()
        process.send_request_sync = Mock()
        return process

    @pytest.fixture
    def hl7_message(self):
        """Create a mock IRIS HL7 message."""
        msg = Mock(spec=['Source', 'RawContent', 'Name'])
        msg.Source = '/app/misc/data/input/patient_adm.hl7'
        msg.RawContent = (
            'MSH|^~\\&|SENDING_APP|SENDING_FAC|REC_APP|REC_FAC|'
            '20240101120000||ADT^A01|123456|P|2.8\r'
            'EVN|A01|20240101120000\r'
            'PID|1||12345^^^MRN||DOE^JOHN||19800101|M'
        )
        msg.Name = 'ADT_Z99'
        return msg

    @pytest.fixture
    def converter_response(self):
        """Create a mock FhirConverterResponse."""
        return FhirConverterResponse(
            status=200,
            output_data='{"resourceType":"Bundle","entry":[]}',
            output_filename='patient_adm.json'
        )

    # ========== on_enslib_message Tests ==========

    def test_on_enslib_message_success(self, process, hl7_message, converter_response):
        """Test successful HL7 message processing."""
        # Setup
        process.send_request_sync.return_value = converter_response
        process.submit_fhir_converter_message = Mock()

        # Execute
        process.on_enslib_message(hl7_message)

        # Verify
        assert process.submit_fhir_converter_message.called
        call_args = process.submit_fhir_converter_message.call_args[0][0]
        assert isinstance(call_args, FhirConverterMessage)
        assert call_args.input_filename == 'patient_adm.hl7'
        assert call_args.input_data_type == 'Hl7v2'
        assert call_args.root_template == 'ADT_Z99'

    def test_on_enslib_message_extracts_filename(self, process, hl7_message):
        """Test that filename is correctly extracted from Source."""
        # Setup
        process.submit_fhir_converter_message = Mock()
        hl7_message.Source = '/path/to/test_message.hl7'

        # Execute
        process.on_enslib_message(hl7_message)

        # Verify
        call_args = process.submit_fhir_converter_message.call_args[0][0]
        assert call_args.input_filename == 'test_message.hl7'

    def test_on_enslib_message_preserves_raw_content(self, process, hl7_message):
        """Test that raw HL7 content is preserved."""
        # Setup
        process.submit_fhir_converter_message = Mock()
        test_content = 'MSH|^~\\&|TEST|APP|REC|FAC|20240101||ADT^A01'
        hl7_message.RawContent = test_content

        # Execute
        process.on_enslib_message(hl7_message)

        # Verify
        call_args = process.submit_fhir_converter_message.call_args[0][0]
        assert call_args.input_data == test_content

    def test_on_enslib_message_preserves_message_type(self, process, hl7_message):
        """Test that HL7 message type (template name) is preserved."""
        # Setup
        process.submit_fhir_converter_message = Mock()
        hl7_message.Name = 'ORM_O01'

        # Execute
        process.on_enslib_message(hl7_message)

        # Verify
        call_args = process.submit_fhir_converter_message.call_args[0][0]
        assert call_args.root_template == 'ORM_O01'

    def test_on_enslib_message_error_handling(self, process, hl7_message):
        """Test error handling when processing fails."""
        # Setup - patch the method on the instance
        with patch.object(process, 'submit_fhir_converter_message', side_effect=ValueError('Processing error')):
            # Execute & Verify
            with pytest.raises(ValueError):
                process.on_enslib_message(hl7_message)

            # Verify error was logged
            assert process.log_error.called
            log_msg = process.log_error.call_args[0][0]
            assert 'Failed to process HL7 message' in log_msg
            assert 'Processing error' in log_msg

    def test_on_enslib_message_with_missing_source(self, process, hl7_message):
        """Test handling when Source attribute is missing or None."""
        # Setup
        process.submit_fhir_converter_message = Mock()
        hl7_message.Source = None

        # Execute - should raise TypeError when os.path.basename receives None
        with pytest.raises(TypeError):
            process.on_enslib_message(hl7_message)

    # ========== submit_fhir_converter_message Tests ==========

    def test_submit_fhir_converter_message_basic_flow(
        self, process, converter_response
    ):
        """Test basic flow: normalize template, convert, and post to FHIR."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_Z99'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify template was normalized to ADT_CUSTOM
        assert request.root_template == 'ADT_CUSTOM'

        # Verify send_request_sync was called 3 times (converter + file + FHIR)
        assert process.send_request_sync.call_count == 3

        # Verify first call: convert HL7 to FHIR
        first_call = process.send_request_sync.call_args_list[0]
        assert first_call[0][0] == process.converter_target
        assert isinstance(first_call[0][1], FhirConverterMessage)

        # Verify second call: drop converted file
        second_call = process.send_request_sync.call_args_list[1]
        assert second_call[0][0] == process.file_target
        assert isinstance(second_call[0][1], FhirConverterResponse)

        # Verify third call: post to FHIR
        third_call = process.send_request_sync.call_args_list[2]
        assert third_call[0][0] == process.fhir_target
        fhir_request = third_call[0][1]
        assert isinstance(fhir_request, FhirRequest)

    def test_submit_sends_file_drop_operation(self, process, converter_response):
        """Test converted payload is routed to dedicated file-drop operation."""
        request = FhirConverterMessage(
            input_filename='drop_test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        process.submit_fhir_converter_message(request)

        second_call = process.send_request_sync.call_args_list[1]
        assert second_call[0][0] == process.file_target
        dropped_msg = second_call[0][1]
        assert isinstance(dropped_msg, FhirConverterResponse)
        assert dropped_msg.output_filename == 'drop_test.json'

    def test_submit_normalizes_adtz99_to_adtcustom(self, process, converter_response):
        """Test that ADT_Z99 template is normalized to ADT_CUSTOM."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_Z99'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify
        assert request.root_template == 'ADT_CUSTOM'

    def test_submit_preserves_other_templates(self, process, converter_response):
        """Test that other templates are not modified."""
        # Setup
        for template in ['ORU_R01', 'ADT_A01', 'ORM_O01', 'ADT_CUSTOM']:
            request = FhirConverterMessage(
                input_filename='test.hl7',
                input_data='MSH|...',
                input_data_type='Hl7v2',
                root_template=template
            )
            process.send_request_sync.return_value = converter_response

            # Execute
            process.submit_fhir_converter_message(request)

            # Verify
            assert request.root_template == template

    def test_submit_converter_call_parameters(self, process, converter_response):
        """Test converter operation is called with correct parameters."""
        # Setup
        request = FhirConverterMessage(
            input_filename='patient.hl7',
            input_data='MSH|^~\\&|SOURCE|FAC|REC|FAC|20240101||ADT',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify converter was called with original request
        converter_call = process.send_request_sync.call_args_list[0]
        converter_request = converter_call[0][1]
        assert converter_request.input_filename == 'patient.hl7'
        assert converter_request.input_data_type == 'Hl7v2'
        assert converter_request.root_template == 'ADT_CUSTOM'

    def test_submit_updates_output_filename(self, process, converter_response):
        """Test that output filename is updated from .hl7 to .json."""
        # Setup
        request = FhirConverterMessage(
            input_filename='patient_data.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify filename was updated in response
        assert converter_response.output_filename == 'patient_data.json'

    def test_submit_fhir_request_structure(self, process, converter_response):
        """Test that FHIR HTTP request has correct structure."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify FHIR request parameters
        fhir_call = process.send_request_sync.call_args_list[2]
        fhir_request = fhir_call[0][1]

        assert fhir_request.url == 'https://webgateway'
        assert fhir_request.resource == 'fhir/r4/'
        assert fhir_request.method == 'POST'
        assert fhir_request.data == converter_response.output_data
        assert fhir_request.headers['Accept'] == 'application/json'
        assert fhir_request.headers['Content-Type'] == 'application/json+fhir'

    def test_submit_logging(self, process, converter_response):
        """Test that conversion progress is logged."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        converter_response.output_filename = 'test.json'
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify logging
        assert process.log_info.called
        log_calls = [call[0][0] for call in process.log_info.call_args_list]
        assert any('test.hl7' in log and 'test.json' in log for log in log_calls)

    def test_submit_handles_converter_error(self, process):
        """Test error handling when converter fails."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.side_effect = RuntimeError('Conversion failed')

        # Execute & Verify
        with pytest.raises(RuntimeError):
            process.submit_fhir_converter_message(request)

    def test_submit_handles_fhir_post_error(self, process, converter_response):
        """Test error handling when FHIR POST fails."""
        # Setup
        request = FhirConverterMessage(
            input_filename='test.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        # First call succeeds (converter), second call fails (FHIR POST)
        process.send_request_sync.side_effect = [
            converter_response,
            Mock(status=200),
            RuntimeError('FHIR server error')
        ]

        # Execute & Verify
        with pytest.raises(RuntimeError):
            process.submit_fhir_converter_message(request)

    # ========== Message Message Properties Tests ==========

    def test_message_properties_preserved_through_pipeline(
        self, process, converter_response
    ):
        """Test all message properties are preserved through conversion."""
        # Setup
        original_filename = 'comprehensive_test.hl7'
        original_data = 'MSH|^~\\&|ORIG|FAC|REC|FAC|20240101120000||ADT^A01'
        request = FhirConverterMessage(
            input_filename=original_filename,
            input_data=original_data,
            input_data_type='Hl7v2',
            root_template='ADT_A01'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify converter call preserves all properties
        converter_call = process.send_request_sync.call_args_list[0]
        msg_arg = converter_call[0][1]
        assert msg_arg.input_filename == original_filename
        assert msg_arg.input_data == original_data

    def test_response_filename_transformation(self, process, converter_response):
        """Test .hl7 to .json filename transformation."""
        # Setup with various filename patterns
        test_cases = [
            ('simple.hl7', 'simple.json'),
            ('patient_201.hl7', 'patient_201.json'),
            ('ADT.hl7', 'ADT.json'),
            ('file.with.dots.hl7', 'file.with.dots.json'),
        ]

        for input_file, expected_output in test_cases:
            request = FhirConverterMessage(
                input_filename=input_file,
                input_data='MSH|...',
                input_data_type='Hl7v2',
                root_template='ADT_CUSTOM'
            )
            process.send_request_sync.return_value = converter_response

            # Execute
            process.submit_fhir_converter_message(request)

            # Verify
            assert converter_response.output_filename == expected_output

    # ========== Integration Tests ==========

    def test_full_message_flow_multiple_calls(self, process, converter_response):
        """Test processing multiple messages in sequence."""
        # Setup
        messages = [
            FhirConverterMessage(
                input_filename=f'msg_{i}.hl7',
                input_data=f'MSH|...|{i}',
                input_data_type='Hl7v2',
                root_template='ADT_CUSTOM'
            )
            for i in range(3)
        ]
        process.send_request_sync.return_value = converter_response

        # Execute
        for msg in messages:
            process.submit_fhir_converter_message(msg)

        # Verify all messages processed
        assert process.send_request_sync.call_count == 9  # 3 calls per message

    def test_target_attributes_exist(self, process):
        """Test that target attributes are properly initialized."""
        # Verify target attributes exist
        assert hasattr(process, 'converter_target')
        assert hasattr(process, 'file_target')
        assert hasattr(process, 'fhir_target')

    def test_process_inheritance(self):
        """Test that FhirConverterProcess inherits from BusinessProcess."""
        from iop import BusinessProcess
        assert issubclass(FhirConverterProcess, BusinessProcess)

    # ========== Edge Cases ==========

    def test_submit_with_empty_hl7_data(self, process, converter_response):
        """Test handling of empty HL7 data."""
        # Setup
        request = FhirConverterMessage(
            input_filename='empty.hl7',
            input_data='',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute - should process even with empty data
        process.submit_fhir_converter_message(request)

        # Verify converter was still called
        assert process.send_request_sync.called

    def test_submit_with_special_characters_in_filename(
        self, process, converter_response
    ):
        """Test handling of special characters in filename."""
        # Setup
        request = FhirConverterMessage(
            input_filename='patient-data_2024-01-15.hl7',
            input_data='MSH|...',
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify output filename transformation
        assert converter_response.output_filename == 'patient-data_2024-01-15.json'

    def test_submit_with_large_hl7_payload(self, process, converter_response):
        """Test handling of large HL7 payload."""
        # Setup - create large HL7 message (10KB)
        large_payload = 'MSH|...' + ('SEGMENT|DATA|' * 1000)
        request = FhirConverterMessage(
            input_filename='large.hl7',
            input_data=large_payload,
            input_data_type='Hl7v2',
            root_template='ADT_CUSTOM'
        )
        process.send_request_sync.return_value = converter_response

        # Execute
        process.submit_fhir_converter_message(request)

        # Verify processing succeeded
        assert process.send_request_sync.call_count == 3
