#!/usr/bin/env python

import sys
import json


def format_(credentials):
    key_map = {"SecretAccessKey": "AWS_SECRET_ACCESS_KEY",
               "SessionToken": "AWS_SESSION_TOKEN",
               "AccessKeyId": "AWS_ACCESS_KEY_ID"}

    for key, value in key_map.items():
        print "export {0}={1}".format(value, credentials[key])
    print "export AWS_SECURITY_TOKEN={0}".format(credentials['SessionToken'])


if __name__ == "__main__":
    format_(json.loads(sys.stdin.read())['Credentials'])
