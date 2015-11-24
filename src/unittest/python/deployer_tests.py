import unittest
from textwrap import dedent

from botocore.exceptions import ClientError
from crassus.deployer import (
    NOTIFICATION_SUBJECT, Crassus, StackUpdateParameter)
from crassus.deployment_response import DeploymentResponse
from mock import ANY, Mock, call, patch

PARAMETER = 'ANY_PARAMETER'
ARN_ID = 'ANY_ARN'
STACK_NAME = 'ANY_STACK'
ANY_TOPIC = ['ANY_TOPIC']

CRASSUS_CFN_PARAMETERS = [
    {
        "updateParameterKey": "ANY_NAME1",
        "updateParameterValue": "ANY_VALUE1"
    },
    {
        "updateParameterKey": "ANY_NAME2",
        "updateParameterValue": "ANY_VALUE2"
    }
]

SAMPLE_EVENT = {
    'Records': [
        {
            'EventVersion': '1.0',
            'EventSubscriptionArn': '<SUBSCRIPTION ARN>',
            'EventSource': 'aws: sns',
            'Sns': {
                'SignatureVersion': '1',
                'Timestamp': '2015-10-23T11: 01: 16.140Z',
                'Signature': '<SIGNATURE>',
                'SigningCertUrl': '<SIGNING URL>',
                'MessageId': '<MESSAGE ID>',
                'Message': '{"version": "1", '
                           '"stackName": "ANY_STACK", '
                           '"region": "eu-west-1", '
                           '"parameters": '
                '[{"updateParameterKey": "ANY_NAME1", '
                '"updateParameterValue": "ANY_VALUE1"}, '
                '{"updateParameterKey": "ANY_NAME2", '
                '"updateParameterValue": "ANY_VALUE2"}]}',
                'MessageAttributes': {
                },
                'Type': 'Notification',
                'UnsubscribeUrl': '<UNSUBSCRIBE URL>',
                'TopicArn': '<TOPIC ARN>',
                'Subject': None
            }
        }
    ]
}


class TestDeployStack(unittest.TestCase):

    @patch('crassus.deployer.Crassus.load')
    @patch('crassus.deployer.Crassus.update')
    def test_should_call_all_necessary_stuff(self, load_mock, update_mock):
        crassus = Crassus(None, None)
        crassus.deploy()
        load_mock.assert_called_once_with()
        update_mock.assert_called_once_with()


class TestParseParameters(unittest.TestCase):

    def setUp(self):
        self.crassus = Crassus(SAMPLE_EVENT, None)

    def test_parse_valid_event(self):

        self.assertEqual(self.crassus.stack_update_parameters.stack_name,
                         STACK_NAME)


class TestNotify(unittest.TestCase):
    STATUS = 'success'
    MESSAGE = 'ANY MESSAGE'

    @patch('crassus.deployer.sqs_send_message')
    @patch('boto3.resource')
    def test_should_notify_sns(self, resource_mock, mock_sqs):
        topic_mock = Mock()
        sns_mock = Mock()
        sns_mock.Topic.return_value = topic_mock
        resource_mock.return_value = sns_mock

        self.crassus = Crassus(None, None)
        self.crassus._stack_name = STACK_NAME
        self.crassus._output_topics = ANY_TOPIC

        self.crassus.notify(self.STATUS, self.MESSAGE)

        self.assertEquals(mock_sqs.call_count, 1)
        self.assertEquals(
            mock_sqs.call_args,
            call(['ANY_TOPIC'], {
                'status': 'success',
                'timestamp': ANY,
                'stackName': 'ANY_STACK',
                'version': '1.1',
                'message': 'ANY MESSAGE',
                'emitter': 'crassus'}))

    @patch('crassus.deployer.Crassus.output_topics', None)
    def test_should_do_gracefully_nothing(self):
        self.crassus = Crassus(None, None)
        self.crassus.notify('status', 'message')


class TestUpdateStack(unittest.TestCase):

    def setUp(self):
        self.stack_mock = Mock()
        self.stack_mock.parameters = [
            {"ParameterKey": "KeyOne",
             "ParameterValue": "OriginalValueOne",
             },
            {"ParameterKey": "KeyTwo",
             "ParameterValue": "OriginalValueTwo",
             }
        ]

        self.update_parameters = {
            "version": 1,
            "stackName": "ANY_STACK",
            "region": "ANY_REGION",
            "parameters":
                {"KeyOne": "UpdateValueOne"},
        }

        self.expected_parameters = [
            {"ParameterKey": "KeyOne",
             "ParameterValue": "UpdateValueOne",
             },
            {"ParameterKey": "KeyTwo",
             "UsePreviousValue": True
             }
        ]
        self.context_mock = Mock(invoked_function_arn="any_arn",
                                 function_version="any_version")
        self.crassus = Crassus(None, self.context_mock)
        self.crassus._stack_update_parameters = \
            StackUpdateParameter(self.update_parameters)
        self.crassus.stack = self.stack_mock
        self.crassus._stack_name = STACK_NAME
        self.crassus._output_topics = ANY_TOPIC
        self.crassus.aws_lambda = Mock()
        self.crassus.aws_lambda.get_function_configuration.return_value = {
            'Description': dedent("""
                {"result_queue":[
                    "arn:aws:sns:eu-west-1:123456789012:crassus-output",
                    "arn:aws:sns:eu-west-1:123456789012:random-topic"
                    ],
                    "cfn_events": ["CFN-SNS-TOPIC-1"]}""")}

    @patch('crassus.deployer.Crassus.notify', Mock())
    @patch('crassus.deployer.get_lambda_config_property')
    def test_update_stack_should_call_update(self, mock_lambda):
        mock_lambda.return_value = ['CFN-SQS-QUEUE-1']
        self.crassus.update()
        self.stack_mock.update.assert_called_once_with(
            UsePreviousTemplate=True,
            Parameters=self.expected_parameters,
            Capabilities=['CAPABILITY_IAM'],
            NotificationARNs=['CFN-SQS-QUEUE-1'])
        self.assertEqual(self.crassus.cfn_output_topics, ['CFN-SQS-QUEUE-1'])

    @patch('crassus.deployer.get_lambda_config_property', Mock())
    @patch('crassus.deployer.Crassus.notify', Mock())
    @patch('crassus.deployer.logger')
    def test_update_stack_load_throws_clienterror_exception(self, logger_mock):
        self.stack_mock.update.side_effect = ClientError(
            {'Error': {'Code': 'ExpectedException', 'Message': ''}},
            'test_deploy_stack_should_notify_error_in_case_of_client_error')
        self.crassus.update()
        logger_mock.error.assert_called_once_with(ANY)

    """@patch('crassus.deployer.notify')
    def test_update_stack_should_notify_in_case_of_error(self, notify_mock):
        self.stack_mock.update.side_effect = ClientError(
            {'Error': {'Code': 'ExpectedException', 'Message': ''}},
            'test_deploy_stack_should_notify_error_in_case_of_client_error')

        update_stack(self.stack_mock, self.update_parameters, 'ANY_ARN')

        notify_mock.assert_called_once_with(ANY, 'ANY_ARN')"""


class TestLoad(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('boto3.resource')
        self.resource_mock = self.patcher.start()

        self.cloudformation_mock = Mock()
        self.stack_mock = Mock()
        self.resource_mock.return_value = self.cloudformation_mock
        self.cloudformation_mock.Stack.return_value = self.stack_mock
        self.crassus = Crassus(None, None)
        self.crassus._stack_name = STACK_NAME
        self.crassus._output_topics = ANY_TOPIC

    def tearDown(self):
        self.patcher.stop()

    def test_deploy_stack_should_load_stack(self):
        self.crassus.load()
        self.stack_mock.load.assert_called_once_with()

    @patch('crassus.deployer.sqs_send_message')
    @patch('crassus.deployer.logger')
    def test_stack_load_throws_clienterror_exception(
            self, logger_mock, mock_sqs):
        self.stack_mock.load.side_effect = ClientError(
            {'Error': {'Code': 'ExpectedException', 'Message': ''}},
            'test_deploy_stack_should_notify_error_in_case_of_client_error')
        self.crassus.load()
        logger_mock.error.assert_called_once_with(ANY)
        self.assertEquals(mock_sqs.call_count, 1)

    """
    @patch('crassus.deployer.notify')
    def test_deploy_stack_should_notify_error_in_case_of_client_error(
        self, notify_mock):
        self.stack_mock.load.side_effect = ClientError(
            {'Error': {'Code': 'ExpectedException', 'Message': ''}},
            'test_deploy_stack_should_notify_error_in_case_of_client_error')
        load_stack('ANY_STACK', 'ANY_ARN')

        notify_mock.assert_called_once_with(ANY, 'ANY_ARN')
    """


class TestStackUpdateParameters(unittest.TestCase):

    def setUp(self):
        self.input_message = {
            "version": 1,
            "stackName": "ANY_STACK",
            "region": "ANY_REGION",
            "parameters": {
                "PARAMETER1": "VALUE1",
                "PARAMETER2": "VALUE2",
            }
        }

    def test_init(self):
        sup = StackUpdateParameter(self.input_message)
        self.assertEqual(sup.version, 1)
        self.assertEqual(sup.stack_name, "ANY_STACK")
        self.assertEqual(sup.region, "ANY_REGION")
        self.assertEqual(sup.items(), [
            ("PARAMETER1", "VALUE1"),
            ("PARAMETER2", "VALUE2")])

    def test_to_aws_format(self):
        expected_output = [{"ParameterKey": "PARAMETER1",
                            "ParameterValue": "VALUE1"},
                           {"ParameterKey": "PARAMETER2",
                            "ParameterValue": "VALUE2"}]
        sup = StackUpdateParameter(self.input_message)
        self.assertEqual(sup.to_aws_format(), expected_output)

    def test_merge(self):
        input_message = {
            "version": 1,
            "stackName": "ANY_STACK",
            "region": "ANY_REGION",
            "parameters": {
                "PARAMETER2": "UPDATED_VALUE2",
            }
        }
        expected_output = [{"ParameterKey": "PARAMETER1",
                            "UsePreviousValue": True},
                           {"ParameterKey": "PARAMETER2",
                            "ParameterValue": "UPDATED_VALUE2"}]
        stack_parameter = [{"ParameterKey": "PARAMETER1",
                            "ParameterValue": "VALUE1"},
                           {"ParameterKey": "PARAMETER2",
                            "ParameterValue": "VALUE2"}]
        sup = StackUpdateParameter(input_message)
        self.assertEqual(sup.merge(stack_parameter), expected_output)


class TestOutputTopic(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('boto3.client')
        self.boto3_client = self.patcher.start()
        self.context_mock = Mock(invoked_function_arn="any_arn",
                                 function_version="any_version")
        self.crassus = Crassus(None, self.context_mock)

    def tearDown(self):
        self.patcher.stop()

    @patch('crassus.aws_tools.aws_lambda')
    def test_output_topics_returns_arn_list(self, mock_lambda):
        mock_lambda.get_function_configuration.return_value = {
            'Description': dedent("""
                {"result_queue":[
                    "arn:aws:sns:eu-west-1:123456789012:crassus-output",
                    "arn:aws:sns:eu-west-1:123456789012:random-topic"
                    ],
                    "cfn_events": ["CFN-SNS-TOPIC-1"]}""")
        }
        topic_list = self.crassus.output_topics
        expected = ["arn:aws:sns:eu-west-1:123456789012:crassus-output",
                    "arn:aws:sns:eu-west-1:123456789012:random-topic", ]
        self.assertEqual(expected, topic_list)

    @patch('crassus.aws_tools.aws_lambda')
    @patch('crassus.aws_tools.logger')
    def test_output_topics_handles_value_error(self, logger_mock, mock_lambda):
        mock_lambda.get_function_configuration.return_value = {
            'Description': "NO_SUCH_JSON"
        }
        topic_list = self.crassus.output_topics
        self.assertEqual(None, topic_list)
        logger_mock.error.assert_called_once_with(ANY)

    @patch('crassus.aws_tools.aws_lambda')
    @patch('crassus.aws_tools.logger')
    def test_output_topics_handles_key_error(self, logger_mock, mock_lambda):
        mock_lambda.get_function_configuration.return_value = {
            'Description': '{"key": "value"}'
        }
        topic_list = self.crassus.output_topics
        self.assertEqual(None, topic_list)
        logger_mock.error.assert_called_once_with(ANY)


class TestGaiusMessage(unittest.TestCase):

    def test_constructor(self):
        result_message = DeploymentResponse(
            'status', 'message', 'stack_name', 'timestamp', 'emitter')
        self.assertEqual(result_message['version'], '1.1')
        self.assertEqual(result_message['status'], 'status')
        self.assertEqual(result_message['message'], 'message')
        self.assertEqual(result_message['stackName'], 'stack_name')
        self.assertEqual(result_message['timestamp'], 'timestamp')
        self.assertEqual(result_message['emitter'], 'emitter')
        self.assertNotEqual(result_message['message'], 'invalid message')
