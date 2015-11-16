import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)

NOTIFICATION_SUBJECT = 'Crassus deployer notification'
MESSAGE_STACK_NOT_FOUND = 'Stack not found {stack_name}: {message}'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {stack_name}: {message}'

STATUS_SUCCESS = 'success'
STATUS_FAILURE = 'failure'

output_sns_topics = None


class Crassus(object):

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.aws_cfn = boto3.resource('cloudformation')
        self.aws_sns = boto3.resource('sns')
        self.aws_lambda = boto3.client('lambda')
        self._output_topics = None

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
            return self._output_topics
        except ValueError:
            logger.error(
                'Description of function must contain JSON, but was "{0}"'
                .format(description))
        except KeyError:
            logger.error('Unable to find the output SNS topic')

    def notify_success(self, message):
        pass

    def notify_failure(self, message):
        pass

    def notify(self, status, message):
        pass

    def load(self):
        pass

    def update(self):
        pass

    def deploy(self):
        pass


def deploy_stack(event, context):
    global output_sns_topics
    output_sns_topics = init_output_sns_topic(context)
    logger.debug('Received event: %s', event)
    stack_update_parameters = parse_event(event)
    logger.debug('Extracted: %s', stack_update_parameters)
    stack = load_stack(stack_update_parameters.stack_name)
    logger.debug('Found stack: %s', stack)

    update_stack(stack, stack_update_parameters)


def parse_event(event):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    return StackUpdateParameter(message)


def load_stack(stack_name):
    cloudformation = boto3.resource('cloudformation')
    stack = cloudformation.Stack(stack_name)

    try:
        stack.load()
    except ClientError as error:
        logger.error(MESSAGE_STACK_NOT_FOUND.format(
            stack_name=stack_name, message=error.message))
        notify(STATUS_FAILURE, error.message, stack_name)
    else:
        return stack


def update_stack(stack, stack_update_parameters):
    merged = stack_update_parameters.merge(stack.parameters)
    try:
        stack.update(
            UsePreviousTemplate=True, Parameters=merged, Capabilities=[
                'CAPABILITY_IAM'], NotificationARNs=output_sns_topics)
        notify(
            STATUS_SUCCESS, 'Cloudformation was triggered successfully.',
            stack_update_parameters.stack_name)
    except ClientError as error:
        logger.error(MESSAGE_UPDATE_PROBLEM.format(
            stack_name=stack.name, message=error.message))
        notify(STATUS_FAILURE, error.message,
               stack_update_parameters.stack_name)


def notify(status, message, stack_name):
    if output_sns_topics is None:
        return
    sns = boto3.resource('sns')
    result_message = ResultMessage(status, message, stack_name)
    for topic_arn in output_sns_topics:
        notification_topic = sns.Topic(topic_arn)
        notification_topic.publish(
            Message=json.dumps(result_message), Subject=NOTIFICATION_SUBJECT,
            MessageStructure='string')


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


class ResultMessage(dict):

    """
    A message that crassus returns for events such as fail or success
    events for stack deployments/updates. These messages will be
    transmitted as JSON encoded strings.

    It is initialized with the following parameters:
    - status: STATUS_FAILURE or STATUS_SUCCESS
    - stack_name: the stack name the notification message stands for
    - version: a version identifier for the message. Defaults as '1.0'
    - message: the textual message for the notification.
    """

    version = '1.0'

    def __init__(self, status, message, stack_name):
        self['version'] = self.version
        self['stackName'] = stack_name
        self['status'] = status
        self['message'] = message


