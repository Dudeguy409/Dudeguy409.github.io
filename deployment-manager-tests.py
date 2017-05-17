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

deployment_name = os.environ.get("DEPLOYMENT_MANAGER_TEST_DEPLOYMENT_NAME")
project_to_create = os.environ.get("DEPLOYMENT_MANAGER_TEST_PROJECT_TO_CREATE")
organization = os.environ.get("DEPLOYMENT_MANAGER_TEST_ORGANIZATION_ID")
service_account_a = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_A")
service_account_b = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_B")
service_account_c = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_OWNER_C")
billing_account = os.environ.get("DEPLOYMENT_MANAGER_TEST_BILLING_ACCOUNT")
account_to_create = os.environ.get("DEPLOYMENT_MANAGER_TEST_SERVICE_ACCOUNT_TO_CREATE")
host_project = os.environ.get("DEPLOYMENT_MANAGER_TEST_HOST_PROJECT")
create_new_project = os.environ.get("DEPLOYMENT_MANAGER_TEST_CREATE_NEW_PROJECT")=="TRUE"
project_name = project_to_create if create_new_project else host_project
zone="us-west1-b"
  

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
    
def create_deployment(deployment_name, yaml_path):
  """Attempts to create a deployment, raising any errors."""
  deployment_create_command = "gcloud deployment-manager deployments create " + deployment_name + " --config examples/v2/" + yaml_path + " --project=" + project_name
  print "Creating deployment of " + deployment_name + "..."  
  call(deployment_create_command)
  print "Deployment created."
  
def update_deployment(deployment_name, yaml_path):
  """Attempts to update an existing deployment, raising any errors."""
  deployment_update_command = "gcloud deployment-manager deployments update " + deployment_name + " --config examples/v2/" + yaml_path + " --project=" + project_name
  print "Updating deployment of " + deployment_name + "..."  
  call(deployment_update_command)
  print "Deployment updated." 

def check_deployment(deployment_name):
  deployment_describe_command = "gcloud deployment-manager deployments describe " + deployment_name + " --format=json --project=" + project_name
  raw_deployment = call(deployment_describe_command)
  parsed_deployment = json.loads(raw_deployment)
  if parsed_deployment.get("deployment").get("operation").get("error"):
    raise Exception("An ERROR was found in the deployment's description.\n"
                    "---BEGIN DESCRIPTION---\n"
                    + raw_deployment + "---END DESCRIPTION---")
    
def delete_deployment(deployment_name):
  deployment_delete_command = "gcloud deployment-manager deployments delete " + deployment_name + " -q --project="+ project_name
  print "Deleting deployment of " + deployment_name + "..." 
  call(deployment_delete_command)
  print "Deployment deleted."

def deploy(deployment_name, yaml_path):
  """Attempts to create and delete a deployment, raising any errors."""
  create_deployment(deployment_name, yaml_path)
  check_deployment(deployment_name)
  delete_deployment(deployment_name)

def parse_ips(deployment_name):
  instance_name_list=[]
  ip_map = {}
  raw_resources=call("gcloud deployment-manager resources list --deployment " + deployment_name + " --format=json")
  parsed_resources =json.loads(raw_resources)
  for resource in parsed_resources:
    if resource["type"]=="compute.v1.instance":
      instance_name_list.append(resource["name"])
  for name in instance_name_list:
    ip_map[name]=(call("gcloud compute instances describe "+name+" --zone=" + zone + " | grep \"networkIP\" | sed 's/networkIP: //'"))
  return ip_map
  
def deploy_http_server(deployment_name, yaml_path):
  create_deployment(deployment_name, yaml_path)
  check_deployment(deployment_name)
  parsed_instances = parse_ips(deployment_name)
  #TODO maybe get rid of port if possible
  port=8890
  for instance_name, ip in parsed_instances.iteritems():
    rslt = get_instance_index_page(instance_name, port, ip)
    raise Exception(rslt)
    port += 1
  delete_deployment(deployment_name)
  
def get_instance_index_page(instance_name, port, ip):
  call("gcloud compute ssh user@"+instance_name+" --zone "+zone+" -- -N -L "+str(port).strip()+":"+str(ip).strip()+":8080")
  return call("curl http://localhost:"+str(port))

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
    deploy("ssl", "ssl/ssl.yaml")
      
  def test_waiter(self):
    # Replace the placeholder "ZONE_TO_RUN" with an actual zone
    call("sed -i.backup 's/ZONE_TO_RUN/"+zone+"/' examples/v2/waiter/config.yaml")
    deploy("waiter", "waiter/config.yaml")
  
  def test_quick_start(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/quick_start/vm.yaml")
    call("sed -i.backup 's/\[FAMILY_NAME\]/debian-8/' examples/v2/quick_start/vm.yaml")
    deploy("quick-start", "quick_start/vm.yaml")
  
  def test_step_by_step_2(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step2_create_a_configuration/two-vms.yaml")
    deploy("step-by-step-2", "step_by_step_guide/step2_create_a_configuration/two-vms.yaml")
  
  def test_step_by_step_4(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step4_use_references/two-vms.yaml")
    deploy("step-by-step-4", "step_by_step_guide/step4_use_references/two-vms.yaml")
  
  def test_step_by_step_5_python(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step5_create_a_template/python/vm-template.py")
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step5_create_a_template/python/vm-template-2.py")
    deploy("step-by-step-5-python", "step_by_step_guide/step5_create_a_template/python/two-vms.yaml")

  def test_step_by_step_5_jinja(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step5_create_a_template/jinja/vm-template.jinja")
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step5_create_a_template/jinja/vm-template-2.jinja")
    deploy("step-by-step-5-jinja", "step_by_step_guide/step5_create_a_template/jinja/two-vms.yaml")
    
  def test_step_by_step_6_python(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step6_use_multiple_templates/python/vm-template.py")
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step6_use_multiple_templates/python/vm-template-2.py")
    deploy("step-by-step-6-python", "step_by_step_guide/step6_use_multiple_templates/python/config-with-many-templates.yaml")
     
  def test_step_by_step_6_jinja(self):
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step6_use_multiple_templates/jinja/vm-template.jinja")
    call("sed -i.backup 's/\[MY_PROJECT\]/" + project_name + "/' examples/v2/step_by_step_guide/step6_use_multiple_templates/jinja/vm-template-2.jinja")
    deploy("step-by-step-6-jinja", "step_by_step_guide/step6_use_multiple_templates/jinja/config-with-many-templates.yaml")
    
  def test_step_by_step_7_python(self):
    deploy("step-by-step-7-python", "step_by_step_guide/step7_use_environment_variables/python/config-with-many-templates.yaml")

  def test_step_by_step_7_jinja(self):
    deploy("step-by-step-7-jinja", "step_by_step_guide/step7_use_environment_variables/jinja/config-with-many-templates.yaml")
  
  """
  def test_vm_startup_script_python(self):
    # Replace the placeholder "ZONE_TO_RUN" with an actual zone
    call("sed -i.backup 's/ZONE_TO_RUN/"+zone+"/' examples/v2/vm_startup_script/python/vm.yaml")
    deploy_http_server("vm-startup-script-python", "vm_startup_script/python/vm.yaml")
    
  def test_vm_startup_script_jinja(self):
    # Replace the placeholder "ZONE_TO_RUN" with an actual zone
    call("sed -i.backup 's/ZONE_TO_RUN/"+zone+"/' examples/v2/vm_startup_script/jinja/vm.yaml")
    deploy_http_server("vm-startup-script-jinja", "vm_startup_script/jinja/vm.yaml")

  def test_vpn_auto_subnet(self):
    # TODO we could probably hack the traditional deploy method to work with this by adding a properties parameter
    # TODO figure out what values to use for the parameters
    "gcloud deployment-manager deployments create vpn-auto-subnet --config vpn-auto-subnet.jinja --project PROJECT_NAME --properties \"peerIp=PEER_VPN_IP,sharedSecret=SECRET,sourceRanges=PEERED_RANGE\""

  def test_step_by_step_8_9_python(self):
    create_deployment("step-by-step-8-9-python", "step_by_step_guide/step8_metadata_and_startup_scripts/python/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-python")
    
    parsed_python_instances = parse_ips("step-by-step-8-9-python")
    # TODO consider getting rid of port once I get this working
    port = 8888
    for instance_name, ip in parsed_python_instances.iteritems():
      rslt = get_instance_index_page(instance_name, port, ip)
      port+=1

    update_deployment("step-by-step-8-9-python", "step_by_step_guide/step9_update_a_deployment/python/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-python")
    
    parsed_python_instances = parse_ips("step-by-step-8-9-python")
    # TODO assert that the contents are updated now
    for instance_name, ip in parsed_python_instances.iteritems():
      call("gcloud compute instances reset " + instance_name + " --project=" + project_name)
      rslt = get_instance_index_page(instance_name, port, ip)
      port+=1

    delete_deployment("step-by-step-8-9-python")
    
  def test_step_by_step_8_9_jinja(self):
    create_deployment("step-by-step-8-9-jinja", "step_by_step_guide/step8_metadata_and_startup_scripts/jinja/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-jinja")
    
    parsed_jinja_instances = parse_ips("step-by-step-8-9-jinja")
    # TODO consider getting rid of port once I get this working
    port = 8888
    for instance_name, ip in parsed_jinja_instances.iteritems():
      rslt = get_instance_index_page(instance_name, port, ip)
      port+=1

    update_deployment("step-by-step-8-9-jinja", "step_by_step_guide/step9_update_a_deployment/jinja/config-with-many-templates.yaml")
    check_deployment("step-by-step-8-9-jinja")
    
    parsed_jinja_instances = parse_ips("step-by-step-8-9-jinja")
    # TODO assert that the contents are updated now
    for instance_name, ip in parsed_jinja_instances.iteritems():
      call("gcloud compute instances reset " + instance_name + " --project=" + project_name)
      rslt = get_instance_index_page(instance_name, port, ip)
      port+=1

    delete_deployment("step-by-step-8-9-jinja")

  
  def test_step_by_step_10(self):
    self.create("step-by-step-10-python", "step_by_step_guide/step10_use_python_templates/python/use-python-template-with-modules.yaml")
    self.create("step-by-step-10-jinja", "step_by_step_guide/step10_use_python_templates/jinja/use-jinja-template-with-modules.yaml")
    # TODO create an SSH tunnel to connect to "gcloud compute instances describe the-first-vm | grep "natIP""
  """
  
  
  
  
