# -*- coding: utf-8 -*-


class DeploymentResponse(dict):

    """
    A message that crassus returns for events such as fail or success
    events for stack deployments/updates. These messages will be
    transmitted as JSON encoded strings, used by Gaius.

    It is initialized with the following parameters:
    - status: STATUS_FAILURE or STATUS_SUCCESS
    - stack_name: the stack name the notification message stands for
    - version: a version identifier for the message. Defaults as '1.0'
    - message: the textual message for the notification.
    """

    version = '1.1'
    STATUS_SUCCESS = 'success'
    STATUS_FAILURE = 'failure'

    EMITTER_CRASSUS = 'crassus'
    EMITTER_CFN = 'cloudformation'

    def __init__(self, status, message, stack_name, timestamp, emitter):
        self['version'] = self.version
        self['emitter'] = emitter
        self['stackName'] = stack_name
        self['timestamp'] = timestamp
        self['status'] = status
        self['message'] = message
