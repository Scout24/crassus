import json
import logging

import boto3
from botocore.exceptions import ClientError
from crassus.result_message import ResultMessage

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)

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
        FunctionName = self.context.invoked_function_arn
        Qualifier = self.context.function_version
        description = self.aws_lambda.get_function_configuration(
            FunctionName=FunctionName,
            Qualifier=Qualifier
        )['Description']
        try:
            data = json.loads(description)
            self._output_topics = data['topic_list']
            logger.debug('Extracted Output Topic(s): %r', self._output_topics)
            return self._output_topics
        except ValueError:
            logger.error(
                'Description of function must contain JSON, but was "{0}"'
                .format(description))
        except KeyError:
            logger.error('Unable to find the output SNS topic')

    def notify(self, status, message):
        if self.output_topics is None:
            return
        result_message = ResultMessage(status, message, self.stack_name)
        for topic_arn in self.output_topics:
            notification_topic = self.aws_sns.Topic(topic_arn)
            notification_topic.publish(
                Message=json.dumps(result_message),
                Subject=NOTIFICATION_SUBJECT,
                MessageStructure='string')

    def load(self):
        self.stack = self.aws_cfn.Stack(self.stack_name)
        try:
            self.stack.load()
            logger.debug('Loaded Stack: %r', self.stack)
        except ClientError as error:
            logger.error(MESSAGE_STACK_NOT_FOUND.format(
                stack_name=self.stack_name, message=error.message))
            self.notify(ResultMessage.STATUS_FAILURE, error.message)

    def update(self):
        merged = self.stack_update_parameters.merge(self.stack.parameters)
        try:
            logger.debug('Will try to update Cloudformation')
            self.stack.update(
                UsePreviousTemplate=True,
                Parameters=merged,
                Capabilities=['CAPABILITY_IAM'],
                NotificationARNs=None)
                # NotificationARNs=self.output_topics)
            message = 'Cloudformation was triggered successfully.'
            logger.debug(message)
            self.notify(ResultMessage.STATUS_SUCCESS, message)
        except ClientError as error:
            logger.error(MESSAGE_UPDATE_PROBLEM.format(
                stack_name=self.stack_name, message=error.message))
            self.notify(ResultMessage.STATUS_FAILURE, error.message)

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
        update_parameters = self.to_aws_format()

        for stack_parameter in stack_parameters:
            for update_parameter in update_parameters:
                if update_parameter['ParameterKey'] in \
                        stack_parameter.values():
                    merged_stack_parameters.append(update_parameter)
                else:
                    stack_parameter['UsePreviousValue'] = True
                    del stack_parameter['ParameterValue']
                    merged_stack_parameters.append(stack_parameter)

        return merged_stack_parameters
