#!/usr/bin/python3

# example to start an instance that offers NVIDIA cards using direct pci passthrough with initial stress test in the OpenStack environment of NetLab - Hochschule Fulda
#
# The script uses standard OpenStack Python API:
# - https://docs.openstack.org/openstacksdk/latest/user/guides/intro.html
#
# can be installed using: "pip install openstacksdk" see also: https://docs.openstack.org/openstacksdk/latest/install/index.html
#
# Alternatives that can be also be used to start instances are:
# - OpenStack Web Interface (Horizon): https://private-cloud.informatik.hs-fulda.de/
# - OpenStack CLI client (use, e.g. "pip install openstack"): https://docs.openstack.org/newton/user-guide/common/cli-install-openstack-command-line-clients.html
# - terraform OpenStack provider: https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs
# - pulumi OpenStack provider: https://www.pulumi.com/registry/packages/openstack/
# - Apache libcloud: https://libcloud.apache.org/
# - ... ;)
#
# The script expects a "clouds.yaml" file in the working directory containing credentials and API endpoints for OpenStack.
# Be sure to use the "05)_AI-NetLab-Pro" VPN profile if you are using a network outside of Hochschule Fulda to be able to access our OpenStack env.
# https://private-cloud.informatik.hs-fulda.de/project/api_access/clouds.yaml
# You can add the password to clouds.yaml. See https://docs.openstack.org/python-openstackclient/latest/configuration/index.html
#
# After running the script you will get SSH access to an instance that offers direct PCI access (passthrough) to one of our NVIDIA RTX GPUs.
# nvidia drivers, docker and gpu-burn are automatically installed (see cloud-init definition in the USERDATA var below). You can change the var content
# to execute further tasks/install packages/fetch data/run experiments/submit results etc.
#
# Using SSH to login to the instance after stating it you will see the installation process defined in USERDATA running. As soon as you are able
# to run "nvidia-smi" the process is finished. You can also snapshot the instance at this point and use the snapshot for subsequent runs, to speed
# up the instance start.

import openstack
import os
import sys
import yaml



###########################
#
# Config
#
###########################

if len(sys.argv) < 3:
   print("usage: %s <instance-name> <burn duration> ?<parameter>" % sys.argv[0])
   exit(-1)

INSTANCE_NAME = sys.argv[1]

#IMAGE_NAME = "Ubuntu 20.04 - Focal Fossa - 64-bit - Cloud Based Image"
IMAGE_NAME = "Ubuntu 22.04 - Jammy Jellyfish - 64-bit - Cloud Based Image"

# You can also use/upload other images for recent Linux distros (see, e.g., https://cloud-images.ubuntu.com/)
#
# To use a prepared image that already has nvidia drivers and cuda installed, use the image here.
# You can create a new image by creating a snapshot of the instance that was started by this script
# Snapshot can be created using CLI/API or web interface of OpenStack
# IMAGE_NAME="my-snapshot-with-nvidia-stuff-installed"

FLAVOR_NAME = "g1-1x2060.medium"
# FLAVOR_NAME = "g1-1x2060.medium" NVIDIA Corporation TU106 [GeForce RTX 2060 SUPER]
# FLAVOR_NAME = "g1-2x2060.medium" NVIDIA Corporation TU106 [GeForce RTX 2060 SUPER]
# FLAVOR_NAME = "g1-4x2060.medium" NVIDIA Corporation TU106 [GeForce RTX 2060 SUPER]
#
# FLAVOR_NAME = "g1-1x2080.medium" NVIDIA Corporation TU102 [GeForce RTX 2080 Ti Rev. A]
# FLAVOR_NAME = "g1-2x2080.medium" NVIDIA Corporation TU102 [GeForce RTX 2080 Ti Rev. A]

#NETWORK_NAME = sys.argv[1] + "-net"
NETWORK_NAME = "test-gpu-net"

#KEYPAIR_NAME: Can be changed to an already existing key imported into Openstack
KEYPAIR_NAME = "examplekey-pub"
PRIVATE_KEYPAIR_FILE = "nvidia-test-keypair.key"
# To use an existing keypair uncomment the following line and change it appropriately:
# IMPORT_EXISTING_PUBKEY_FILE = "~/.ssh/id_rsa.pub"
#IMPORT_EXISTING_PUBKEY_FILE = "~/.ssh/pub.key"
IMPORT_EXISTING_PUBKEY_FILE = ""

# initial installation using cloud-init
#
# can be changed to install packages, configure instance etc. - see also: https://help.ubuntu.com/community/CloudInit
#                                                                         https://cloudinit.readthedocs.io/en/latest/

USERDATA = """
#cloud-config
packages:
  - update-notifier-common
  - unattended-upgrades
  - landscape-common
  - nvidia-driver-535
  - nvidia-dkms-535
  - docker.io
package_update: true
package_upgrade: true
package_reboot_if_required: true
write_files:
  - content: |
      @reboot root sleep 40 && chdir /home/ubuntu/gpu-burn && docker build -t gpu_burn . && docker run --rm --gpus all gpu_burn >> "gpu-burn-results_$(date +'\%Y-\%m-\%d_\%H-\%M-\%S').log"
    path: /etc/crontab
    append: true
runcmd:
  - apt-get update
  - apt-get upgrade -y
  - curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
  - curl -s -L https://nvidia.github.io/nvidia-docker/ubuntu22.04/nvidia-docker.list > /etc/apt/sources.list.d/nvidia-docker.list 
  - apt update
  - apt -y install nvidia-container-toolkit
  - git clone https://github.com/wilicc/gpu-burn /home/ubuntu/gpu-burn
  - chdir /home/ubuntu/gpu-burn
  - sudo sed -i 's/60/<duration> <parameter>/g' Dockerfile
  - docker build -t gpu_burn .
  - touch /root/cloud-init-script-ran-successfully
  - reboot
"""

#for Ubuntu 20.04 change the second curl command to: - curl -s -L https://nvidia.github.io/nvidia-docker/ubuntu20.04/nvidia-docker.list > /etc/apt/sources.list.d/nvidia-docker.list

USERDATA = USERDATA.replace("<duration>", sys.argv[2])

if len(sys.argv) > 3:
 USERDATA = USERDATA.replace("<parameter>", sys.argv[3])
else:
 USERDATA = USERDATA.replace("<parameter>", "")

###########################
#
# Code
#
###########################

def get_keypair(conn):
    keypair = conn.compute.find_keypair(KEYPAIR_NAME)

    if not keypair:
        if IMPORT_EXISTING_PUBKEY_FILE != "":
            print("Importing public key from %s" % (IMPORT_EXISTING_PUBKEY_FILE))

            with open(os.path.expanduser(IMPORT_EXISTING_PUBKEY_FILE), 'r') as f:
                pubkey = f.read()
                keypair = conn.compute.create_keypair(name=KEYPAIR_NAME, public_key=pubkey)
                ssh_privkey = "<private key corresponding to " + IMPORT_EXISTING_PUBKEY_FILE + ">"

        else:
            print("Create Key Pair:")

            keypair = conn.compute.create_keypair(name=KEYPAIR_NAME)

            print(keypair)

            with open(PRIVATE_KEYPAIR_FILE, 'w') as f:
                f.write("%s" % keypair.private_key)

            os.chmod(PRIVATE_KEYPAIR_FILE, 0o400)
            ssh_privkey = PRIVATE_KEYPAIR_FILE
    else:
        if IMPORT_EXISTING_PUBKEY_FILE != "":
            ssh_privkey = "<private key corresponding to existing " + IMPORT_EXISTING_PUBKEY_FILE + ">"
        else:
            ssh_privkey = PRIVATE_KEYPAIR_FILE


    return keypair, ssh_privkey

# Initialize and turn on debug logging
# openstack.enable_logging(debug=True)

# Initialize connection
conn = openstack.connect(cloud='openstack')

image = conn.compute.find_image(IMAGE_NAME)
flavor = conn.compute.find_flavor(FLAVOR_NAME)
network = conn.network.find_network(NETWORK_NAME)
keypair, ssh_privkey = get_keypair(conn)

# print("Image: %s" % image)
# print("Flavor: %s" % flavor)
# print("Network: %s" % network)
# print("Keypair: %s" % keypair)

# Boot a server, wait for it to boot, and then do whatever is needed
# to get a public IP address for it.

# delete server if it already exists
# conn.delete_server(INSTANCE_NAME)

# TODO: remove auto_ip and search for floating_ip separately?
server = conn.create_server(
  INSTANCE_NAME, image=image, flavor=flavor, network=network, key_name=keypair.name, userdata=USERDATA, wait=True, auto_ip=True)
print("Server instance started:\n\n%s" % server)

print("\n\nLogin using, e.g.:\n\nssh -i {key} ubuntu@{ip}".format(
  key=ssh_privkey,
  ip=server.public_v4))
