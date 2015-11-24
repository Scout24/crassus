import os
import json

my_dir = os.path.dirname(os.path.realpath(__file__))


def load_fixture_json(name):
    """
    Load a fixture file from the fixture directory, and return its JSON
    parsed value.
    """
    with open(os.path.join(my_dir, 'fixtures', name)) as fp:
        return json.load(fp)
