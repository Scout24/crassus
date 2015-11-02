import boto3
import logging
import json
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)

NOTIFICATION_SUBJECT = 'Crassus deployer notification'
MESSAGE_STACK_NOT_FOUND = 'Stack not found {0}: {1}'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {0}: {1}'


def deploy_stack(event, context):
    logger.debug('Received event: %s', event)
    stack_name, notification_arn, update_parameters = parse_event(event)
    logger.debug('Extracted: %s, %s, %s', stack_name, notification_arn, update_parameters)
    stack = load_stack(stack_name, notification_arn)
    logger.debug('Found stack: %s', stack)

    update_stack(stack, update_parameters, notification_arn)


def parse_event(event):
    payload = json.loads(event['Records'][0]['Sns']['Message'])
    payload_parameters = payload['params']

    update_parameters = map(map_cloudformation_parameters, payload_parameters)

    return payload['stackName'], payload['notificationARN'], update_parameters


def map_cloudformation_parameters(parameter):
    cloudformation_parameter = {}

    cloudformation_parameter['ParameterKey'] = parameter["updateParameterKey"]
    cloudformation_parameter['ParameterValue'] = parameter["updateParameterValue"]

    return cloudformation_parameter


def load_stack(stack_name, notification_arn):
    cloudformation = boto3.resource('cloudformation')
    stack = cloudformation.Stack(stack_name)

    try:
        stack.load()
    except ClientError as error:
        logger.error(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message))
        notify(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message), notification_arn)

    return stack

def update_stack(stack, update_parameters, notification_arn):
    stack_parameters = stack.parameters
    merged = merge_stack_parameters(update_parameters, stack_parameters)
    try:
        stack.update(UsePreviousTemplate=True,
                     Parameters=merged,
                     NotificationARNs=[
                         notification_arn
                     ],
                     Capabilities=[
                         'CAPABILITY_IAM',
                     ])
    except ClientError as error:
        logger.error(MESSAGE_UPDATE_PROBLEM.format(stack.name, error.message))
        notify(MESSAGE_UPDATE_PROBLEM.format(stack.name, error.message), notification_arn)

def merge_stack_parameters(update_parameters, stack_parameters):
    merged_stack_parameters = []

    for stack_parameter in stack_parameters:
        for update_parameter in update_parameters:
            if update_parameter['ParameterKey'] in stack_parameter.values():
                update_parameter['UsePreviousValue'] = False
                merged_stack_parameters.append(update_parameter)
            else:
                stack_parameter['UsePreviousValue'] = True
                del stack_parameter['ParameterValue']
                merged_stack_parameters.append(stack_parameter)

    return merged_stack_parameters

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
