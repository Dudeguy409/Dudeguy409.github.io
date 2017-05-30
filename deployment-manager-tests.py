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
deployments, follow the instrictions in the project creation github example:

https://github.com/GoogleCloudPlatform/deploymentmanager-samples/tree/master/examples/v2/project_creation

Then, before running the tests, set the environment variables for your specific
project.  If "DEPLOYMENT_MANAGER_TEST_CREATE_NEW_PROJECT" is set to "TRUE", the
tests will be run in a new project.  If not, they will be run in your default
configured project.
"""

import json
import os
import subprocess
import yaml
import time
from nose.tools import timed

# The variables immediately below are used to create a new project in which to make test deployments, but only if the environment variable "DM_TEST_CREATE_NEW_PROJECT" is set to "TRUE".  Please see the example instructions on GitHub to see what value to assign each variable:
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


def setup_module():
  if create_new_project:
    call("gcloud deployment-manager deployments create "
         + project_deployment_name
         + " --config config-template.jinja --properties \"PROJECT_NAME:'"
         + project_to_create + "',ORGANIZATION_ID:'" + organization
         + "',BILLING_ACCOUNT:'" + billing_account
         + "',SERVICE_ACCOUNT_TO_CREATE:'" + account_to_create
         + "',SERVICE_ACCOUNT_OWNER_A:'" + service_account_a
         + "',SERVICE_ACCOUNT_OWNER_B:'" + service_account_b + "'\"")


def teardown_module():
  if create_new_project:
    call("gcloud deployment-manager deployments delete "
         + project_deployment_name + " -q")


def call(command):
  """Runs the command and returns the output, possibly as an exception."""
  print "Running command: ", command
  try:
    result = subprocess.check_output(command,
                                     shell=True, stderr=subprocess.STDOUT)
    return result
  except subprocess.CalledProcessError as e:
    raise Exception(e.output)
    
def replace_placeholder_in_file(search_for, replace_with, file):
  # FIXME(davidsac): Host this test file in the testing folder of the repo, and update these tests to copy over the example folder and make changes and deployments with it.
  call("sed -i.backup 's/" + search_for + "/" + replace_with + "/' examples/v2/" + file)

def create_deployment(deployment_name, yaml_path, properties=None):
  """Attempts to create a deployment, raising any errors."""
  deployment_create_command = ("gcloud deployment-manager deployments create "
                               + deployment_name + " --config examples/v2/"
                               + yaml_path + " --project=" + project_name)
  if properties:
    deployment_create_command += " --properties " + properties
  print "Creating deployment of " + deployment_name + "..."
  call(deployment_create_command)
  print "Deployment created."


def update_and_check_deployment(deployment_name, yaml_path):
  """Attempts to update an existing deployment, raising any errors."""
  deployment_update_command = ("gcloud deployment-manager deployments update "
                               + deployment_name + " --config examples/v2/"
                               + yaml_path + " --project=" + project_name)
  print "Updating deployment of " + deployment_name + "..."
  number_of_attempts = 0
  max_number_of_attempts = 3
  while max_number_of_attempts > number_of_attempts:
    try:
      call(deployment_update_command)
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
  print "Deployment updated."


def check_deployment(deployment_name):
  deployment_describe_command = ("gcloud deployment-manager "
                                 "deployments describe " + deployment_name
                                 + " --format=json --project=" + project_name)
  raw_deployment = call(deployment_describe_command)
  parsed_deployment = json.loads(raw_deployment)
  if parsed_deployment.get("deployment").get("operation").get("error"):
    raise Exception("An ERROR was found in the deployment's description.\n"
                    "---BEGIN DESCRIPTION---\n"
                    + raw_deployment + "---END DESCRIPTION---")


def delete_deployment(deployment_name):
  deployment_delete_command = ("gcloud deployment-manager deployments delete "
                               + deployment_name + " -q --project="
                               + project_name)
  print "Deleting deployment of " + deployment_name + "..."
  call(deployment_delete_command)
  print "Deployment deleted."


def deploy(deployment_name, yaml_path):
  """Attempts to create and delete a deployment, raising any errors."""
  create_deployment(deployment_name, yaml_path)
  check_deployment(deployment_name)
  delete_deployment(deployment_name)


def parse_instances(deployment_name):
  """Creates a map of a deployment's GCE instances and associated IPs."""
  instance_map = {}
  raw_resources = call("gcloud deployment-manager resources list --deployment "
                       + deployment_name + " --format=json")
  parsed_resources = json.loads(raw_resources)
  for resource in parsed_resources:
    if resource["type"] == "compute.v1.instance":
      parsed_properties = yaml.load(resource["properties"])
      zone = parsed_properties["zone"]
      instance_map[resource["name"]] = {"zone" : zone}
  for name in instance_map:
    instance_map[name]["ip"] = call("gcloud compute instances describe "
                        + name+" --zone=" + instance_map[name]["zone"]
                        + " | grep \"networkIP\" | sed 's/networkIP: //'")
  return instance_map


def deploy_http_server(deployment_name, yaml_path):
  """Tests deployments with GCE instances that host servers."""
  create_deployment(deployment_name, yaml_path)
  check_deployment(deployment_name)
  parsed_instances = parse_instances(deployment_name)
  for instance_name in parsed_instances:
    pass
    # TODO(davidsac) assert that the value is what is expected
    # get_instance_index_page(instance_name, default_ssh_tunnel_port, parsed_instances[instance_name]["ip"])
  delete_deployment(deployment_name)


def get_instance_index_page(instance_name, local_port, ip):
  # TODO fix
  call("gcloud compute ssh user@" + instance_name + " --zone " + default_zone
       + " -- -N -L " + str(port).strip() + ":" + str(ip).strip() + ":8080")
  return call("curl http://localhost:"+str(local_port))


class TestSimpleDeployment(object):
  """A test class for simple deployments.

  This is a test class for simple deployments that only need to be deployed in
  order to be considered working successfully.  It is not for deployments that
  need to be interacted with after being deployed in order to ensure that they
  were deployed successfully.
  """

  def test_build_configuration_vm(self):
    deploy("build-config-vm", "build_configuration/vm.yaml")

  def test_build_configuration_vm_and_bigquery(self):
    deploy("build-config-vm-and-bigquery",
           "build_configuration/vm_and_bigquery.yaml")

  def test_ssl(self):
    # TODO should we interact with the deployment to make sure that it works?  Or is the simple warning-free deployment of an SSL certificate enough?
    deploy("ssl", "ssl/ssl.yaml")

  def test_waiter(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "waiter/config.yaml")
    deploy("waiter", "waiter/config.yaml")

  def test_quick_start(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "quick_start/vm.yaml")
    replace_placeholder_in_file("\\[FAMILY_NAME\\]", "debian-8", "quick_start/vm.yaml")
    deploy("quick-start", "quick_start/vm.yaml")

  def test_step_by_step_2(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step2_create_a_configuration/two-vms.yaml")
    deploy("step-by-step-2",
           "step_by_step_guide/step2_create_a_configuration/two-vms.yaml")

  def test_step_by_step_4(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step4_use_references/two-vms.yaml")
    deploy("step-by-step-4",
           "step_by_step_guide/step4_use_references/two-vms.yaml")

  def test_step_by_step_5_python(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step5_create_a_template/python/vm-template.py")
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step5_create_a_template/python/vm-template-2.py")
    deploy("step-by-step-5-python",
           "step_by_step_guide/step5_create_a_template/python/two-vms.yaml")

  def test_step_by_step_5_jinja(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step5_create_a_template/jinja/vm-template.jinja")
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step5_create_a_template/jinja/vm-template-2.jinja")
    deploy("step-by-step-5-jinja",
           "step_by_step_guide/step5_create_a_template/jinja/two-vms.yaml")

  def test_step_by_step_6_python(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step6_use_multiple_templates/python/vm-template.py")
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step6_use_multiple_templates/python/vm-template-2.py")
    deploy("step-by-step-6-python",
           "step_by_step_guide/step6_use_multiple_templates"
           "/python/config-with-many-templates.yaml")

  def test_step_by_step_6_jinja(self):
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step6_use_multiple_templates/jinja/vm-template.jinja")
    replace_placeholder_in_file("\\[MY_PROJECT\\]", project_name, "step_by_step_guide/step6_use_multiple_templates/jinja/vm-template-2.jinja")
    deploy("step-by-step-6-jinja",
           "step_by_step_guide/step6_use_multiple_templates"
           "/jinja/config-with-many-templates.yaml")

  def test_step_by_step_7_python(self):
    deploy("step-by-step-7-python",
           "step_by_step_guide/step7_use_environment_variables"
           "/python/config-with-many-templates.yaml")

  def test_step_by_step_7_jinja(self):
    deploy("step-by-step-7-jinja",
           "step_by_step_guide/step7_use_environment_variables"
           "/jinja/config-with-many-templates.yaml")
  """
  
  
  
  
  """  
  
  def test_build_config_add_templates_jinja(self):
    # TODO zone is us-central1-a
    deploy("build-config-add-templates-jinja",
           "build_configuration/add_templates/jinja/use_vm_template.yaml")
    
  def test_build_config_add_templates_python(self):
    # TODO zone is us-central1-a
    deploy("build-config-add-templates-python",
           "build_configuration/add_templates/python/use_vm_template.yaml")  
  
  def test_single_vm_jinja(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "single_vm/jinja/vm.yaml")
    deploy("single-vm",
           "single_vm/jinja/vm.yaml")
    
  def test_single_vm_python(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "single_vm/python/vm.yaml")
    deploy("single-vm",
           "single_vm/python/vm.yaml")
    
  def test_build_config_use_outputs(self):
    deploy("build-config-use-outputs",
           "build_configuration/use_outputs/use_template_with_outputs.yaml")
    
  def test_build_config_explicit_dependencies(self):
    # TODO zone is us-central1-a
    deploy("build-config-explicit-dependencies",
           "build_configuration/explicit_dependencies/backend_frontend_instances.yaml")

  def test_vm_startup_script_python(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "vm_startup_script/python/vm.yaml")
    deploy_http_server("vm-startup-script-python", "vm_startup_script/python/vm.yaml")
    
  def test_vm_startup_script_jinja(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "vm_startup_script/jinja/vm.yaml")
    deploy_http_server("vm-startup-script-jinja", "vm_startup_script/jinja/vm.yaml")

  def test_vpn_auto_subnet(self):
    # TODO we could probably hack the traditional deploy method to work with this by adding a properties parameter
    #TODO How are we going to test this with the firewall?
    # TODO figure out what values to use for the parameters
    # deploy("vpn-auto-subnet", "vpn-auto-subnet.jinja", properties= "\\\"peerIp=PEER_VPN_IP,sharedSecret=SECRET,sourceRanges=PEERED_RANGE\\\"")
    pass
  
  def test_step_by_step_8_9_jinja(self):
    # TODO the zone that 8 is being created in is us-central1-f, not us-west1-b
    create_deployment("step-by-step-8-9-jinja", "step_by_step_guide/step8_metadata_and_startup_scripts/jinja/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-jinja")
    
    parsed_instances = parse_instances("step-by-step-8-9-jinja")
    # TODO consider getting rid of port once I get this working
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name, default_ssh_tunnel_port, ip)
      pass
    
    # TODO the zone that 8 is being created in is still us-central1-f, not us-west1-b.
    update_and_check_deployment("step-by-step-8-9-jinja", "step_by_step_guide/step9_update_a_deployment/jinja/config-with-many-templates.yaml")
    
    parsed_instances = parse_instances("step-by-step-8-9-jinja")
    # TODO assert that the contents are updated now
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.  Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project=" + project_name + " --zone="+parsed_instances[instance_name]["zone"])
      # rslt = get_instance_index_page(instance_name, port, ip)

    delete_deployment("step-by-step-8-9-jinja")

  def test_step_by_step_8_9_python(self):
    # TODO the zone that 8 is being created in is us-central1-f, not us-west1-b
    create_deployment("step-by-step-8-9-python", "step_by_step_guide/step8_metadata_and_startup_scripts/python/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-python")
    parsed_instances = parse_instances("step-by-step-8-9-python")
    for instance_name in parsed_instances:
      # rslt = get_instance_index_page(instance_name, default_ssh_tunnel_port, ip)
      pass
    
    # TODO the zone that 8 is being created in is still us-central1-f, not us-west1-b
    update_and_check_deployment("step-by-step-8-9-python", "step_by_step_guide/step9_update_a_deployment/python/config-with-many-templates.yaml")
    
    parsed_instances = parse_instances("step-by-step-8-9-python")
    for instance_name in parsed_instances:
      # Reset the instance before testing the server again.  Note that the instances are in us-central1-f.
      call("gcloud compute instances reset " + instance_name + " --project=" + project_name + " --zone="+parsed_instances[instance_name]["zone"] )
      # rslt = get_instance_index_page(instance_name, default_ssh_tunnel_port, ip)

    delete_deployment("step-by-step-8-9-python")
    


  
  def test_step_by_step_10_jinja(self):
    #self.create("step-by-step-10-jinja", "step_by_step_guide/step10_use_python_templates/jinja/use-jinja-template-with-modules.yaml")
    # TODO when I have time, read through this example and make sure my test will deploy it correctly
    pass
    
  def test_step_by_step_10_python(self):
    # self.create("step-by-step-10-python", "step_by_step_guide/step10_use_python_templates/python/use-python-template-with-modules.yaml")
    # TODO when I have time, read through this example and make sure my test will deploy it correctly
    pass
    
  def test_common_jinja(self):
    #TODO do I need to add tests for these?  It doesn't seem like there are any deploymets here, just utility files for other deployments
    pass
    
  def test_common_python(self):
    #TODO do I need to add tests for these?  It doesn't seem like there are any deploymets here, just utility files for other deployments
    pass
  
  def test_container_vm_jinja(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "container_vm/jinja/container_vm.yaml")
    deploy("container-vm-jinja", "container_vm/jinja/container_vm.yaml")
    # TODO(davidsac) ensure after deployment that this deployed correctly
    
  def test_container_vm_python(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "container_vm/python/container_vm.yaml")
    deploy("container-vm-python", "container_vm/python/container_vm.yaml")
    # TODO(davidsac) ensure after deployment that this deployed correctly
    
  def test_nodejs_jinja(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "nodejs/jinja/nodejs.yaml")
    deploy("nodejs-jinja", "nodejs/jinja/nodejs.yaml")
    # TODO(davidsac) ensure after deployment that this deployed correctly
    
  def test_nodejs_python(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "nodejs/python/nodejs.yaml")
    deploy("nodejs-python", "nodejs/python/nodejs.yaml")
    # TODO(davidsac) ensure after deployment that this deployed correctly  
    
  def test_regional_igm(self):
    deploy("regional-igm", "regional_igm/regional_igm.yaml")
    # TODO(davidsac) ensure after deployment that this deployed correctly  
    
  def test_nodejs_l7_jinja(self):
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone, "nodejs_l7/jinja/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "nodejs_l7/jinja/application.yaml")
    deployment_name = "nodejs-l7-jinja"
    create_deployment(deployment_name, "nodejs_l7/jinja/application.yaml")
    check_deployment(deployment_name)
    # TODO all the steps specifically mentioned in the readme are performed, but perhaps there are still more things to be done to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports " + deployment_name + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone " + default_zone)
    call("gcloud compute instance-groups unmanaged set-named-ports " + deployment_name + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone " + secondary_zone)
    forwarding_rule = call("gcloud compute forwarding-rules list | grep " + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    delete_deployment(deployment_name)

  def test_nodejs_l7_python(self):
    secondary_zone = "us-central1-f"
    replace_placeholder_in_file("SECOND_ZONE_TO_RUN", secondary_zone, "nodejs_l7/python/application.yaml")
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "nodejs_l7/python/application.yaml")
    deployment_name = "nodejs-l7-python"
    create_deployment(deployment_name, "nodejs_l7/python/application.yaml")
    check_deployment(deployment_name)
    # TODO all the steps specifically mentioned in the readme are performed, but perhaps there are still more things to be done to check that it works?
    call("gcloud compute instance-groups unmanaged set-named-ports " + deployment_name + "-frontend-pri-igm --named-ports http:8080,httpstatic:8080 --zone " + default_zone)
    call("gcloud compute instance-groups unmanaged set-named-ports " + deployment_name + "-frontend-sec-igm --named-ports http:8080,httpstatic:8080 --zone " + secondary_zone)
    forwarding_rule = call("gcloud compute forwarding-rules list | grep " + deployment_name + "-application-l7lb")
    if not forwarding_rule:
      raise Exception("no forwarding rule found")
    delete_deployment(deployment_name)
    
  def test_vm_with_disks_jinja(self):
    # TODO zone is us-central1-a
    deploy("vm-with-disks-jinja", "vm_with_disks/jinja/vm_with_disks.yaml")
    
  def test_vm_with_disks_python(self):
    # TODO zone is us-central1-a
    deploy("vm-with-disks-python", "vm_with_disks/python/vm_with_disks.yaml")
    
  def test_container_igm_jinja(self):
    # TODO zone is us-central1-f
    deploy("container-igm-jinja","container_igm/jinja/container_igm.yaml")
    
  def test_container_igm_python(self):
    # TODO zone is us-central1-f
    deploy("container-igm-python","container_igm/python/container_igm.yaml")
    
  def test_iam(self):
    deploy("iam", "iam/jinja/accessible_resource.yaml")
    # TODO make sure that this is actually deploying correctly
    
  def test_htcondor(self):
    # TODO read the tutorial and figure out how to deploy this
    pass
  
  def test_metadata_from_file_jinja(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "metadata_from_file/jinja/config.yaml")
    deploy_http_server("metadata-from-file-jinja", "metadata_from_file/jinja/config.yaml")
    
  def test_metadata_from_file_python(self):
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "metadata_from_file/python/config.yaml")
    deploy_http_server("metadata-from-file-python", "metadata_from_file/python/config.yaml")
    
  def test_instance_pool_jinja(self):
    deploy("instance-pool-jinja", "instance_pool/jinja/instance-pool.yaml")
    # TODO(davidsac) is there anything else that needs to be checked?  The number of instances created, for example?  Or maybe interconnectivity?
    
  def test_instance_pool_python(self):
    deploy("instance-pool-python", "instance_pool/python/instance-pool.yaml")
    # TODO(davidsac) is there anything else that needs to be checked?  The number of instances created, for example?  Or maybe interconnectivity?
    
  def test_image_based_igm_jinja(self):
    # TODO this deployment has some more complex features like an IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-jinja" 
    create_deployment(deployment_name, "image_based_igm/image_based_igm.jinja", "\"targetSize:3,zone:" + default_zone + ",maxReplicas:5\"")
    check_deployment(deployment_name)
    delete_deployment(deployment_name)
    
  def test_image_based_igm_python(self):
    # TODO this deployment has some more complex features like an IGM and Autoscaler that may need to be tested more thoroughly
    deployment_name = "image-based-igm-python"
    create_deployment(deployment_name, "image_based_igm/image_based_igm.py", "\"targetSize:3,zone:" + default_zone + ",maxReplicas:5\"")
    check_deployment(deployment_name)
    delete_deployment(deployment_name)

  def test_igm_updater_jinja(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    deployment_name = "igm-updater-jinja"
    create_deployment(deployment_name, "igm-updater/jinja/frontendver1.yaml")
    check_deployment(deployment_name)
    update_and_check_deployment(deployment_name, "igm-updater/jinja/frontendver2.yaml")
    update_and_check_deployment(deployment_name, "igm-updater/jinja/frontendver3.yaml")
    delete_deployment(deployment_name)
     
  def test_igm_updater_python(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    deployment_name = "igm-updater-python"
    create_deployment(deployment_name, "igm-updater/python/frontendver1.yaml")
    check_deployment(deployment_name)
    update_and_check_deployment(deployment_name, "igm-updater/python/frontendver2.yaml")
    update_and_check_deployment(deployment_name, "igm-updater/python/frontendver3.yaml")
    delete_deployment(deployment_name)
    
  def test_internal_lb(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    deploy("internal-lb", "internal_lb/python/config.yaml")
    
  def test_internal_lb_haproxy_jinja(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "internal_lb_haproxy/jinja/config.yaml")
    deploy("int-lb-hap-j", "internal_lb_haproxy/jinja/config.yaml")
    
  # TODO(davidsac): There are two copies of the python files it seems.  Which ones are the most up-to-date?  
  def test_internal_lb_haproxy_python_a(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "internal_lb_haproxy/python/config.yaml")
    deploy("int-lb-hap-p-a", "internal_lb_haproxy/python/config.yaml")
  
  def test_internal_lb_haproxy_python_b(self):
    # TODO(davidsac):  This is a pretty complex example.  It may be necessary to more thoroughly check that it works
    replace_placeholder_in_file("ZONE_TO_RUN", default_zone, "internal_lb_haproxy/config.yaml")
    deploy("int-lb-hap-p-b", "internal_lb_haproxy/config.yaml")
