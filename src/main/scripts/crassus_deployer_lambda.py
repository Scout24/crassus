from crassus import Crassus
from crassus.output_converter import OutputConverter


def handler(event, context):
    crassus = Crassus(event, context)
    crassus.deploy()


def cfn_output_converter(event, context):
    """
    Convert an AWS CloudFormation output message to our defined
    ResultMessage format.
    """
    output_converter = OutputConverter(event, context)
    output_converter.convert()
