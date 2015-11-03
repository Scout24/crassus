# Smoke Testing CRASSUS
The goal is to have a simple integration test which involves the infrastructure on which CRASSUS is relying and
that is represented by the CloudFormation template.

To determine if CRASSUS can successfully update a CloudFormation stack we use the [python-docker-hello-world-webapp]
(https://github.com/ImmobilienScout24/python-docker-hello-world-webapp#python-docker-hello-world-webapp) as target
application stack.

## Steps

1. Create test role which has zero permission in the current account
1. Create CRASSUS test stack from latest version, authorize the test role to send update messages 
1. Create target application stack
1. Use the test role to send an update message with an updated stack parameter
1. Test that the parameter of the target application successfully was successfully updated
1. If the test was successful, delete the the target application stacl, the test role and the CRASSUS test stack
