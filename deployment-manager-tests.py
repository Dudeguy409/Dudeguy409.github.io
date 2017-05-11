# Copyright 2017 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A program that automatically tests that the Deployment Manager examples work.

This is a nose test program that checks that all of the GitHub examples for the
Google Cloud Platform's Deployment Manager are being deployed correctly.  These
tests should detect breaking changes in the example code and breaking changes
in the uderlying APIs that the examples use.  This program can be run locally on
your machine as long as your cloud SDK has been installed and configured, and
have the nose python testing framework installed.  To run this test from the
command line, try:
nosetests -v deployment-manager-tests.py
"""

import json
import os
import subprocess
import time

deployment_name = os.environ.get("DEPLOYMENT_MANAGER_TEST_DEPLOYMENT_NAME")
project_to_create = os.environ.get("DEPLOYMENT_MANAGER_TEST_PROJECT_NAME")
organization = os.environ.get("DEPLOYMENT_MANAGER_TEST_ORGANIZATION_ID")
service_account_a = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_A")
service_account_b = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_B")
service_account_c = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_C")
billing_account = os.environ.get("DEPLOYMENT_MANAGER_TEST_BILLING_ACCOUNT")
account_to_create = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_TO_CREATE")
create_new_project = os.environ.get("DEPLOYMENT_MANAGER_TEST_CREATE_NEW_PROJECT")=="TRUE"

def setup_module(module):
  if create_new_project:
    call("gcloud deployment-manager deployments create "+deployment_name+" --config config-template.jinja --properties \"PROJECT_NAME:'"+project_to_create+"',ORGANIZATION_ID:'"+organization+"',BILLING_ACCOUNT:'"+billing_account+"',SERVICE_ACCOUNT_TO_CREATE:'"+account_to_create+"',SERVICE_ACCOUNT_OWNER_A:'"+service_account_a+"',SERVICE_ACCOUNT_OWNER_B:'"+service_account_b+"',SERVICE_ACCOUNT_OWNER_C:'"+service_account_c+"'\"")

def teardown_module(module):
  if create_new_project:
    call("gcloud deployment-manager deployments delete " + deployment_name + " -q")

def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  print "Running command: ", command
  try:
    result = subprocess.check_output(command,
                                     shell=True, stderr=subprocess.STDOUT)
    print result
    return result
  except subprocess.CalledProcessError as  e:
    raise Exception(e.output)

class TestSimpleDeployment(object):
  """A test class for simple deployments.

  This is a test class for simple deployments that only need to be deployed in
  order to be considered working successfully.  It is not for deployments that
  need to be interacted with after being deployed in order to ensure that they
  were deployed successfully.
  """

  def deploy(self, deployment_name, yaml_path):
    """Attempts to create and delete a deployment, raising any errors."""
    deployment_create_command = "gcloud deployment-manager deployments create " + deployment_name + " --config examples/v2/" + yaml_path
    deployment_describe_command = "gcloud deployment-manager deployments describe " + deployment_name + " --format=json"
    deployment_delete_command = "gcloud deployment-manager deployments delete " + deployment_name + " -q"
    if create_new_project:
      deployment_create_command += " --project=" + project_to_create
      deployment_describe_command += " --project=" + project_to_create
      deployment_delete_command += " --project=" + project_to_create

    print "Beginning deployment of " + deployment_name + "..."  
    call(deployment_create_command)
    print "Deployment complete."
    raw_deployment = call(deployment_describe_command)
    parsed_deployment = json.loads(raw_deployment)
    if parsed_deployment.get("deployment").get("operation").get("error"):
      raise Exception("An ERROR was found in the deployment's description.\n"
                      "---BEGIN DESCRIPTION---\n"
                      + raw_deployment + "---END DESCRIPTION---")
    print "Deleting deployment..."
    call(deployment_delete_command)
    print "Deployment deleted."

  def test_build_configuration_vm(self):
    self.deploy("build-config-vm", "build_configuration/vm.yaml")

  def test_build_configuration_vm_and_bigquery(self):
    self.deploy("build-config-vm-and-bigquery",
                "build_configuration/vm_and_bigquery.yaml")
