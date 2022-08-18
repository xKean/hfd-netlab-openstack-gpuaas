#!/bin/bash
#cd /home/user/nvidia-test-examples/GPUaaS
ssh-keygen -f "/root/.ssh/known_hosts" -R "192.168.72.101"
#ssh -i nvidia-test-keypair.key ubuntu@192.168.72.101
ssh -i ~/.ssh/id_rsa ubuntu@192.168.72.101
