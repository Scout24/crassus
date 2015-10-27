import boto3
import logging
import json
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)


NOTIFICATION_SUBJECT = 'Crassus deployer notification'

MESSAGE_STACK_NOT_FOUND = 'Did not found stack {0}: {1}'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {0}: {1}'


def deploy_stack(event, context):
    logger.debug('Received event: %s', event)
    stack_name, notification_arn, parameter_name, parameter_value = parse_event(event)
    logger.debug('Extracted: %s, %s, %s, %s', stack_name, notification_arn, parameter_name, parameter_value)

    cloudformation = boto3.resource('cloudformation')
    stack = cloudformation.Stack(stack_name)

    try:
        stack.load()
    except ClientError as error:
        logger.error(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message))
        notify(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message), notification_arn)
        return False

    logger.debug('Found stack: {}'.format(stack))

    try:
        stack.update(UsePreviousTemplate=True,
                     Parameters=[
                         {
                             'ParameterKey': parameter_name,
                             'ParameterValue': parameter_value,
                             'UsePreviousValue': False
                         },
                         ],
                     NotificationARNs=[
                         notification_arn
                     ])
    except ClientError as error:
        logger.error(MESSAGE_UPDATE_PROBLEM.format(stack_name, error.message))
        notify(MESSAGE_UPDATE_PROBLEM.format(stack_name, error.message), notification_arn)
        return False

    return True


def notify(message, notification_arn):
    sns = boto3.resource('sns')
    notification_topic = sns.Topic(notification_arn)
    notification_topic.publish(Message=message,
                               Subject=NOTIFICATION_SUBJECT,
                               MessageStructure='string')


def parse_event(event):
    payload = json.loads(event['Records'][0]['Sns']['Message'])
    return payload['stackName'], payload['notificationARN'], 'dockerImageVersion', payload['params']['dockerImageVersion']
