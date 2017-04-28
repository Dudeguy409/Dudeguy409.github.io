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
nosetests -v -s deployment-manager-tests.py
"""

import json
import subprocess
import os

def setup_module(module):
  call("gcloud deployment-manager deployments create "+os.environ["DEPLOYMENT_MANAGER_TEST_DEPLOYMENT_NAME"]+" --config config-template.jinja --properties \"PROJECT_NAME:'"+os.environ["DEPLOYMENT_MANAGER_TEST_PROJECT_NAME"]+"',ORGANIZATION_ID:\"'"+os.environ["DEPLOYMENT_MANAGER_TEST_ORGANIZATION_ID"]+"'\",BILLING_ACCOUNT:'"+os.environ["DEPLOYMENT_MANAGER_TEST_BILLING_ACCOUNT"]+"',SERVICE_ACCOUNT_TO_CREATE:'"+os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_TO_CREATE"]+"',SERVICE_ACCOUNT_OWNER_A:'\""+os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_A"]+"\"',SERVICE_ACCOUNT_OWNER_B:'\""+os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_B"]+"\"'\"")
    
def teardown_module(module):
  call("gcloud deployment-manager deployments delete " + os.environ["DEPLOYMENT_MANAGER_TEST_DEPLOYMENT_NAME"] + " -q --async")
    
def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  try:
    return subprocess.check_output(command,
                                   shell=True, stderr=subprocess.STDOUT)
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
    print "Beginning deployment of " + deployment_name + "..."
    call("gcloud deployment-manager deployments create " + deployment_name +
              " --config examples/v2/" + yaml_path + " --project="+os.environ["DEPLOYMENT_MANAGER_TEST_PROJECT_NAME"])
    print "Deployment complete."
    raw_deployment = call("gcloud deployment-manager deployments describe "
                               + deployment_name + " --format=json" + " --project="+os.environ["DEPLOYMENT_MANAGER_TEST_PROJECT_NAME"])
    parsed_deployment = json.loads(raw_deployment)
    if parsed_deployment.get("deployment").get("operation").get("error"):
      raise Exception("An ERROR was found in the deployment's description.\n"
                      "---BEGIN DESCRIPTION---\n"
                      + raw_deployment + "---END DESCRIPTION---")
    print "Queueing deployment for deletion..."
    call("gcloud deployment-manager deployments delete " + deployment_name + " -q --async" + " --project="+os.environ["DEPLOYMENT_MANAGER_TEST_PROJECT_NAME"])
    print "Deployment queued for deletion."

  def test_build_configuration_vm(self):
    self.deploy("build-config-vm", "build_configuration/vm.yaml")

  def test_build_configuration_vm_and_bigquery(self):
    self.deploy("build-config-vm-and-bigquery",
                "build_configuration/vm_and_bigquery.yaml")
