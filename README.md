# HFD NetLab GPUaaS

Example (proof of concept) to start an instance that offers NVIDIA RTX cards using direct pci passthrough in the OpenStack environment of NetLab - Hochschule Fulda - Applied Computer Science.

The script uses standard OpenStack Python API:
- https://docs.openstack.org/openstacksdk/latest/user/guides/intro.html

Alternatives that can be also be used to start instances are:
- OpenStack Web Interface (Horizon): https://private-cloud.informatik.hs-fulda.de/
- OpenStack CLI client (use, e.g. "pip install openstack"): https://docs.openstack.org/newton/user-guide/common/cli-install-openstack-command-line-clients.html
- terraform OpenStack provider: https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs
- pulumi OpenStack provider: https://www.pulumi.com/registry/packages/openstack/
- Apache libcloud: https://libcloud.apache.org/
- ... ;)

Need access to "05)_AI-NetLab-Pro" VPN profile if you are using a network outside of Hochschule Fulda to be able to access our OpenStack env and obviously credentials for OpenStack:

The script expects a "clouds.yaml" ([example](https://raw.githubusercontent.com/srieger1/hfd-netlab-openstack-gpuaas/main/clouds.yaml)) file in the working directory containing credentials and API endpoints for OpenStack. You can also download clouds.yaml from Horizon web interface https://private-cloud.informatik.hs-fulda.de/project/api_access/clouds.yaml. You can add the password to clouds.yaml. See https://docs.openstack.org/python-openstackclient/latest/configuration/index.html


After running the script you will get SSH access to an instance that offers direct PCI access (passthrough) to one of our NVIDIA RTX GPUs.

NVIDIA drivers and cuda are automatically installed (see cloud-init definition in the USERDATA var below). You can change the var content to execute further tasks/install packages/fetch data/run experiments/submit results etc.

Using SSH to login to the instance after stating it you will see the installation process defined in USERDATA running. As soon as you are able to run "nvidia-smi" the process is finished. You can also snapshot the instance at this point and use the snapshot for subsequent runs, to speed up the instance start.

Currently only flavor g1.medium is offered, but further flavors with other CPU, memory, storage resources etc. are possible. Also multiple GPUs are possible in a single instance.

Instances are currently limited to run max. for one week to allow others to also use the GPUs. Instances are automatically "shelved" after one week, effectively snapshotting/suspending their disk state. You can use the "unshelve" operation to get them running again if nobody else reserved GPUs meanwhile.