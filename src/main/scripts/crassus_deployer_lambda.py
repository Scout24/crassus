import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

cloudformation = boto3.resource('cloudformation')


def handler (event, context):
    cfn_update_parameters = parse_event(event)
    logger.debug('Parsed parameters: {}'.format(cfn_update_parameters))

    stack = find_stack(cfn_update_parameters["stack_name"])
    logger.debug('Found stack: {}'.format(cfn_update_parameters))

    #existing_stack_parameters = cfn_update_parametersk)
    #prepared_parameters = prepare_stack_parameters(existing_stack_parameters, cfn_update_parameters)

    #cloudformation.update_stack(StackName=cfn_update_parameters.stack_name)







#validate json and parse sns event to dictionary or class
def parse_event(event):
    return {"stack_name": "sample-stack"}

#find stack according to parameter -> not found == error
def find_stack(stack_name):
    return cloudformation.Stack(stack_name)
