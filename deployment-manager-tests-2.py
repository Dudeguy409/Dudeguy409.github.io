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

import json
import os
import subprocess
import yaml
import time

project_deployment_name = os.environ.get("DM_TEST_DEPLOYMENT_NAME")
host_project = os.environ.get("DM_TEST_HOST_PROJECT")
create_new_project = os.environ.get("DM_TEST_CREATE_NEW_PROJECT") == "TRUE"
project_name = project_to_create if create_new_project else host_project
default_zone = "us-west1-b"
default_ssh_tunnel_port = 8890


def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  print "Running command: ", command
  try:
    result = subprocess.check_output(command,
                                     shell=True, stderr=subprocess.STDOUT)
    return result
  except subprocess.CalledProcessError as e:
    raise Exception(e.output)


def delete_deployment(deployment_name):
  deployment_delete_command = ("gcloud deployment-manager deployments delete "
                               + deployment_name + " -q --project="
                               + project_name)
  print "Deleting deployment of " + deployment_name + "..."
  call(deployment_delete_command)
  print "Deployment deleted."

class TestSimpleDeployment(object):
 

  def test_build_configuration_vm(self):
    delete_deployment("step-by-step-5-python")


