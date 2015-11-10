from __future__ import print_function
import uuid
import unittest
import json
from time import sleep

import re
import boto3


class CrassusIntegrationTest(unittest.TestCase):

    def setUp(self):
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

        self.invoker_role_name = "crassus-invoker-it-{0}".format(uuid.uuid1())
        iam_service = boto3.resource('iam')
        self.invoker_role = iam_service.create_role(
            RoleName=self.invoker_role_name, AssumeRolePolicyDocument=policy)

        sleep(10)

        sts_client = boto3.client('sts')
        print('role arn: {0}'.format(self.invoker_role.arn))
        credentials = sts_client.assume_role(
            RoleArn=self.invoker_role.arn, RoleSessionName='{0}'
            .format(uuid.uuid1()))['Credentials']

        # ec2 = boto3.client(service_name="ec2", region_name='eu-west-1',
        #              aws_access_key_id=credentials['AccessKeyId'],
        #              aws_secret_access_key=credentials['SecretAccessKey'],
        #              aws_session_token=credentials['SessionToken'])
        # print(ec2.describe_instances())

    def test_create_stacks_and_update(self):
        print(self.invoker_role)

    def tearDown(self):
        if self.invoker_role is None:
            pass

        self.iam_client.delete_role(RoleName=self.invoker_role_name)
