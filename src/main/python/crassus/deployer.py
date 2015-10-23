import boto3
import logging
import json
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
logger.addHandler(consoleLogger)

cloudformation = boto3.resource('cloudformation')
sns = boto3.resource('sns')

NOTIFICATION_SUBJECT = 'Crassus deployer notification'

MESSAGE_STACK_NOT_FOUND = 'Did not found stack {0}: {1}'
MESSAGE_INVALID_PARAMETERS = 'Invalid parameters'
MESSAGE_UPDATE_PROBLEM = 'Problem while updating stack {0}: {1}'


def deploy_stack(event, context):
    cfn_update_parameters = parse_event(event)
    logger.debug('Parsed parameters: {}'.format(cfn_update_parameters))
    stack_name = cfn_update_parameters['stackName']
    notification_arn = cfn_update_parameters['notificationARN']
    parameter_name = 'dockerImageVersion'
    parameter_value = cfn_update_parameters['params']['dockerImageVersion']

    stack = cloudformation.Stack(stack_name)


    try:
        stack.load()
    except ClientError as error:
        logger.error(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message))
        notify(MESSAGE_STACK_NOT_FOUND.format(stack_name, error.message), notification_arn)
        return False

    logger.debug('Found stack: {}'.format(stack))

    if not validate_parameters(cfn_update_parameters):
        notify(MESSAGE_INVALID_PARAMETERS, notification_arn)
        raise Exception('Invalid parameters')

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
    notification_topic = sns.Topic(notification_arn)
    notification_topic.publish(Message=message,
                               Subject=NOTIFICATION_SUBJECT,
                               MessageStructure='string')


def validate_parameters(update_parameters):
    return True


# validate json and parse sns event to dictionary or class -> how does it look like?
def parse_event(event):
    payload = json.loads(event['Records'][0]['Sns']['Message'])

    return payload


