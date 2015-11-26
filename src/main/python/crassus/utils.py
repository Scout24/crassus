# -*- coding: utf-8 -*-

import json
import logging
import os

import boto3
from crassus.deployment_response import DeploymentResponse

"""Utility functions module."""

aws_cf = boto3.client('cloudformation')
aws_sqs = boto3.client('sqs')
aws_lambda = boto3.client('lambda')


def _get_VERSION():
    """
    Walk up the directory tree while trying to find a file named 'VERSION'.

    If the file is found and readable, return its content, if not, return None.
    """
    actual_dir = os.path.dirname(os.path.realpath(__file__))
    while True:
        file_path = os.path.join(actual_dir, 'VERSION')
        try:
            with open(file_path, 'r') as fp:
                return 'v{0}'.format(fp.read())
        except IOError:
            if os.path.realpath(actual_dir) == '/':
                # We are at the top level, exit
                return 'NO_VERSION'
        # Iterate with the parent directory
        actual_dir = os.path.dirname(actual_dir)


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

logger = logging.getLogger('crassus-{0}'.format(_get_VERSION()))
logger.setLevel(logging.DEBUG)
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(consoleLogger)
