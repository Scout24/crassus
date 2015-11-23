# -*- coding: utf-8 -*-

import boto3

__doc__ = """AWS helper functions module."""

aws_cf = boto3.client('cloudformation')


class AwsToolsBaseException(Exception):
    pass


class StackResourceException(AwsToolsBaseException):
    pass


def get_physical_by_logical_id(context, stack_name, resource_id):
    """
    Get a physical ID (mostly ARN) from a logical ID in a given stack's
    parameters.

    Raise StackResourceException if an error occurred, return None if
    not found, and return the ID if found.
    """
    stack_param_dict = aws_cf.list_stack_resources(
        StackName=stack_name)
    if stack_param_dict.get(
            'ResponseMetadata', {}).get('HTTPStatusCode') != 200:
        # We got a weird/nonexistent response code
        raise StackResourceException('Erroneous HTTPStatusCode.')
    for parameters_item in stack_param_dict.get('StackResourceSummaries', []):
        if parameters_item['LogicalResourceId'] == resource_id:
            return parameters_item['PhysicalResourceId']


def get_my_stack_name(context):
    """
    Get the stack name for the currently running lambda from the
    context.

    Returns the stack name if found, None if not available or in case
    of any errors.
    """
    stack_dict = aws_cf.list_stacks(
        StackStatusFilter=[
            'CREATE_COMPLETE',
            'UPDATE_COMPLETE',
        ]
    )
    if stack_dict.get('ResponseMetadata', {}).get('HTTPStatusCode') != 200:
        # We got a weird/nonexistent response code
        return
    for item in stack_dict.get('StackSummaries', []):
        stack_name = item['StackName']
        try:
            resource_id = get_physical_by_logical_id(
                context, stack_name, context.invoked_function_arn)
        except StackResourceException:
            continue
        if resource_id is not None:
            # Got the resource id, our stack name is the current
            # stack_name
            return stack_name
