import unittest

from crassus.deployer import parse_event
from crassus.deployer import map_cloudformation_parameters

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
                'Message': '{"stackName": "ANY STACK","notificationARN": "ANY ARN","region": "eu-west-1","params": [{"updateParameterKey": "ANY_NAME1", "updateParameterValue": "ANY_VALUE1"}, {"updateParameterKey": "ANY_NAME2", "updateParameterValue": "ANY_VALUE2"}]}',
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

        self.assertEqual(stack_name, 'ANY STACK')
        self.assertEqual(notification_arn, 'ANY ARN')


    def test_map_mulitple_cloudformation_parameters(self):
        result = map(map_cloudformation_parameters, CRASSUS_CFN_PARAMETERS)

        self.assertEqual(result[0]['ParameterKey'], 'ANY_NAME1')
        self.assertEqual(result[0]['ParameterValue'], 'ANY_VALUE1')
        self.assertEqual(result[0]['UsePreviousValue'], False)
        self.assertEqual(result[1]['ParameterKey'], 'ANY_NAME2')
        self.assertEqual(result[1]['ParameterValue'], 'ANY_VALUE2')
        self.assertEqual(result[1]['UsePreviousValue'], False)

