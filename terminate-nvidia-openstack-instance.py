#!/usr/bin/python3

import openstack
import os
import sys

if len(sys.argv) < 2:
    print("usage: %s <instance-name>" % sys.argv[0])
    exit(-1)

INSTANCE_NAME = sys.argv[1]

# Initialize and turn on debug logging
#openstack.enable_logging(debug=True)

# Initialize connection
conn = openstack.connect(cloud='openstack')

conn.delete_server(INSTANCE_NAME)
