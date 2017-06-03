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
your machine as long as your Google Cloud SDK has been installed and configured,
and you have installed the nose python testing framework.  To run this test from
the command line, try:
nosetests -v -s deployment-manager-tests.py
In order to create a temporary project in which to create and delete these test
deployments, follow the instructions in the project creation github example:
https://github.com/GoogleCloudPlatform/deploymentmanager-samples/tree/master/examples/v2/project_creation
Then, before running the tests, set the environment variables for your specific
project.  If "DEPLOYMENT_MANAGER_TEST_CREATE_NEW_PROJECT" is set to "TRUE", the
tests will be run in a new project.  If not, they will be run in your default
configured project.
"""

import json
import os
import parameterized
import subprocess
import time
import unittest
import yaml

# TODO(davidsac) Consider removing the description here or above
# The variables immediately below are used to create a new project in which to
# make test deployments, but only if the environment variable
# "DM_TEST_CREATE_NEW_PROJECT" is set to "TRUE".  Please see the example
# instructions on GitHub to see what value to assign each variable:
# https://github.com/GoogleCloudPlatform/deploymentmanager-samples/blob/master/examples/v2/project_creation/README.md
project_deployment_name = os.environ.get("DM_TEST_DEPLOYMENT_NAME")
project_to_create = os.environ.get("DM_TEST_PROJECT_TO_CREATE")
organization = os.environ.get("DM_TEST_ORGANIZATION_ID")
service_account_a = os.environ.get("DM_TEST_SERVICE_ACCOUNT_OWNER_A")
service_account_b = os.environ.get("DM_TEST_SERVICE_ACCOUNT_OWNER_B")
billing_account = os.environ.get("DM_TEST_BILLING_ACCOUNT")
account_to_create = os.environ.get("DM_TEST_SERVICE_ACCOUNT_TO_CREATE")

host_project = os.environ.get("DM_TEST_HOST_PROJECT")
create_new_project = os.environ.get("DM_TEST_CREATE_NEW_PROJECT") == "TRUE"
project_name = project_to_create if create_new_project else host_project
default_zone = "us-west1-b"
default_ssh_tunnel_port = 8890

environment = {"default_zone": default_zone, "project_name": project_name}
command_types = {"CREATE": "create", "DELETE": "delete", "UPDATE": "update", "DESCRIBE": "describe"}

with open("simple_tests.yaml", 'r') as stream:
  tests = yaml.load(stream)


def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  print "Running command: ", command
  try:
    result = subprocess.check_output(command,
                                     shell=True, stderr=subprocess.STDOUT)
    return result
  except subprocess.CalledProcessError as e:
    raise Exception(e.output)


def replace_placeholder_in_file(search_for, replace_with, file_to_modify):
  call("sed -i.backup 's/" + search_for + "/" + replace_with
       + "/' " + file_to_modify)


def parse_instances(deployment_name, resource_type_to_parse="compute.v1.instance"):
  """Creates a map of a deployment's GCE instances and associated IPs."""
  instance_map = {}
  raw_resources = call("gcloud deployment-manager resources list --deployment "
                       + deployment_name + " --format=json")
  parsed_resources = json.loads(raw_resources)
  for resource in parsed_resources:
    if resource["type"] == resource_type_to_parse:
      parsed_properties = yaml.load(resource["properties"])
      zone = parsed_properties["zone"]
      instance_map[resource["name"]] = {"zone": zone}
  for name in instance_map:
    instance_map[name]["ip"] = call("gcloud compute instances describe "
                                    + name + " --zone="
                                    + instance_map[name]["zone"]
                                    + " | grep \"networkIP\""
                                    " | sed 's/networkIP: //'")
  return instance_map


def get_instance_index_page(instance_name, local_port, ip):
  # TODO(davidsac) get this working
  """ call("gcloud compute ssh user@" + instance_name + " --zone "
          + default_zone + " -- -N -L " + str(local_port).strip() + ":"
          + str(ip).strip() + ":8080")
  
  return call("curl http://localhost:" + str(local_port))"""
  return "This is not a real page"


def gcloud_dm_command(command_type, deployment_name, project=project_name, properties=None, config_path=None):
  command = "gcloud deployment-manager deployments "+command_types[command_type]+" "+deployment_name+ " --project=" + project + " --format=json -q"
  if config_path:
    command += " --config " + config_path
  if properties:
    command += " --properties " + properties
  return call(command)


def create_deployment(deployment_name, config_path, project=project_name, properties=None):
  """Attempts to create a deployment."""
  print "Creating deployment of " + deployment_name + "..."
  gcloud_dm_command("CREATE", deployment_name, project, properties, config_path)
  print "Deployment created."


def update_deployment(deployment_name, config_path, project=project_name, properties=None):
  """Attempts to update a deployment."""
  print "Updating deployment of " + deployment_name + "..."
  gcloud_dm_command("UPDATE", deployment_name, project, properties, config_path)
  print "Deployment updated."


def check_deployment(deployment_name, project=project_name):
  raw_deployment = gcloud_dm_command("DESCRIBE", deployment_name, project)
  parsed_deployment = json.loads(raw_deployment)
  if parsed_deployment.get("deployment").get("operation").get("error"):
    raise Exception("An ERROR was found in the deployment's description.\n"
                    "---BEGIN DESCRIPTION---\n"
                    + raw_deployment + "---END DESCRIPTION---")


def delete_deployment(deployment_name, project=project_name):
  print "Deleting deployment of " + deployment_name + "..."
  gcloud_dm_command("DELETE", deployment_name, project)
  print "Deployment deleted."


def update_rolling_update_deployment(deployment_name, config_path, project=project_name):
  max_number_of_attempts = 3
  number_of_attempts = 0
  while max_number_of_attempts > number_of_attempts:
    try:
      update_deployment(deployment_name, config_path, project)
      break
    except Exception as e:
      if "412" in e.message:
        time.sleep(600)
        number_of_attempts += 1
      else:
        raise e
  number_of_attempts = 0
  while max_number_of_attempts > number_of_attempts:
    try:
      check_deployment(deployment_name)
      break
    except Exception as e:
      if "412" in e.message:
        time.sleep(600)
        number_of_attempts += 1
      else:
        raise e


def deploy(deployment_name, config_path):
  """Attempts to create and delete a deployment, raising any errors."""
  create_deployment(deployment_name, config_path)
  check_deployment(deployment_name)
  delete_deployment(deployment_name)


def deploy_http_server(deployment_name, config_path):
  """Tests deployments with GCE instances that host servers."""
  create_deployment(deployment_name, config_path)
  check_deployment(deployment_name)
  parsed_instances = parse_instances(deployment_name)
  for instance_name in parsed_instances:
    page = get_instance_index_page(instance_name, default_ssh_tunnel_port,
                                   parsed_instances[instance_name]["ip"])
    # TODO(davidsac) assert that the value is what is expected
  delete_deployment(deployment_name)


def setup_module():
  call("cp -a ../examples/v2/. .")
  if create_new_project:
    properties = "\"PROJECT_NAME:'" + project_to_create + "',ORGANIZATION_ID:'" + organization + "',BILLING_ACCOUNT:'" + billing_account + "',SERVICE_ACCOUNT_TO_CREATE:'" + account_to_create + "',SERVICE_ACCOUNT_OWNER_A:'" + service_account_a + "',SERVICE_ACCOUNT_OWNER_B:'" + service_account_b + "'\""
    create_deployment(project_deployment_name, "config-template.jinja", host_project, properties)


def teardown_module():
  call("rm -R -- */")
  if create_new_project:
    delete_deployment(project_deployment_name, host_project)


class TestSimpleDeployment(unittest.TestCase):
  """A test class for simple deployments.

  This is a test class for simple deployments that only need to be deployed in
  order to be considered working successfully.  It is not for deployments that
  need to be interacted with after being deployed in order to ensure that they
  were deployed successfully.
  """

  @parameterized.parameterized.expand(tests)
  def test_sequence(self, deployment_name, parameters):
    if parameters.get("replace-placeholders"):
      for replacement in parameters.get("replace-placeholders"):
        replace_with = replacement["replace-with"]
        if environment.get(replace_with):
          replace_with = environment.get(replace_with)
        replace_placeholder_in_file(replacement["search-for"], replace_with, replacement["file-to-modify"])
    if parameters.get("http-server"):
      deploy_http_server(deployment_name, parameters["config-path"])
    else:
      deploy(deployment_name, parameters["config-path"])


class TestComplexDeployment(object):
  """A test class for complex deployments needing post-deployment interaction.
  """

  def test_step_by_step_8_9_jinja(self):
    create_deployment("step-by-step-8-9-jinja",
                      "step_by_step_guide/step8_metadata_and_startup_scripts"
                      "/jinja/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-jinja")

    parsed_instances = parse_instances("step-by-step-8-9-jinja")
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name,
      #                                default_ssh_tunnel_port, ip)
      pass

    update_deployment("step-by-step-8-9-jinja", "step_by_step_guide/step9_update_a_deployment/jinja/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-jinja")
    
    parsed_instances = parse_instances("step-by-step-8-9-jinja")
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.
      # Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project="
           + project_name + " --zone="+parsed_instances[instance_name]["zone"])
      # rslt = get_instance_index_page(instance_name, port, ip)

    delete_deployment("step-by-step-8-9-jinja")

  def test_step_by_step_8_9_python(self):

    create_deployment("step-by-step-8-9-python",
                      "step_by_step_guide/step8_metadata_and_startup_scripts"
                      "/python/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-python")
    parsed_instances = parse_instances("step-by-step-8-9-python")
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name,
      #                                default_ssh_tunnel_port, ip)
      pass

    update_deployment("step-by-step-8-9-python", "step_by_step_guide/step9_update_a_deployment/python/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-python")

    parsed_instances = parse_instances("step-by-step-8-9-python")
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.
      # Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project="
           + project_name + " --zone="+parsed_instances[instance_name]["zone"])
      # rslt = get_instance_index_page(instance_name,
      #                                default_ssh_tunnel_port, ip)

    delete_deployment("step-by-step-8-9-python")

  def test_nodejs_l7_jinja(self):
    """Tests that the jinja NodeJS L7 application deploys correctly."""
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone,
                                "nodejs_l7/jinja/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone,
                                "nodejs_l7/jinja/application.yaml")
    deployment_name = "nodejs-l7-jinja"
    create_deployment(deployment_name, "nodejs_l7/jinja/application.yaml")
    check_deployment(deployment_name)
    # TODO(davidsac) all the steps specifically mentioned in the readme
    # are performed, but perhaps there are still more things to be done
    # to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone "
         + default_zone)
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone "
         + secondary_zone)
    forwarding_rule = call("gcloud compute forwarding-rules list | grep "
                           + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    else:
      print forwarding_rule
    delete_deployment(deployment_name)

  def test_nodejs_l7_python(self):
    """Tests that the python NodeJS L7 application deploys correctly."""
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone,
                                "nodejs_l7/python/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone,
                                "nodejs_l7/python/application.yaml")
    deployment_name = "nodejs-l7-python"
    create_deployment(deployment_name, "nodejs_l7/python/application.yaml")
    check_deployment(deployment_name)
    # TODO(davidsac) all the steps specifically mentioned in the readme
    # are performed, but perhaps there are still more things to be done
    # to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone "
         + default_zone)
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone "
         + secondary_zone)
    forwarding_rule = call("gcloud compute forwarding-rules list | grep "
                           + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    else:
      print forwarding_rule
    delete_deployment(deployment_name)

  def test_image_based_igm_jinja(self):
    # TODO(davidsac) this deployment has some more complex features like an
    # IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-jinja"
    create_deployment(deployment_name, "image_based_igm/image_based_igm.jinja", properties=
                      "\"targetSize:3,zone:" + default_zone
                      + ",maxReplicas:5\"")
    check_deployment(deployment_name)
    delete_deployment(deployment_name)

  def test_image_based_igm_python(self):
    # TODO(davidsac) this deployment has some more complex features like an
    # IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-python"
    create_deployment(deployment_name, "image_based_igm/image_based_igm.py", properties=
                      "\"targetSize:3,zone:" + default_zone
                      + ",maxReplicas:5\"")
    check_deployment(deployment_name)
    delete_deployment(deployment_name)

  def test_igm_updater_jinja(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary
    # to more thoroughly check that it works
    deployment_name = "igm-updater-jinja"
    create_deployment(deployment_name, "igm-updater/jinja/frontendver1.yaml")
    check_deployment(deployment_name)
    update_rolling_update_deployment(deployment_name,
                                "igm-updater/jinja/frontendver2.yaml")
    update_rolling_update_deployment(deployment_name,
                                "igm-updater/jinja/frontendver3.yaml")
    delete_deployment(deployment_name)

  def test_igm_updater_python(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary
    # to more thoroughly check that it works
    deployment_name = "igm-updater-python"
    create_deployment(deployment_name, "igm-updater/python/frontendver1.yaml")
    check_deployment(deployment_name)
    update_rolling_update_deployment(deployment_name,
                                "igm-updater/python/frontendver2.yaml")
    update_rolling_update_deployment(deployment_name,
                                "igm-updater/python/frontendver3.yaml")
    delete_deployment(deployment_name)

  def test_htcondor(self):
    # TODO(davidsac) read the tutorial and figure out how to deploy this
    pass
  
  
  def test_common_jinja(self):
    # TODO(davidsac) do I need to add tests for these?  It doesn't seem like
    # there are any deploymets here, just utility files for other deployments
    pass

  def test_common_python(self):
    # TODO(davidsac) do I need to add tests for these?  It doesn't seem like
    # there are any deploymets here, just utility files for other deployments
    pass
  
  def test_step_by_step_10_jinja(self):
    """ self.create("step-by-step-10-jinja",
                "step_by_step_guide/step10_use_python_templates"
                "/jinja/use-jinja-template-with-modules.yaml")
    """
    """ TODO(davidsac) when I have time, read through this
    example and make sure my test will deploy it correctly
    """
    pass

  def test_step_by_step_10_python(self):
    """ self.create("step-by-step-10-python",
    "step_by_step_guide/step10_use_python_templates"
    "/python/use-python-template-with-modules.yaml")
    """
    """ TODO(davidsac) when I have time, read through this
    example and make sure my test will deploy it correctly
    """
    pass
  
  def test_vpn_auto_subnet(self):
    # TODO(davidsac) How do I test this?
    # TODO(davidsac) figure out what values to use for the parameters
    # deploy("vpn-auto-subnet", "vpn-auto-subnet.jinja", properties=
    #        "peerIp=PEER_VPN_IP,sharedSecret=SECRET,sourceRanges=PEERED_RANGE")
    pass
