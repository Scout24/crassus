from __future__ import print_function

import json
import logging
import re
import socket
import sys
import threading
import unittest
import urllib2
from datetime import datetime
from time import sleep

import boto3
from botocore.exceptions import ClientError
from cfn_sphere.config import Config
from cfn_sphere.main import StackActionHandler

REGION_NAME = 'eu-west-1'
SNS_FULL_ACCESS = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"

logging.basicConfig(
    format='%(asctime)s %(threadName)s %(levelname)s %(module)s: %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
    stream=sys.stdout)
logger = logging.getLogger()
logger.level = logging.INFO


class CreateStack(threading.Thread):

    def __init__(self, thread_name, stack_config):
        super(CreateStack, self).__init__(name=thread_name)
        self.stack_config = stack_config

    def run(self):
        StackActionHandler(self.stack_config).create_or_update_stacks()


class CrassusIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.test_id = "crassus-it-{0}-{1}" \
            .format(socket.gethostname(),
                    datetime.utcnow().strftime("%Y%m%d%H%M%S"))
        self.invoker_role_name = "crassus-invoker-it-{0}".format(self.test_id)
        logger.info("running with test id: {0}".format(self.test_id))

        self.iam_client = boto3.client('iam')
        self.sts_client = boto3.client('sts')
        self.cfn_client = boto3.client('cloudformation')
        self.ec2_client = boto3.client("ec2")

    def create_invoker_role(self):
        current_account = re.compile('arn:aws:iam::(\d{12}):.*')\
            .match(self.iam_client.list_roles()['Roles'][0]['Arn']).group(1)
        assume_role_policy = json.dumps(
            {
                "Statement": [
                    {"Effect": "Allow", "Principal":
                        {"AWS": "arn:aws:iam::{0}:root".format(
                            current_account)},
                     "Action": ["sts:AssumeRole"]}
                ]
            })

        invoker_role = boto3.resource('iam').create_role(
            RoleName=self.invoker_role_name,
            AssumeRolePolicyDocument=assume_role_policy)

        self.iam_client.attach_role_policy(RoleName=self.invoker_role_name,
                                           PolicyArn=SNS_FULL_ACCESS)

        return invoker_role

    def assume_role(self, invoker_role):
        credentials = self.sts_client.assume_role(
            RoleArn=invoker_role.arn, RoleSessionName="{0}".format(
                self.test_id))['Credentials']

        ec2 = boto3.client(service_name="ec2", region_name=REGION_NAME,
                           aws_access_key_id=credentials['AccessKeyId'],
                           aws_secret_access_key=credentials[
                               'SecretAccessKey'],
                           aws_session_token=credentials['SessionToken'])
        try:
            ec2.describe_instances()
            self.fail(
                "Should not be allowed for role: {0}".format(invoker_role.arn))
        except ClientError as e:
            logger.debug("Expected error: {0}".format(e))

        return credentials

    def test_create_stacks_and_update(self):
        invoker_role = self.create_invoker_role()

        stack = self.create_crassus_stack(invoker_role.arn)
        app_stack = self.create_app_stack()
        stack.join()
        app_stack.join()

        self.send_update_message(invoker_role)

        hello_world_url = self.get_stack_output(self.app_stack_name,
                                                "WebsiteURL")

        update_successful = False

        for i in range(0, 30):
            hello_world = urllib2.urlopen(hello_world_url).read()
            if re.compile('.*?python-docker-hello-world-webapp 40.*').match(
                    hello_world):
                update_successful = True
                break
            else:
                sleep(10)

        self.assertTrue(update_successful)

    def send_update_message(self, invoker_role):
        credentials = self.assume_role(invoker_role)
        sns_client = boto3.client(service_name="sns",
                                  region_name=REGION_NAME,
                                  aws_access_key_id=credentials['AccessKeyId'],
                                  aws_secret_access_key=credentials[
                                      'SecretAccessKey'],
                                  aws_session_token=credentials['SessionToken'])
        message = {
            "version": 1,
            "stackName": self.app_stack_name,
            "region": REGION_NAME,
            "parameters": {
                "dockerImageVersion": "40"
            }
        }
        crassus_input_topic_arn = self.get_stack_output(self.test_id,
                                                        "inputSnsTopicARN")

        message_id = sns_client.publish(TopicArn=crassus_input_topic_arn,
                                        Message=json.dumps(message))
        logger.info(
            "published update message to topic: {0}, message: {1}, got message_id: {2}".format(
                crassus_input_topic_arn, message, message_id
            ))

    def get_stack_output(self, stack_name, output_name):
        stack_outputs = self.cfn_client.describe_stacks(
            StackName=stack_name)['Stacks'][0]['Outputs']

        output_value = None

        for output_item in stack_outputs:
            if output_item['OutputKey'] == output_name:
                output_value = output_item['OutputValue']

        if output_value is None:
            raise Exception("Stack with name: {0} does not have output: {1}"
                            .format(stack_name, output_name))

        return output_value

    def create_app_stack(self):
        subnet_ids, vpc_id = self.get_first_vpc_and_subnets()
        self.app_stack_name = "app-{0}".format(self.test_id)
        app_config = Config(config_dict={
            "region": REGION_NAME,
            "stacks": {
                self.app_stack_name: {
                    "template-url": "s3://is24-python-docker-hello-world-webapp/latest/ecs-minimal-webapp.json",
                    "parameters": {
                        "vpcId": vpc_id,
                        "subnetIds": subnet_ids,
                        "dockerImageVersion": "15"
                    }
                }
            }
        })
        app_stack_creation = CreateStack("AppCreationThread", app_config)
        app_stack_creation.start()
        return app_stack_creation

    def create_crassus_stack(self, invoker_role_arn):
        crassus_config = Config(config_dict={
            "region": REGION_NAME,
            "stacks": {
                self.test_id: {
                    "template-url": "s3://crassus-lambda-zips/latest/crassus.json",
                    "parameters": {
                        "zipFile": "latest/crassus.zip",
                        "bucketName": "crassus-lambda-zips",
                        "triggeringUserArn": invoker_role_arn
                    }
                }
            }
        })
        crassus_stack_creation = CreateStack("CrassusCreationThread",
                                             crassus_config)
        crassus_stack_creation.start()
        return crassus_stack_creation

    def get_first_vpc_and_subnets(self):
        vpc_id = self.ec2_client.describe_vpcs()['Vpcs'][0]['VpcId']
        subnet_ids = []
        subnets = self.ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id',
                                                             'Values': [vpc_id]}])['Subnets']
        for subnet in subnets:
            subnet_ids.append(subnet['SubnetId'])
        subnet_ids_paramater = ",".join(subnet_ids)
        return subnet_ids_paramater, vpc_id

    def tearDown(self):
        self.delete_invoker_role()
        self.delete_stack(self.test_id)
        self.delete_stack(self.app_stack_name)

    def delete_invoker_role(self):
        self.ignore_client_error(lambda:
                                 self.iam_client.detach_role_policy(
                                     RoleName=self.invoker_role_name,
                                     PolicyArn=SNS_FULL_ACCESS))
        self.ignore_client_error(lambda:
                                 self.iam_client.delete_role(
                                     RoleName=self.invoker_role_name))

    def delete_stack(self, stack_name):
        self.ignore_client_error(lambda:
                                 self.cfn_client.delete_stack(
                                     StackName=stack_name))

    def ignore_client_error(self, function):
        try:
            function()
        except ClientError as exc:
            logger.info(
                'unable to execute {0}: {1}'.format(
                    function.__name__, exc.message))
