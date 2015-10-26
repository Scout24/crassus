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
                'Message': '{"stackName": "ANY STACK","notificationARN": "ANY ARN","region": "eu-west-1","params": {"dockerImageVersion": "any value"}}',
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

    def test_parse_event(self):
        stack_name, notification_arn, parameter_name, parameter_value = parse_event(SAMPLE_EVENT)

        self.assertEqual(stack_name, 'ANY STACK')
        self.assertEqual(notification_arn, 'ANY ARN')
        self.assertEqual(parameter_name, 'dockerImageVersion')
        self.assertEqual(parameter_value, 'any value')