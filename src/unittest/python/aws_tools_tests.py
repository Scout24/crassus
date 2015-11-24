import json
import unittest

from crassus.aws_tools import sqs_send_message
from crassus.deployment_response import DeploymentResponse
from mock import patch


class TestSqsSendMessage(unittest.TestCase):

    def setUp(self):
        self.patch_logger = patch('crassus.aws_tools.logger')
        self.mock_logger = self.patch_logger.start()

        self.patch_sqs = patch('crassus.aws_tools.aws_sqs')
        self.mock_aws_sqs = self.patch_sqs.start()

    def teardown(self):
        self.patch_logger.stop()
        self.patch_sqs.stop()

    def test_message_is_not_valid_type(self):
        sqs_send_message(['123'], 'invalid message')
        self.assertEqual(self.mock_logger.error.call_count, 1)

    def test_message_is_valid(self):
        message = DeploymentResponse(
            'status', 'message', 'stack_name', 'timestamp', 'emitter')
        message_json = json.dumps(message)
        sqs_send_message(['123'], message)
        self.mock_aws_sqs.send_message.assert_called_once_with(
            QueueUrl='123', MessageBody=message_json, DelaySeconds=0)
