# -*- coding: utf-8 -*-
from result_message import ResultMessage


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
        pass

ResultMessage
