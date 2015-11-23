import json
import logging

import boto3
from botocore.exceptions import ClientError
from crassus.deployment_response import DeploymentResponse

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

    def _get_config_property(self, property_name):
        """
        Extract JSON properties from the JSON encoded description.
        """
        function_arn = self.context.invoked_function_arn
        qualifier = self.context.function_version
        description = self.aws_lambda.get_function_configuration(
            FunctionName=function_arn,
            Qualifier=qualifier
        )['Description']
        try:
            data = json.loads(description)
            return_value = data[property_name]
            logger.debug('Extracted {0} property: %{1}'.format(
                property_name, repr(return_value)))
            return return_value
        except ValueError:
            logger.error(
                'Description of function must contain JSON, but was "{0}"'
                .format(description))
        except KeyError:
            logger.error((
                'Unable to find \'{0}\' property in the JSON '
                'description.').format(property_name))

    @property
    def output_topics(self):
        if self._output_topics:
            return self._output_topics
        self._output_topics = self._get_config_property('result_queue')
        return self._output_topics

    @property
    def cfn_output_topics(self):
        if self._cfn_output_topics is not None:
            return self._cfn_output_topics
        self._cfn_output_topics = self._get_config_property('cfn_events')
        return self._cfn_output_topics

    def notify(self, status, message):
        if self.output_topics is None:
            return
        result_message = DeploymentResponse(status, message, self.stack_name)
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
            self.notify(DeploymentResponse.STATUS_FAILURE, error.message)

    def update(self):
        merged = self.stack_update_parameters.merge(self.stack.parameters)
        try:
            logger.debug('Will try to update Cloudformation')
            self.stack.update(
                UsePreviousTemplate=True,
                Parameters=merged,
                Capabilities=['CAPABILITY_IAM'],
                # NotificationARNs=None)
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
