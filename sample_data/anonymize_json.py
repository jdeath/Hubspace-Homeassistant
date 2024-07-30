#!/usr/bin/env python3

import re
import argparse
import sys
import uuid
import random

parser = argparse.ArgumentParser(description = 'Anonymize the JSON output for Hubspace, so that it can be shared')

parser.add_argument('--infile', '-i', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument('--outfile', '-o', nargs='?', type=argparse.FileType('w'), default=sys.stdout)
args = parser.parse_args()

infile = args.infile.read()

# Replace UUIDs
uuid_re = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
unique_uuids = set(re.findall(uuid_re, infile))
for unique_uuid in unique_uuids:
	infile = infile.replace(unique_uuid, str(uuid.uuid4()))

# Replace Times
# 13 digits includes dates since late 2001
# Keep times in relative order, add random value less than ~15 minutes
time_re = re.compile('[0-9]{13}')
unique_times = sorted(set(re.findall(time_re, infile)))
random_increasing_offset = random.randint(1, 1000000)
for unique_time in unique_times:
	infile = infile.replace(unique_time, str(int(unique_time) + random_increasing_offset))
	random_increasing_offset += random.randint(1, 1000000)

# Replace Lat / Long
latlong_re = re.compile(r'"(-?[0-9]{1,3}\.[0-9]*)"')
unique_latlongs = set(re.findall(latlong_re, infile))
for unique_latlong in unique_latlongs:
	infile = infile.replace(unique_latlong, str(random.random()))

# Replace Friendly Names
friendlyname_re = re.compile('"friendlyName": "([^"]*)"')
unique_friendlynames = set(re.findall(friendlyname_re, infile))
i = 0
for unique_friendlyname in unique_friendlynames:
	infile = infile.replace(unique_friendlyname, 'Friendly Name ' + str(i))
	i += 1

# Replace MACs
mac_re = re.compile('"([0-9a-f]{12})"')
unique_macs = set(re.findall(mac_re, infile))
for unique_mac in unique_macs:
	infile = infile.replace(unique_mac, '%12x' % random.randrange(16**12))

# Replace SSIDs
ssid_re = re.compile('"wifi-ssid",.*?"value": "(.*?)"', re.DOTALL)
unique_ssids = set(re.findall(ssid_re, infile))
i = 0
for unique_ssid in unique_ssids:
	infile = infile.replace(unique_ssid, "SSID" + str(i))
	i += 1

args.outfile.write(infile)