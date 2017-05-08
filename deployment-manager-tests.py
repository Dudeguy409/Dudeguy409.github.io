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

deployment_name = os.environ["DEPLOYMENT_MANAGER_TEST_DEPLOYMENT_NAME"]
project_to_create = os.environ["DEPLOYMENT_MANAGER_TEST_PROJECT_NAME"]
organization = os.environ["DEPLOYMENT_MANAGER_TEST_ORGANIZATION_ID"]
service_account_a = os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_A"]
service_account_b = os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_B"]
service_account_c = os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_C"]
billing_account = os.environ["DEPLOYMENT_MANAGER_TEST_BILLING_ACCOUNT"]
account_to_create = os.environ["DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_TO_CREATE"]

def setup_module(module):
  call_async("gcloud deployment-manager deployments create "+deployment_name+" --async --format=json --config config-template.jinja --properties \"PROJECT_NAME:'"+project_to_create+"',ORGANIZATION_ID:'"+organization+"',BILLING_ACCOUNT:'"+billing_account+"',SERVICE_ACCOUNT_TO_CREATE:'"+account_to_create+"',SERVICE_ACCOUNT_OWNER_A:'"+service_account_a+"',SERVICE_ACCOUNT_OWNER_B:'"+service_account_b+"',SERVICE_ACCOUNT_OWNER_C:'"+service_account_c+"'\"", False)
  
def teardown_module(module):
  call_async("gcloud deployment-manager deployments delete " + deployment_name + " -q --async --format=json", False)

def call_async(command, is_in_created_project):
  """Runs the command and returns the output, possibly as an exception."""
  if is_in_created_project:
    command+=" --project="+project_to_create 
  print "Running command: ", command

  popen = subprocess.Popen( command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  output,error = popen.communicate()
  print "error:", error
  if popen.returncode != 0:
    raise Exception(error)
  print "output: ", output
  parsed_result = json.loads(output)
  operation_name = ""
  if isinstance(parsed_result, list):
    operation_name = (parsed_result[0])["name"]
  else:
    operation_name = parsed_result["name"]
  poll_command = "gcloud deployment-manager operations describe " + operation_name+" --format=json"
  if is_in_created_project:
    poll_command+=" --project="+project_to_create
  print "poll command: ", poll_command
  try:
    timeout=0
    while timeout<90:
      time.sleep(1)
      poll_popen = subprocess.Popen( poll_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      poll_output, poll_error = poll_popen.communicate()
      if poll_popen.returncode != 0:
        raise Exception(poll_error)
      parsed_poll_result = json.loads(poll_output)
      if parsed_poll_result.get("status")=="DONE":
        poll_result_error = parsed_poll_result.get("error")
        if poll_result_error:
          print "poll result error: ", poll_result_error
          raise Exception(json.dumps(poll_result_error))
        print "poll result: ", poll_output
        return poll_output
      timeout += 1
  except subprocess.CalledProcessError as  e:
    print "CalledProcessError: ", e
    raise Exception(e.output)

def call_sync(command):
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
    print "Beginning deployment of " + deployment_name + "..."
    call_async("gcloud deployment-manager deployments create " + deployment_name +
              " --format=json --async --config examples/v2/" + yaml_path, True)
    print "Deployment complete."
    raw_deployment = call_sync("gcloud deployment-manager deployments describe "
                               + deployment_name + " --format=json" + " --project="+project_to_create)
    parsed_deployment = json.loads(raw_deployment)
    if parsed_deployment.get("deployment").get("operation").get("error"):
      raise Exception("An ERROR was found in the deployment's description.\n"
                      "---BEGIN DESCRIPTION---\n"
                      + raw_deployment + "---END DESCRIPTION---")
    print "Queueing deployment for deletion..."
    call_async("gcloud deployment-manager deployments delete " + deployment_name + " -q --async --format=json", True)
    print "Deployment queued for deletion."

  def test_build_configuration_vm(self):
    self.deploy("build-config-vm", "build_configuration/vm.yaml")

  def test_build_configuration_vm_and_bigquery(self):
    self.deploy("build-config-vm-and-bigquery",
                "build_configuration/vm_and_bigquery.yaml")
