# -*- coding: utf-8 -*-

import json
import logging

import boto3
from crassus.deployment_response import DeploymentResponse

__doc__ = """AWS helper functions module."""

aws_cf = boto3.client('cloudformation')
aws_sqs = boto3.client('sqs')
aws_lambda = boto3.client('lambda')

logger = logging.getLogger(__name__)


class AwsToolsBaseException(Exception):
    pass


class StackResourceException(AwsToolsBaseException):
    pass


def get_physical_by_logical_id(stack_name, resource_id):  # pragma: no cover
    """
    Get a physical ID (mostly ARN) from a logical ID in a given stack's
    parameters.

    Raise StackResourceException if an error occurred, return None if
    not found, and return the ID if found.
    """
    stack_param_dict = aws_cf.list_stack_resources(StackName=stack_name)
    stack_param_http_result = stack_param_dict.get(
        'ResponseMetadata', {}).get('HTTPStatusCode')
    if stack_param_http_result != 200:
        # We got a weird/nonexistent response code
        raise StackResourceException('Erroneous HTTPStatusCode.')
    for parameters_item in stack_param_dict.get('StackResourceSummaries', []):
        if parameters_item['LogicalResourceId'] == resource_id:
            return parameters_item['PhysicalResourceId']


def get_my_stack_name_by_func_arn(invoked_function_arn):  # pragma: no cover
    """
    Get the stack name for an invoked function ARN.

    Returns the stack name if found, None if not available or in case
    of any errors.
    """
    stack_dict = aws_cf.list_stacks(
        StackStatusFilter=[
            'CREATE_COMPLETE',
            'UPDATE_COMPLETE',
        ])
    stack_param_http_result = stack_dict.get(
        'ResponseMetadata', {}).get('HTTPStatusCode')
    if stack_param_http_result != 200:
        # We got a weird/nonexistent response code
        return
    for item in stack_dict.get('StackSummaries', []):
        stack_name = item['StackName']
        try:
            resource_id = get_physical_by_logical_id(
                stack_name, invoked_function_arn)
        except StackResourceException:
            continue
        if resource_id is not None:
            # Got the resource id, our stack name is the current
            # stack_name
            return stack_name


def sqs_send_message(queue_url_list, message):
    """
    Send an message to a given SQS queue. The function is not foolproof,
    you should have the rights to transmit to the SQS queue.
    """
    if type(message) is not DeploymentResponse:
        logger.error(
            'sqs_send_message: got wrong type of message parameter: {0}: {1}'
            .format(type(message), repr(message)))
        return
    message_str = json.dumps(message)
    for queue_url in queue_url_list:
        aws_sqs.send_message(
            QueueUrl=queue_url, MessageBody=message_str, DelaySeconds=0)


def get_lambda_config_property(context, property_name):
    """
    Extract JSON properties from the JSON encoded description.

    Return the value for the property, None if not found.
    """
    function_arn = context.invoked_function_arn
    qualifier = context.function_version
    description = aws_lambda.get_function_configuration(
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
        logger.error(
            'Unable to find \'{0}\' property in the JSON description.'
            .format(property_name))
