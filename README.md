[![Build Status](https://travis-ci.org/ImmobilienScout24/crassus.svg?branch=master)](https://travis-ci.org/ImmobilienScout24/crassus)
[![Code Health](https://landscape.io/github/ImmobilienScout24/crassus/master/landscape.svg?style=flat)](https://landscape.io/github/ImmobilienScout24/crassus/master)
[![Coverage Status](https://coveralls.io/repos/ImmobilienScout24/crassus/badge.svg?branch=master&service=github)](https://coveralls.io/github/ImmobilienScout24/crassus?branch=master)

# This project is DEPRECATED and not any longer supported

# crassus
Cross Account Smart Software Update Service

## Deployer
### Event interface
Actual a SNS with a json payload is used to trigger crassus. The payload should look like this:

```json
      {
        "version": 1,
        "stackName": "sample-stack",
        "region": "<AWS-REGION-ID>",
        "parameters": {
            "parameter1": "value1",
            "parameter2": "value2",
        }
      }
```


Sample event as expected from deployer
```json
{
  "Records": [
    {
      "EventVersion": "1.0",
      "EventSubscriptionArn": "<SUBSCRIPTION ARN>",
      "EventSource": "aws: sns",
      "Sns": {
        "SignatureVersion": "1",
        "Timestamp": "2015-10-23T11: 01: 16.140Z",
        "Signature": "<SIGNATURE>",
        "SigningCertUrl": "<SIGNING URL>",
        "MessageId": "<MESSAGE ID>",
        "Message": "{
          \"version\": 1,
          \"stackName\": \"sample-stack\",
          \"region\": \"eu-west-1\",
          \"parameters\": {
            \"InstanceType\": \"t2.micro\"
          }
        }",
        "MessageAttributes": {
        },
        "Type": "Notification",
        "UnsubscribeUrl": "<UNSUBSCRIBE URL>",
        "TopicArn": "<TOPIC ARN>",
        "Subject": "None"
      }
    }
  ]
}
```
## Deploy the Deployer

One possibility to deploy crassus is to use CloudFormation.

To do it the simple way take a look at [cfn-sphere](https://github.com/marco-hoyer/cfn-sphere)

In ``cfn-sphere`` directory you can find the template and configuration file for cfn-sphere usage.

## Smoke Testing CRASSUS
The goal is to have a simple integration test which involves the infrastructure on which CRASSUS is relying and
that is represented by the CloudFormation template.

To determine if CRASSUS can successfully update a CloudFormation stack we use the [python-docker-hello-world-webapp]
(https://github.com/ImmobilienScout24/python-docker-hello-world-webapp#python-docker-hello-world-webapp) as target
application stack.

### Steps

1. Create test role which has only permission to use SNS in the current account
1. Create CRASSUS test stack from latest version, authorize the test role to send update messages
1. Create target application stack
1. Use the test role to send an update message with an updated stack parameter
1. Test that the parameter of the target application successfully was successfully updated
1. If the test was successful, delete the the target application stack, the
test role and the CRASSUS test stack
