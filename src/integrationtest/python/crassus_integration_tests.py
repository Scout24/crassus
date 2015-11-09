from __future__ import print_function
import uuid
import unittest
import json

import re
import boto3


class CrassusIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.iam_client = boto3.client('iam')
        current_account = re.compile('arn:aws:iam::(\d{12}):.*') \
            .match(self.iam_client.list_roles()['Roles'][0]['Arn']).group(1)
        policy = json.dumps(
            {
                "Statement": [
                    {"Effect":"Allow", "Principal":
                        {"AWS": "arn:aws:iam::{0}:root".format(current_account)},
                     "Action": ["sts:AssumeRole"]}
                ]
            })

        self.invoker_role_name = "crassus-invoker-it-{0}".format(uuid.uuid1())
        self.invoker_role = self.iam_client.create_role(RoleName=self.invoker_role_name,
                                                        AssumeRolePolicyDocument=policy)


    def test_create_stacks_and_update(self):
        print(self.invoker_role)

    def tearDown(self):
        if self.invoker_role is None:
            pass

        self.iam_client.delete_role(RoleName=self.invoker_role_name)