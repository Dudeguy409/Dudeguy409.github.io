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
your machine as long as your Google Cloud SDK has been installed and configured, and
you have installed the nose python testing framework.  To run this test from the
command line, try:
nosetests -v deployment-manager-tests.py

In order to create a temporary project in which to create and delete these test deployments, follow the instrictions in the project creation github example:
https://github.com/GoogleCloudPlatform/deploymentmanager-samples/tree/master/examples/v2/project_creation

Then, before running the tests, set the environment variables for your specific project.  If "DEPLOYMENT_MANAGER_TEST_CREATE_NEW_PROJECT" is set to "TRUE", the tests will be run in a new project.  If not, they will be run in your default configured project. 
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
    
  """  
  def test_waiter(self):
    # Replace the placeholder "ZONE_TO_RUN" with an actual zone
    call("sed -i.backup 's/ZONE_TO_RUN/us-west1-b/' examples/v2/waiter/config.yaml")
    self.deploy("waiter", "waiter/config.yaml")
  
  def test_vpn_auto_subnet(self):
    # TODO we could probably hack the traditional deploy method to work with this by adding a properties parameter
    # TODO figure out what values to use for the parameters
    "gcloud deployment-manager deployments create vpn-auto-subnet --config vpn-auto-subnet.jinja --project PROJECT_NAME --properties \"peerIp=PEER_VPN_IP,sharedSecret=SECRET,sourceRanges=PEERED_RANGE\""

  
  def test_ssl(self):
    self.deploy("ssl", "ssl.ssl.yaml")
    
  def test_vm_startup_script(self):
    # TODO may want to refactor my deploy method to be broken up into two separate methods to test that the script is actually working
    # TODO create an SSH tunnel to connect 
    # TODO test both versions
    pass
  
  def test_step_by_step_2(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_to_create + "/' examples/v2/step_by_step_guide/step2_create_a_configuration/two-vms.yaml")
    self.deploy("step_by_step_2", "step_by_step_guide/step2_create_a_configuration/two-vms.yaml")
  
  def test_step_by_step_4(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_to_create + "/' examples/v2/step_by_step_guide/step4_use_references/two-vms.yaml")
    self.deploy("step_by_step_4", "step_by_step_guide/step4_use_references/two-vms.yaml")
  
  def test_step_by_step_5(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_to_create + "/' examples/v2/step_by_step_guide/step5_create_a_template/jinja/two-vms.yaml")
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_to_create + "/' examples/v2/step_by_step_guide/step5_create_a_template/python/two-vms.yaml")
    self.deploy("step_by_step_5", "step_by_step_guide/step5_create_a_template/python/two-vms.yaml")
    self.deploy("step_by_step_5", "step_by_step_guide/step5_create_a_template/jinja/two-vms.yaml")
    
  def test_step_by_step_6(self):
    self.deploy("step_by_step_6", "step_by_step_guide/step4_use_references/two-vms.yaml")
    
  def test_step_by_step_7(self):
    self.deploy("step_by_step_7", "step_by_step_guide/step4_use_references/two-vms.yaml")
    
  def test_step_by_step_8(self):
    self.deploy("step_by_step_8", "step_by_step_guide/step4_use_references/two-vms.yaml")
    
  def test_step_by_step_9(self):
    self.deploy("step_by_step_9", "step_by_step_guide/step4_use_references/two-vms.yaml")
    
  def test_step_by_step_10(self):
    self.deploy("step_by_step_10", "step_by_step_guide/step4_use_references/two-vms.yaml")
  """
  
  
  
  
