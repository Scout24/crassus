import boto3
import logging

logger = logging.getLogger('crassus-deployer')
logger.setLevel(logging.DEBUG)

consoleLogger = logging.StreamHandler()

logger.addHandler(consoleLogger)

cloudformation = boto3.resource('cloudformation')


# TODOS
# message format from the sns triggerin the lambda
# validate parameters
# check if stack exists
# check if stack is updateable
# check if all parameters must be present
# what about no echo parameters?
# register a sqs for stack update output
# message handling for all errors

def handler (event, context):
    cfn_update_parameters = parse_event(event)
    #import pdb; pdb.set_trace()
    logger.debug('Parsed parameters: {}'.format(cfn_update_parameters))

    stack = find_stack(cfn_update_parameters["stack_name"])
    logger.debug('Found stack: {}'.format(stack.timeout_in_minutes))

    #if not stack -> return error?

    if not validate_parameters(cfn_update_parameters):
        raise Exception('Invalid parameters')

    #do all parameters be need to specified?
    stack.update(UsePreviousTemplate=True,
                 Parameters=[
                     {
                         'ParameterKey': cfn_update_parameters["parameter_name"],
                         'ParameterValue': cfn_update_parameters["parameter_value"],
                         'UsePreviousValue': False
                     },
                     ],)


    return True




def validate_parameters(update_parameters):
    return True

#validate json and parse sns event to dictionary or class -> how does it look like?
def parse_event(event):
    return {"stack_name": "sample-stack", "parameter_name": "InstanceType", "parameter_value": "t2.micro"}

#find stack according to parameter -> not found == error
def find_stack(stack_name):
    stack = cloudformation.Stack(stack_name)
    return stack


handler(None, None)