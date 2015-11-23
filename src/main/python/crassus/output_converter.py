# -*- coding: utf-8 -*-
from __future__ import print_function

from gaius_message import GaiusMessage


class OutputConverter(object):

    """
    Output converter class to do the message conversion for the command
    line client.
    """

    event = None
    context = None

    def __init__(self, event, context):
        super(OutputConverter, self).__init__()
        self.event = event
        self.context = context

    def convert(self):
        print('convert:', self.event, self.context)

GaiusMessage
