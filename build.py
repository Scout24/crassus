#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import boto3
import zipfile
import subprocess

from datetime import datetime
from pybuilder.core import use_plugin, init, task
from pybuilder.plugins.python.install_dependencies_plugin import as_pip_argument

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
#use_plugin("python.coverage")

name = 'crassus'
summary = 'AWS lambda function for deployment automation'
description = """
    AWS lambda function for deployment automation, which makes use of
    sns/sqs for trigger and backchannel."""
license = 'Apache License 2.0'
url = 'https://github.com/ImmobilienScout24/crassus'
version = 0.1
default_task = ['clean', 'analyze', 'package']


@init
def set_properties(project):
    project.depends_on("boto3")
    project.build_depends_on("unittest2")
    project.build_depends_on("mock")
    #project.set_property('coverage_break_build', False)

    project.set_property('distutils_classifiers', [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration'
    ])


@init(environments='teamcity')
def set_properties_for_teamcity_builds(project):
    project.set_property('teamcity_output', True)
    project.version = '%s-%s' % (project.version,
                                 os.environ.get('BUILD_NUMBER', 0))
    project.default_task = [
        'clean',
        'install_build_dependencies',
        'publish',
        'package_lambda_code'
    ]
    project.set_property('install_dependencies_index_url',
                         os.environ.get('PYPIPROXY_URL'))


# ------------------ AWS Lambda deployment logic starts here -------------------


def zip_recursive(archive, directory, folder="", excludes=None):
    """Zip directories recursively"""
    for item in os.listdir(directory):
        if not item in excludes:
            if os.path.isfile(os.path.join(directory, item)):
                archive.write(os.path.join(directory, item),
                              os.path.join(folder, item),
                              zipfile.ZIP_DEFLATED)
            elif os.path.isdir(os.path.join(directory, item)):
                zip_recursive(archive,
                              os.path.join(directory, item),
                              folder=os.path.join(folder, item),
                              excludes=excludes)


def copy_dir_content_to_ziproot(archive, directory):
    """Put every file found in directory to root layer of the zipfile"""
    for item in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, item)):
            archive.write(os.path.join(directory, item),
                          item, zipfile.ZIP_DEFLATED)


def package_dependencies(project, target_directory):
    """Get all dependencies from project and install them to given dir"""
    dependencies = map(lambda dep: as_pip_argument(dep), project.dependencies)
    pip_cmd = 'pip install --target {0} {1}'
    for dependency in dependencies:
        cmd = pip_cmd.format(target_directory, dependency).split()
        subprocess.Popen(cmd, stdout=subprocess.PIPE)


@task
def package_lambda_code(project):
    build_dir = 'target/dist/crassus-{0}/'.format(version)
    archive = zipfile.ZipFile('target/crassus.zip', 'w')
    package_dependencies(project, build_dir)
    zip_recursive(archive, build_dir, excludes=['scripts'])
    copy_dir_content_to_ziproot(archive, '{0}/scripts/'.format(build_dir))
    archive.close()


@task
def upload_zip_to_s3():
    timestamp = time.time()
    formatted_timestamp = datetime.fromtimestamp(timestamp)
    formatted_timestamp = formatted_timestamp.strftime('%Y%m%d%H%M%S')
    keyname = 'crassus-{0}.zip'.format(formatted_timestamp)
    s3 = boto3.resource('s3')
    data = open('target/crassus.zip', 'rb')
    s3.Bucket('crassus-zips').put_object(Key=keyname, Body=data)
