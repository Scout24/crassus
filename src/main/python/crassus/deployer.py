import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)

NOTIFICATION_SUBJECT = 'Crassus deployer notification'
MESSAGE_STACK_NOT_FOUND = 'Stack not found {0}: {1}'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {0}: {1}'

output_sns_topic = None


def deploy_stack(event, context):
    global output_sns_topic
    output_sns_topic = init_output_sns_topic()
    logger.debug('Received event: %s', event)
    stack_update_parameters = parse_event(event)
    logger.debug('Extracted: %s', stack_update_parameters)
    stack = load_stack(stack_update_parameters.stack_name)
    logger.debug('Found stack: %s', stack)

    update_stack(stack, stack_update_parameters)


def init_output_sns_topic():
    sns = boto3.resource('sns')
    topics = [topic for topic in sns.topics.all()
              if topic.arn.endswith(":crassus-output")]
    if len(topics) != 1:
        logger.error('Unable to find the output SNS topic')
    else:
        return topics[0]


def parse_event(event):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    return StackUpdateParameter(message)


def load_stack(stack_name):
    cloudformation = boto3.resource('cloudformation')
    stack = cloudformation.Stack(stack_name)

    try:
        stack.load()
    except ClientError as error:
        logger.error(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message))
    else:
        return stack


def update_stack(stack, stack_update_parameters):
    merged = stack_update_parameters.merge(stack.parameters)
    try:
        stack.update(UsePreviousTemplate=True,
                     Parameters=merged,
                     Capabilities=[
                         'CAPABILITY_IAM',
                     ])
    except ClientError as error:
        logger.error(MESSAGE_UPDATE_PROBLEM.format(stack.name, error.message))


def notify(message, notification_arn):
    sns = boto3.resource('sns')
    notification_topic = sns.Topic(notification_arn)
    notification_topic.publish(Message=message,
                               Subject=NOTIFICATION_SUBJECT,
                               MessageStructure='string')


class StackUpdateParameter(dict):

    def __init__(self, message):
        self.version = message['version']
        self.stack_name = message['stackName']
        self.region = message['region']
        self.update(message['parameters'])

    def to_aws_format(self):
        return [{"ParameterKey": k, "ParameterValue": v}
                for k, v in self.items()]

    def merge(self, stack_parameters):
        merged_stack_parameters = []
        update_parameters = self.to_aws_format()

        for stack_parameter in stack_parameters:
            for update_parameter in update_parameters:
                if update_parameter['ParameterKey'] in stack_parameter.values():
                    merged_stack_parameters.append(update_parameter)
                else:
                    stack_parameter['UsePreviousValue'] = True
                    del stack_parameter['ParameterValue']
                    merged_stack_parameters.append(stack_parameter)

        return merged_stack_parameters


class ResultMessage(dict):

    version = '1.0'

    def __init__(self, status, message):
        self['version'] = self.version
        self['status'] = status
        self['message'] = message
