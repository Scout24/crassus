import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)

consoleLogger = logging.StreamHandler()

logger.addHandler(consoleLogger)

cloudformation = boto3.resource('cloudformation')


# TODOS
# message format from the sns triggerin the lambda
# validate parameters

# check if all parameters must be present
# what about no echo parameters?
# register a sqs for stack update output
# message handling for all errors

def handler (event, context):
    cfn_update_parameters = parse_event(event)
    logger.debug('Parsed parameters: {}'.format(cfn_update_parameters))
    stack_name = cfn_update_parameters["stack_name"]
    stack = cloudformation.Stack(stack_name)

    try:
        stack.load()
    except ClientError as error:
        logger.error('Did not found stack: {}'.format(stack_name))
        logger.error(error.message)
        return False

    logger.debug('Found stack: {}'.format(stack))

    if not validate_parameters(cfn_update_parameters):
        raise Exception('Invalid parameters')


    #do all parameters be need to specified?
    try:
        stack.update(UsePreviousTemplate=True,
                     Parameters=[
                         {
                             'ParameterKey': cfn_update_parameters["parameter_name"],
                             'ParameterValue': cfn_update_parameters["parameter_value"],
                             'UsePreviousValue': False
                         },
                         ])
    except ClientError as error:
        logger.error('Problem during update'.format(stack_name))
        logger.error(error.message)
        return False


    return True




def validate_parameters(update_parameters):
    return True

#validate json and parse sns event to dictionary or class -> how does it look like?
def parse_event(event):
    return {"stack_name": "sample-stack", "parameter_name": "InstanceType", "parameter_value": "t2.small"}



handler(None, None)