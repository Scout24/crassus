# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import logging

from crassus.aws_tools import get_lambda_config_property, sqs_send_message
from deployment_response import DeploymentResponse

logger = logging.getLogger(__name__)


class OutputConverter(object):

    """
    Output converter class to do the message conversion for the command
    line client.
    """

    event = None
    context = None

    def __init__(self, event, context):
        super(OutputConverter, self).__init__()
        self.event = event
        self.context = context

    def _cast_type(self, value):
        """
        Try to JSON cast the value. It can be parsed this way to dict,
        list or integers.

        Return the string value, if nothing else succeeds.
        """
        try:
            # Try to cast to integer, or JSON
            value = json.loads(value)
            return value
        except ValueError:
            return value

    def _parse_sns_message(self, sns_message):
        """
        Parse the received SNS message from cloudformation.

        Beware: the lines are terminated with "'\n", so they must be
        split up along this pattern. There can be deviations sometimes,
        thus the workaround.

        Returns the parsed key-value pairs in a dictionary.
        """
        splitted_list = sns_message.split('\'\n')
        # Workaround for when the last parameter is not terminated with
        # the same separator pattern, then a closing quote might remain.
        if splitted_list[-1] != '' and splitted_list[-1][-1] == '\'':
            # Cut the last character from the last item
            splitted_list[-1] = splitted_list[-1][:-1]
        result_dict = {}
        for line_item in splitted_list:
            line_item = line_item.strip()
            if line_item == '':
                # Empty line, do not parse
                continue
            key, value = line_item.split('=\'')
            result_dict[key] = self._cast_type(value)
        return result_dict

    def convert(self):
        queue_url_list = get_lambda_config_property(
            self.context, 'result_queue')
        for event_item in self.event['Records']:
            sns_message = event_item.get('Sns', {}).get('Message')
            if sns_message is None:
                logger.warning(
                    'No \'Sns\' or \'Message\' in received event: {0}'
                    .format(event_item))
                continue
            message = self._parse_sns_message(sns_message)
            deployment_response = DeploymentResponse(
                message['ResourceStatus'], message['ResourceStatusReason'],
                message['StackName'], message['Timestamp'],
                DeploymentResponse.EMITTER_CFN)
            deployment_response['resourceType'] = message['ResourceType']
            sqs_send_message(queue_url_list, deployment_response)
