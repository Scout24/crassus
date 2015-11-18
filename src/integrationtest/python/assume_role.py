#!/usr/bin/env python

import boto3
import os


def assume_role():
    invoker_role_arn = os.environ["INVOKER_ROLE_ARN"]
    sts_client = boto3.client('sts')
    return sts_client.assume_role(
        RoleArn=invoker_role_arn,
        RoleSessionName='integration_test')['Credentials']


def format_(credentials):
    key_map = {"SecretAccessKey": "AWS_SECRET_ACCESS_KEY",
               "SessionToken": "AWS_SECURITY_TOKEN",
               "AccessKeyId": "AWS_ACCESS_KEY_ID"}

    for key, value in key_map.items():
        print "export {0}={1}".format(value, credentials[key])


if __name__ == "__main__":
    format_(assume_role())