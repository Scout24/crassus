from __future__ import print_function
import socket
import unittest
import json
from datetime import datetime
import logging
import sys
import threading

from botocore.exceptions import ClientError
from cfn_sphere.config import Config
from cfn_sphere.main import StackActionHandler
import re
import boto3

logging.basicConfig(format='%(asctime)s %(threadName)s %(levelname)s %(module)s: %(message)s',
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
        self.test_id = "crassus-it-{0}-{1}".format(socket.gethostname(), datetime.utcnow().strftime("%Y%m%d%H%M%S"))
        print("running with test id: {0}".format(self.test_id))

        self.iam_client = boto3.client('iam')
        current_account = re.compile('arn:aws:iam::(\d{12}):.*')\
            .match(self.iam_client.list_roles()['Roles'][0]['Arn']).group(1)
        policy = json.dumps(
            {
                "Statement": [
                    {"Effect": "Allow", "Principal":
                        {"AWS": "arn:aws:iam::{0}:root".format(
                            current_account)},
                     "Action": ["sts:AssumeRole"]}
                ]
            })

        self.invoker_role_name = "crassus-invoker-it-{0}".format(self.test_id)
        iam_service = boto3.resource('iam')
        self.invoker_role = iam_service.create_role(
            RoleName=self.invoker_role_name, AssumeRolePolicyDocument=policy)

    def assume_role(self):
        sts_client = boto3.client('sts')
        credentials = sts_client.assume_role(RoleArn=self.invoker_role.arn,
                                             RoleSessionName="{0}".format(self.test_id))['Credentials']

        ec2 = boto3.client(service_name="ec2", region_name='eu-west-1',
                           aws_access_key_id=credentials['AccessKeyId'],
                           aws_secret_access_key=credentials['SecretAccessKey'],
                           aws_session_token=credentials['SessionToken'])
        try:
            ec2.describe_instances()
            self.fail("Should not be allowed for role: {0}".format(self.invoker_role.arn))
        except ClientError as e:
            print("Error: {0}".format(e))
            print("vars: {0}".format(vars(e)))

        return credentials

    def test_create_stacks_and_update(self):
        crassus_config = Config(config_dict={
            "region": "eu-west-1",
            "stacks": {
                self.test_id: {
                    "template-url": "s3://crassus-lambda-zips/latest/crassus.json",
                    "parameters": {
                        "zipFile": "latest/crassus.zip",
                        "bucketName": "crassus-lambda-zips",
                        "triggeringUserArn": self.invoker_role.arn
                    }
                }
            }
        })
        crassus_stack_creation = CreateStack("CrassusCreationThread", crassus_config)
        crassus_stack_creation.start()

        subnet_ids, vpc_id = self.get_vpc_and_subnets()

        self.app_stack_name = "app-{0}".format(self.test_id)
        app_config = Config(config_dict={
            "region": "eu-west-1",
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

        crassus_stack_creation.join()
        app_stack_creation.join()

        self.assume_role()

    def get_vpc_and_subnets(self):
        ec2_client = boto3.client("ec2")
        vpc_id = ec2_client.describe_vpcs()['Vpcs'][0]['VpcId']
        subnet_ids = []
        subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
        for subnet in subnets:
            subnet_ids.append(subnet['SubnetId'])
        subnet_ids_parmater = ",".join(subnet_ids)
        return subnet_ids_parmater, vpc_id

    def tearDown(self):
        try:
            self.delete_role()
        except ClientError as e:
            logger.info(e)
            pass

        self.delete_crassus_stack(self.test_id)
        self.delete_crassus_stack(self.app_stack_name)

    def delete_role(self):
        if self.invoker_role is None:
            pass
        self.iam_client.delete_role(RoleName=self.invoker_role_name)

    def delete_crassus_stack(self, stack_name):
        cfn_client = boto3.client('cloudformation')
        try:
            cfn_client.delete_stack(StackName=stack_name)
        except ClientError as e:
            logger.info("unable to delete stack {0}".format(stack_name))
            pass
