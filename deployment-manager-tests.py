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
This is a test program that checks that all of the GitHub examples for the
Google Cloud Platform's Deployment Manager are being deployed correctly.  These
tests should detect breaking changes in the example code and breaking changes
in the uderlying APIs that the examples use.  This program can be run locally on
your machine as long as your Google Cloud SDK has been installed and configured,
and you have installed all of the necessary python packages.
For information on how to run these tests, try:
python deployment-manager-tests.py -h
"""

import argparse
import json
import subprocess
import sys
import time
import unittest
import parameterized
import yaml


new_proj_deployment_name = None
new_proj_name = None
new_proj_org = None
new_proj_service_account_a = None
new_proj_service_account_b = None
new_proj_billing_account = None
new_proj_account_to_create = None

host_project = None
create_new_project = None
project_name = None
default_zone = None
ssh_tunnel_port = None

environment = None
command_types = {"CREATE": "create", "DELETE": "delete",
                 "UPDATE": "update", "DESCRIBE": "describe"}

with open("simple_tests.yaml", "r") as stream:
  tests = yaml.load(stream)
  
class CustomCalledProcessError(Exception):

  def __init__(self, cmd, output, returncode):		
    message = "Command '" + cmd +"' returned non-zero exit status " + str(returncode) + " and output:\n" + output		
    super(CustomCalledProcessError, self).__init__(message)


def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  print "Running command: ", command
  try:
    result = subprocess.check_output(command,
                                     shell=True, stderr=subprocess.STDOUT)
    return result
  except subprocess.CalledProcessError as e:
    raise CustomCalledProcessError(e.cmd, e.output, e.returncode)


def replace_placeholder_in_file(search_for, replace_with, file_to_modify):
  call("sed -i.backup 's/" + search_for + "/" + replace_with
       + "/' " + file_to_modify)


def parse_instances(deployment_name, project,
                    resource_type_to_parse="compute.v1.instance"):
  """Creates a map of a deployment's GCE instances and associated IPs."""
  instance_map = {}
  raw_resources = call("gcloud deployment-manager resources list --deployment "
                       + deployment_name + " --project="
                       + project + " --format=json")
  parsed_resources = json.loads(raw_resources)
  for resource in parsed_resources:
    if resource["type"] == resource_type_to_parse:
      parsed_properties = yaml.load(resource["properties"])
      zone = parsed_properties["zone"]
      instance_map[resource["name"]] = {"zone": zone}
  for name in instance_map:
    instance_map[name]["ip"] = call("gcloud compute instances describe " + name
                                    + " --project=" + project + " --zone="
                                    + instance_map[name]["zone"]
                                    + " | grep \"networkIP\" "
                                    "| sed 's/networkIP: //'")
  return instance_map


def get_instance_index_page(instance_name, local_port, ip, project):
  # TODO(davidsac) get this working
  """
  call("gcloud compute ssh user@" + instance_name + " --zone "
          + default_zone + " -- -N -L " + str(local_port).strip() + ":"
          + str(ip).strip() + ":8080" + " --project="+project)
  return call("curl http://localhost:" + str(local_port))
  """
  return "This is not a real page"


def gcloud_dm_command(command_type, deployment_name, project,
                      properties=None, config_path=None):
  command = ("gcloud deployment-manager deployments "
             + command_types[command_type] + " " + deployment_name
             + " --project=" + project + " --format=json -q")
  if config_path:
    command += " --config " + config_path
  if properties:
    command += " --properties " + properties
  return call(command)


def create_deployment(deployment_name, config_path, project, properties=None):
  """Attempts to create a deployment."""
  print "Creating deployment of " + deployment_name + "..."
  gcloud_dm_command("CREATE", deployment_name, project, properties, config_path)
  print "Deployment created."


def update_deployment(deployment_name, config_path, project, properties=None):
  """Attempts to update a deployment."""
  print "Updating deployment of " + deployment_name + "..."
  gcloud_dm_command("UPDATE", deployment_name, project, properties, config_path)
  print "Deployment updated."


def check_deployment(deployment_name, project):
  raw_deployment = gcloud_dm_command("DESCRIBE", deployment_name, project)
  parsed_deployment = json.loads(raw_deployment)
  if parsed_deployment.get("deployment").get("operation").get("error"):
    raise Exception("An ERROR was found in the deployment's description.\n"
                    "---BEGIN DESCRIPTION---\n"
                    + raw_deployment + "---END DESCRIPTION---")


def delete_deployment(deployment_name, project):
  print "Deleting deployment of " + deployment_name + "..."
  gcloud_dm_command("DELETE", deployment_name, project)
  print "Deployment deleted."


def update_rolling_update_deployment(deployment_name, config_path, project):
  max_number_of_attempts = 3
  number_of_attempts = 0
  while max_number_of_attempts > number_of_attempts:
    try:
      update_deployment(deployment_name, config_path, project)
      break
    except CustomCalledProcessError as e:
      if "412" in e.message:
        time.sleep(600)
        number_of_attempts += 1
  number_of_attempts = 0
  while max_number_of_attempts > number_of_attempts:
    try:
      check_deployment(deployment_name, project)
      break
    except CustomCalledProcessError as e:
      if "412" in e.message:
        time.sleep(600)
        number_of_attempts += 1


def deploy(deployment_name, config_path, project):
  """Attempts to create and delete a deployment, raising any errors."""
  create_deployment(deployment_name, config_path, project)
  check_deployment(deployment_name, project)
  delete_deployment(deployment_name, project)


def deploy_http_server(deployment_name, config_path, project):
  """Tests deployments with GCE instances that host servers."""
  create_deployment(deployment_name, config_path, project)
  check_deployment(deployment_name, project)
  parsed_instances = parse_instances(deployment_name, project)
  for instance_name in parsed_instances:
    page = get_instance_index_page(instance_name, ssh_tunnel_port,
                                   parsed_instances[instance_name]["ip"],
                                   project)
    # TODO(davidsac) assert that the value is what is expected
  delete_deployment(deployment_name, project)


def setUpModule():
  if create_new_project:
    properties = ("\"PROJECT_NAME:'" + new_proj_name + "',ORGANIZATION_ID:'"
                  + new_proj_org
                  + "',BILLING_ACCOUNT:'" + new_proj_billing_account
                  + "',SERVICE_ACCOUNT_TO_CREATE:'" + new_proj_account_to_create
                  + "', SERVICE_ACCOUNTS: " + new_proj_service_account_a + " " + new_proj_service_account_b
                  + "\"")
    create_deployment(new_proj_deployment_name, "config-template.jinja",
                      host_project, properties)
  call("cp -a ../examples/v2/. .")


def tearDownModule():
  call("rm -R -- */")
  if create_new_project:
    delete_deployment(new_proj_deployment_name, host_project)
'''
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
        replace_placeholder_in_file(replacement["search-for"],
                                    replace_with, replacement["file-to-modify"])

    if parameters.get("http-server"):
      deploy_http_server(deployment_name,
                         parameters["config-path"], project_name)
    else:
      deploy(deployment_name, parameters["config-path"], project_name)
'''
class TestComplexDeployment(unittest.TestCase):
  """A test class for complex deployments needing post-deployment interaction.
  """
  '''
  def test_step_by_step_8_9_jinja(self):
    create_deployment("step-by-step-8-9-jinja",
                      "step_by_step_guide/step8_metadata_and_startup_scripts"
                      "/jinja/config-with-many-templates.yaml", project_name)
    check_deployment("step-by-step-8-9-jinja", project_name)

    parsed_instances = parse_instances("step-by-step-8-9-jinja", project_name)
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name,
      #                                ssh_tunnel_port, ip, project_name)
      pass

    update_deployment("step-by-step-8-9-jinja",
                      "step_by_step_guide/step9_update_a_deployment"
                      "/jinja/config-with-many-templates.yaml", project_name)
    check_deployment("step-by-step-8-9-jinja", project_name)

    parsed_instances = parse_instances("step-by-step-8-9-jinja", project_name)
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.
      # Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project="
           + project_name + " --zone="+parsed_instances[instance_name]["zone"])
      # rslt = get_instance_index_page(instance_name, port, ip, project_name)

    delete_deployment("step-by-step-8-9-jinja", project_name)

  def test_step_by_step_8_9_python(self):

    create_deployment("step-by-step-8-9-python",
                      "step_by_step_guide/step8_metadata_and_startup_scripts"
                      "/python/config-with-many-templates.yaml", project_name)
    check_deployment("step-by-step-8-9-python", project_name)
    parsed_instances = parse_instances("step-by-step-8-9-python", project_name)
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name,
      #                                ssh_tunnel_port, ip, project_name)
      pass

    update_deployment("step-by-step-8-9-python",
                      "step_by_step_guide/step9_update_a_deployment"
                      "/python/config-with-many-templates.yaml", project_name)
    check_deployment("step-by-step-8-9-python", project_name)

    parsed_instances = parse_instances("step-by-step-8-9-python", project_name)
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.
      # Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project="
           + project_name + " --zone="+parsed_instances[instance_name]["zone"])
      # rslt = get_instance_index_page(instance_name,
      #                                ssh_tunnel_port, ip, project_name)

    delete_deployment("step-by-step-8-9-python", project_name)

  def test_nodejs_l7_jinja(self):
    """Tests that the jinja NodeJS L7 application deploys correctly."""
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone,
                                "nodejs_l7/jinja/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone,
                                "nodejs_l7/jinja/application.yaml")
    deployment_name = "nodejs-l7-jinja"
    create_deployment(deployment_name,
                      "nodejs_l7/jinja/application.yaml", project_name)
    check_deployment(deployment_name, project_name)
    # TODO(davidsac) all the steps specifically mentioned in the readme
    # are performed, but perhaps there are still more things to be done
    # to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone "
         + default_zone + " --project=" + project_name)
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone "
         + secondary_zone + " --project=" + project_name)
    forwarding_rule = call("gcloud compute forwarding-rules list --project="
                           + project_name 
                           + " | grep " + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    else:
      print forwarding_rule
    delete_deployment(deployment_name, project_name)

  def test_nodejs_l7_python(self):
    """Tests that the python NodeJS L7 application deploys correctly."""
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone,
                                "nodejs_l7/python/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone,
                                "nodejs_l7/python/application.yaml")
    deployment_name = "nodejs-l7-python"
    create_deployment(deployment_name,
                      "nodejs_l7/python/application.yaml", project_name)
    check_deployment(deployment_name, project_name)
    # TODO(davidsac) all the steps specifically mentioned in the readme
    # are performed, but perhaps there are still more things to be done
    # to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone "
         + default_zone + " --project=" + project_name)
    call("gcloud compute instance-groups unmanaged set-named-ports "
         + deployment_name
         + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone "
         + secondary_zone + " --project=" + project_name)
    forwarding_rule = call("gcloud compute forwarding-rules list --project=" 
                           + project_name 
                           + " | grep " + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    else:
      print forwarding_rule
    delete_deployment(deployment_name, project_name)

  def test_image_based_igm_jinja(self):
    # TODO(davidsac) this deployment has some more complex features like an
    # IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-jinja"
    create_deployment(deployment_name, "image_based_igm/image_based_igm.jinja",
                      project_name, properties="\"targetSize:3,zone:"
                      + default_zone + ",maxReplicas:5\"")
    check_deployment(deployment_name, project_name)
    delete_deployment(deployment_name, project_name)
  '''
  def test_image_based_igm_python(self):
    # TODO(davidsac) this deployment has some more complex features like an
    # IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-python"
    create_deployment(deployment_name, "image_based_igm/image_based_igm.py",
                      project_name, properties="\"targetSize:3,zone:"
                      + default_zone + ",maxReplicas:5\"")
    check_deployment(deployment_name, project_name)
    delete_deployment(deployment_name, project_name)

  '''
  def test_igm_updater_jinja(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary
    # to more thoroughly check that it works
    deployment_name = "igm-updater-jinja"
    create_deployment(deployment_name,
                      "igm-updater/jinja/frontendver1.yaml", project_name)
    check_deployment(deployment_name, project_name)
    update_rolling_update_deployment(deployment_name,
                                     "igm-updater/jinja/frontendver2.yaml",
                                     project_name)
    update_rolling_update_deployment(deployment_name,
                                     "igm-updater/jinja/frontendver3.yaml",
                                     project_name)
    delete_deployment(deployment_name, project_name)

  def test_igm_updater_python(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary
    # to more thoroughly check that it works
    deployment_name = "igm-updater-python"
    create_deployment(deployment_name,
                      "igm-updater/python/frontendver1.yaml", project_name)
    check_deployment(deployment_name, project_name)
    update_rolling_update_deployment(deployment_name,
                                     "igm-updater/python/frontendver2.yaml",
                                     project_name)
    update_rolling_update_deployment(deployment_name,
                                     "igm-updater/python/frontendver3.yaml",
                                     project_name)
    delete_deployment(deployment_name, project_name)

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
    # TODO(davidsac) when I have time, read through this
    # example and make sure my test will deploy it correctly
    pass

  def test_step_by_step_10_python(self):
    # TODO(davidsac) when I have time, read through this
    # example and make sure my test will deploy it correctly
    pass

  def test_vpn_auto_subnet(self):
    # TODO(davidsac) How do I test this?
    # TODO(davidsac) figure out what values to use for the parameters
    # deploy("vpn-auto-subnet", "vpn-auto-subnet.jinja", properties=
    #        "peerIp=PEER_VPN_IP,sharedSecret=SECRET,sourceRanges=PEERED_RANGE")
    pass
  '''

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description=
                                   "Deploy github Deployment Manager examples.")

  required_args = parser.add_argument_group("required arguments")
  required_args.add_argument("--host_project", required=True, nargs=1,
                             help="The host project.  If running the tests in "
                             "temp project creation mode, this is the project "
                             "in which the project will be deployed.  If not "
                             "in temp project creation mode, this is the "
                             "project in which all of the tests are deployed.")

  parser.add_argument("--default_zone", default="us-west1-b", nargs=1,
                      help="The zone to use when an example requires the user "
                      "to specify a port.")
  parser.add_argument("--ssh_tunnel_port", default=8890, type=int, nargs=1,
                      help="The port on which the local machine should create "
                      "an ssh tunnel.  The default is 8890")

  project_creation_args = parser.add_argument_group(
      "project creation arguments")
  project_creation_args.add_argument("--create_new_project",
                                     action="store_true",
                                     help="If this flag is icluded, a "
                                     "temporary project will be created to run "
                                     "test deployments.  However, the rest of "
                                     "the project creation arguments will need "
                                     "to be included as well. Follow the "
                                     "prerequisite instructions in the project "
                                     "creation github example (steps 1-6):\n\n"
                                     "https://github.com/GoogleCloudPlatform"
                                     "/deploymentmanager-samples/tree/master"
                                     "/examples/v2/project_creation\n\n"
                                     "Then, supply the necessary arguments "
                                     "through the command line.")
  project_creation_args.add_argument("--new_proj_account_to_create", nargs=1,
                                     help="The name of the service account to "
                                     "create for the new project.")
  project_creation_args.add_argument("--new_proj_billing_account", nargs=1,
                                     help="The billing account to use for "
                                     "the new project.")
  project_creation_args.add_argument("--new_proj_deployment_name", nargs=1,
                                     help="The name in the host project of the "
                                     "deployment to create the new project.")
  project_creation_args.add_argument("--new_proj_name", nargs=1,
                                     help="The name for the new project.")
  project_creation_args.add_argument("--new_proj_org", nargs=1,
                                     help="The organization in which to create "
                                     "the new project.")
  project_creation_args.add_argument("--new_proj_service_account_a", nargs=1,
                                     help="The first service account to add "
                                     "to the new project.")
  project_creation_args.add_argument("--new_proj_service_account_b", nargs=1,
                                     help="The second service account to add "
                                     "to the new project.")

  args = parser.parse_args()
  sys.argv[1:] = []

  if args.new_proj_deployment_name:
    new_proj_deployment_name = args.new_proj_deployment_name[0]
  if args.new_proj_name:
    new_proj_name = args.new_proj_name[0]
  if args.new_proj_org:
    new_proj_org = args.new_proj_org[0]
  if args.new_proj_service_account_a:
    new_proj_service_account_a = args.new_proj_service_account_a[0]
  if args.new_proj_service_account_b:
    new_proj_service_account_b = args.new_proj_service_account_b[0]
  if args.new_proj_billing_account:
    new_proj_billing_account = args.new_proj_billing_account[0]
  if args.new_proj_account_to_create:
    new_proj_account_to_create = args.new_proj_account_to_create[0]

  host_project = args.host_project[0]
  create_new_project = args.create_new_project
  project_name = new_proj_name if create_new_project else host_project
  default_zone = args.default_zone
  ssh_tunnel_port = args.ssh_tunnel_port

  environment = {"default_zone": default_zone, "project_name": project_name}

  unittest.main()
