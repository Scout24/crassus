import datetime
import json

import boto3
from botocore.exceptions import ClientError
from crassus.utils import get_lambda_config_property, sqs_send_message, logger
from crassus.deployment_response import DeploymentResponse
from dateutil import tz

NOTIFICATION_SUBJECT = 'Crassus deployer notification'
MESSAGE_STACK_NOT_FOUND = 'Stack not found {stack_name}: {message}'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {stack_name}: {message}'


class Crassus(object):

    def __init__(self, event, context):
        self.event = event
        logger.debug('Received event: %r', event)
        self.context = context
        logger.debug('Received context: %r', context)

        self.aws_cfn = boto3.resource('cloudformation')
        self.aws_sns = boto3.resource('sns')
        self.aws_lambda = boto3.client('lambda')

        self._output_topics = None
        self._cfn_output_topics = None
        self._stack_update_parameters = None
        self._stack_name = None
        self.stack = None

    @property
    def stack_name(self):
        if not self._stack_name:
            self.parse_event()
        return self._stack_name

    @property
    def stack_update_parameters(self):
        if not self._stack_update_parameters:
            self.parse_event()
        return self._stack_update_parameters

    def parse_event(self):
        message = json.loads(self.event['Records'][0]['Sns']['Message'])
        self._stack_update_parameters = StackUpdateParameter(message)
        self._stack_name = self._stack_update_parameters.stack_name
        logger.debug('Extracted Update Parameters: %r',
                     self._stack_update_parameters)

    @property
    def output_topics(self):
        if self._output_topics:
            return self._output_topics
        self._output_topics = get_lambda_config_property(
            self.context, 'result_queue')
        return self._output_topics

    @property
    def cfn_output_topics(self):
        if self._cfn_output_topics is not None:
            return self._cfn_output_topics
        self._cfn_output_topics = get_lambda_config_property(
            self.context, 'cfn_events')
        return self._cfn_output_topics

    def notify(self, status, message):
        if self.output_topics is None:
            return
        timestamp_str = datetime.datetime.now(tz=tz.tzutc()).isoformat()
        result_message = DeploymentResponse(
            status, message, self.stack_name, timestamp_str,
            DeploymentResponse.EMITTER_CRASSUS)
        sqs_send_message(self.output_topics, result_message)

    def load(self):
        self.stack = self.aws_cfn.Stack(self.stack_name)
        try:
            self.stack.load()
            logger.debug('Loaded Stack: %r', self.stack)
        except ClientError as error:
            logger.error(MESSAGE_STACK_NOT_FOUND.format(
                stack_name=self.stack_name, message=error.message))
            self.notify(DeploymentResponse.STATUS_FAILURE, error.message)

    def update(self):
        logger.debug('Parameters to be updated: %s', self.stack.parameters)
        merged = self.stack_update_parameters.merge(self.stack.parameters)
        logger.debug('Merged parameters: %s', merged)
        try:
            logger.debug('Will try to update Cloudformation')
            self.stack.update(
                UsePreviousTemplate=True,
                Parameters=merged,
                Capabilities=['CAPABILITY_IAM'],
                NotificationARNs=self.cfn_output_topics)
            message = 'Cloudformation was triggered successfully.'
            logger.debug(message)
            self.notify(DeploymentResponse.STATUS_SUCCESS, message)
        except ClientError as error:
            logger.error(MESSAGE_UPDATE_PROBLEM.format(
                stack_name=self.stack_name, message=error.message))
            self.notify(DeploymentResponse.STATUS_FAILURE, error.message)

    def deploy(self):
        self.load()
        self.update()


class StackUpdateParameter(dict):

    def __init__(self, message):
        self.version = message['version']
        self.stack_name = message['stackName']
        self.region = message['region']
        self.update(message['parameters'])

    def to_aws_format(self):
        return [
            {'ParameterKey': key, 'ParameterValue': value}
            for key, value in self.items()]

    def merge(self, stack_parameters):
        merged_stack_parameters = []

        for update_key in self:
            update_value = self[update_key]
            filtered_list = filter(
                lambda x: x.get('ParameterKey') == update_key,
                stack_parameters)
            if not filtered_list:
                # No such parameter in stack parameters
                continue
            if filtered_list[0].get('ParameterValue') != update_value:
                merged_stack_parameters.append({
                    'ParameterKey': update_key,
                    'ParameterValue': update_value})
                stack_parameters = filter(
                    lambda x: x.get('ParameterKey') != update_key,
                    stack_parameters)

        # Turn all remaining key-values to UsePreviousValue = True
        stack_parameters = map(
            lambda x: {
                'ParameterKey': x.get('ParameterKey'),
                'UsePreviousValue': True},
            stack_parameters)
        merged_stack_parameters.extend(stack_parameters)

        return merged_stack_parameters
