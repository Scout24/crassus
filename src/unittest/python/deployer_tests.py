import unittest

from crassus.deployer import (
    parse_event,
    map_cloudformation_parameters,
    load_stack,
    notify,
    NOTIFICATION_SUBJECT,
)

from botocore.exceptions import ClientError
from mock import Mock, patch, ANY

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
                'Message': '{"stackName": "ANY_STACK","notificationARN": "ANY_ARN","region": "eu-west-1","params": [{"updateParameterKey": "ANY_NAME1", "updateParameterValue": "ANY_VALUE1"}, {"updateParameterKey": "ANY_NAME2", "updateParameterValue": "ANY_VALUE2"}]}',
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


class TestDeployer(unittest.TestCase):
    def test_parse_valid_event(self):
        stack_name, notification_arn, parameters = parse_event(SAMPLE_EVENT)

        self.assertEqual(stack_name, 'ANY_STACK')
        self.assertEqual(notification_arn, 'ANY_ARN')


    def test_map_mulitple_cloudformation_parameters(self):
        result = map(map_cloudformation_parameters, CRASSUS_CFN_PARAMETERS)

        self.assertEqual(result[0]['ParameterKey'], 'ANY_NAME1')
        self.assertEqual(result[0]['ParameterValue'], 'ANY_VALUE1')
        self.assertEqual(result[0]['UsePreviousValue'], False)
        self.assertEqual(result[1]['ParameterKey'], 'ANY_NAME2')
        self.assertEqual(result[1]['ParameterValue'], 'ANY_VALUE2')
        self.assertEqual(result[1]['UsePreviousValue'], False)


class TestNotify(unittest.TestCase):
    MESSAGE = 'ANY MESSAGE'
    NOTIFICATION_ARN = 'ANY_NOTIFICATION_ARN'

    @patch('boto3.resource')
    def test_should_notify_sns(self, resource_mock):
        topic_mock = Mock()
        sns_mock = Mock()
        sns_mock.Topic.return_value = topic_mock
        resource_mock.return_value = sns_mock

        notify(self.MESSAGE, self.NOTIFICATION_ARN)

        topic_mock.publish.assert_called_once_with(Message=self.MESSAGE, Subject=NOTIFICATION_SUBJECT,
                                                   MessageStructure='string')


class TestLoadStack(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('boto3.resource')
        self.resource_mock = self.patcher.start()

        self.cloudformation_mock = Mock()
        self.stack_mock = Mock()
        self.resource_mock.return_value = self.cloudformation_mock
        self.cloudformation_mock.Stack.return_value = self.stack_mock


    def tearDown(self):
        self.patcher.stop()

    def test_deploy_stack_should_load_stack(self):
        load_stack('ANY_STACK', 'ANY_ARN')

        self.stack_mock.load.assert_called_once_with()


    @patch('crassus.deployer.notify')
    def test_deploy_stack_should_notify_error_in_case_of_client_error(self, notify_mock):
        self.stack_mock.load.side_effect = ClientError({'Error': {'Code': 'ExpectedException', 'Message': ''}},
                                                       'test_deploy_stack_should_notify_error_in_case_of_client_error')
        load_stack('ANY_STACK', 'ANY_ARN')

        notify_mock.assert_called_once_with(ANY, 'ANY_ARN')