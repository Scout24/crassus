import unittest

from crassus.deployer import parse_event

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
                'Message': '{"stackName": "ANY STACK","notificationARN": "ANY ARN","region": "eu-west-1","params": [{"ParameterKey": "ANY_NAME1", "ParameterValue": "ANY_VALUE1"}, {"ParameterKey": "ANY_NAME2", "ParameterValue": "ANY_VALUE2"}]}',
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
        self.assertEqual(parameters[0]['ParameterKey'], 'ANY_NAME1')
        self.assertEqual(parameters[0]['ParameterValue'], 'ANY_VALUE1')
        self.assertEqual(parameters[1]['ParameterKey'], 'ANY_NAME2')
        self.assertEqual(parameters[1]['ParameterValue'], 'ANY_VALUE2')