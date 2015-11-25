import json
import unittest

from crassus.deployment_response import DeploymentResponse
from crassus.output_converter import OutputConverter
from mock import call, patch
from utils import load_fixture_json

cfn_event = load_fixture_json('cfn_event.json')
cfn_event_different_termination = load_fixture_json(
    'cfn_event_different_termination.json')


class TestOutputConverter(unittest.TestCase):

    """
    Tests for OutputConverter.
    """

    def setUp(self):
        self.event = cfn_event
        self.context = {}
        self.output_converter = OutputConverter(self.event, self.context)

        # Patch get_lambda_config_property
        self.patch_getconfig = patch(
            'crassus.output_converter.get_lambda_config_property')
        self.mock_getconfig = self.patch_getconfig.start()
        self.mock_getconfig.return_value = ['OUTPUT-SQS-QUEUE-1']

        # Patch logger
        self.patch_logger = patch('crassus.output_converter.logger')
        self.mock_logger = self.patch_logger.start()

        # Patch sqs_send_message
        self.patch_sqs_send = patch(
            'crassus.output_converter.sqs_send_message')
        self.mock_sqs_send = self.patch_sqs_send.start()

    def teardown(self):
        self.patch_getconfig.stop()
        self.patch_logger.stop()
        self.patch_sqs_send.stop()

    def test_cast_type_string(self):
        """
        _cast_type() should return string if the input is not a valid
        JSON.
        """
        invalid_json = '{foo'
        return_value = self.output_converter._cast_type(invalid_json)
        self.assertEqual(return_value, invalid_json)

    def test_cast_type_json(self):
        """
        _cast_type() should return a python type if the input is a valid
        JSON.
        """
        valid_json = '{"foo":"bar"}'
        return_value = self.output_converter._cast_type(valid_json)
        self.assertEqual(return_value, json.loads(valid_json))

    def test_parser_parses_correctly(self):
        """
        Test if the input event is parsed correctly.

        We only check parts of the input event, which implies it was
        parsed properly.
        """
        return_value = self.output_converter._parse_sns_message(
            self.event['Records'][0]['Sns']['Message'])
        self.assertEqual(return_value['ResourceStatus'], 'CREATE_IN_PROGRESS')
        self.assertEqual(return_value['Namespace'], 123456789012)
        self.assertEqual(return_value['StackName'], 'crassus-karolyi-temp1')
        self.assertNotEqual(
            return_value['StackName'], 'crassus-karolyi-temp1garbage')
        self.assertEqual(return_value['ResourceProperties'], {
            'Action': 'lambda:invokeFunction',
            'SourceArn':
                'arn:aws:sns:eu-west-1:123456789012:crassus-karolyi-temp1-'
                'cfnOutputSnsTopic-KKF3Y90CS6SA',
            'FunctionName':
                'crassus-karolyi-temp1-cfnOutputConverterFunction-'
                '7T8X9HH83YRH',
            'Principal': 'sns.amazonaws.com'})

    def test_different_termination_parsed(self):
        """
        Test if the input event is parsed correctly. In this test, the
        message parameter does not have a "'\n" termination at the end
        of it, yet the parser parses the last parameter correctly.

        We only check parts of the input event, which implies it was
        parsed properly.
        """
        return_value = self.output_converter._parse_sns_message(
            cfn_event_different_termination['Records'][0]['Sns']['Message'])
        self.assertEqual(return_value['ResourceStatus'], 'CREATE_IN_PROGRESS')
        self.assertEqual(return_value['Namespace'], 123456789012)
        # All hail the successful parsing, last parameter is StackName!
        self.assertEqual(return_value['StackName'], 'crassus-karolyi-temp1')
        # ... and the value should NOT have a closing quote.
        self.assertNotEqual(
            return_value['StackName'], 'crassus-karolyi-temp1\'')
        self.assertEqual(return_value['ResourceProperties'], {
            'Action': 'lambda:invokeFunction',
            'SourceArn':
                'arn:aws:sns:eu-west-1:123456789012:crassus-karolyi-temp1-'
                'cfnOutputSnsTopic-KKF3Y90CS6SA',
            'FunctionName':
                'crassus-karolyi-temp1-cfnOutputConverterFunction-'
                '7T8X9HH83YRH',
            'Principal': 'sns.amazonaws.com'})

    def test_converts_correctly(self):
        """
        convert() should call and initialize the right
        functions/objects.
        """
        self.output_converter.convert()
        self.assertEqual(self.mock_logger.warning.call_count, 0)
        self.mock_sqs_send.assert_called_once_with(
            ['OUTPUT-SQS-QUEUE-1'], {
                'status': 'CREATE_IN_PROGRESS',
                'timestamp': '2015-11-23T16:53:46.443Z',
                'stackName': 'crassus-karolyi-temp1',
                'version': '1.1',
                'message': 'Resource creation Initiated',
                'emitter': 'cloudformation',
                'resourceType': 'AWS::Lambda::Permission'})
        deployment_parameter = self.mock_sqs_send.call_args[0][1]
        self.assertIs(type(deployment_parameter), DeploymentResponse)

    def test_skips_empty_messages(self):
        """
        If there is no 'Sns' or 'Message' in the received event list,
        log a warning.
        """
        self.output_converter.event = {'Records': [{}, {'foo': 1}]}
        self.output_converter.convert()
        self.assertFalse(self.mock_sqs_send.called)
        self.assertEqual(list(self.mock_logger.warning.call_args_list), [
            call('No \'Sns\' or \'Message\' in received event: {}'),
            call('No \'Sns\' or \'Message\' in received event: {\'foo\': 1}')])
