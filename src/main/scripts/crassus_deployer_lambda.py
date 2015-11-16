from crassus import Crassus


def handler(event, context):
    crassus = Crassus(event, context)
    crassus.deploy()
