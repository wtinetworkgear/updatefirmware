#!/usr/bin/env python3

import json
import os
import tempfile
import shutil
import sys

try:
    import requests
except ImportError:
    print("The 'requests' modules is required for this code.")
    exit(1)

try:
    import urllib3
except ImportError:
    print("The 'urllib3' modules is required for this code.")
    exit(1)

# supress Unverified HTTPS request, only do this in a verified environment
urllib3.disable_warnings()

# Address of the WTI device
URI = "https://"
SITE_NAME = "192.168.168.168"

# put in the username and password to your WTI device here
USERNAME = "super"
PASSWORD = "super"

result = ""
forceupgrade = 0
family = 1
fips = None
checkonly = 0

assert sys.version_info >= (3, 0)

if len(sys.argv) == 2:
    if (sys.argv[1] == "force"):
        forceupgrade = 1

print("WTI Device Upgrade Program\n")

tempdata = input("Enter URI [default: %s ]: " % (URI))
if (len(tempdata) > 0):
    URI = tempdata

tempdata = input("Enter Device Address [default: %s ]: " % (SITE_NAME))
if (len(tempdata) > 0):
    SITE_NAME = tempdata

tempdata = input("Enter Device Username [default: %s ]: " % (USERNAME))
if (len(tempdata) > 0):
    USERNAME = tempdata

tempdata = input("Enter Device Password [default: %s ]: " % (PASSWORD))
if (len(tempdata) > 0):
    PASSWORD = tempdata

tempdata = input("Check Only [default: %s ]: " % ("No"))
if (len(tempdata) > 0):
    if ((tempdata.upper() == "YES") or (tempdata.upper() == "Y")):
        checkonly = 1

try:
    # 1. Get the current version and the device type of a WTI device
    fullurl = ("%s%s/cgi-bin/getfile" % (URI, SITE_NAME))

    print("\n\n\nChecking version and type of WTI device at: %s%s" % (URI, SITE_NAME))

    response = requests.get(URI+SITE_NAME+"/api/v2/status/firmware", auth=(USERNAME, PASSWORD), verify=False)
    if (response.status_code == 200):
        result = response.json()

        statuscode = result["status"]["code"]
        if (int(statuscode) != 0):
            exit(1)

#		Uncomment to see the JSON return by the unit
#        print(response.text)
        local_release_version = result["config"]["firmware"]
        try:
            family = result['data']["config"]["family"]
        except Exception as ex:
            family = 1

        try:
            fips = result['data']["config"]["fips"]
            if (fips == 0):
                fips = 1  # MAKE 2, 1 ONLY TEST: get me the no fips or merged code
        except Exception as ex:
            fips = 1

        print("Device reports Version: %s, Family: %s\n" % (local_release_version, ("Console" if family == 1 else "Power")))
    else:
        print("Error Step 1: %s\n" % (response.status_code))
        exit(0)

    # 2. Go online and find the latest version of software for this WTI device
    fullurl = ("https://my.wti.com/update/version.aspx?fam=%s" % (family))
    if (fips is not None):
        fullurl = ("%s&fipsonly=%d" % (fullurl, fips))

    print("Checking WTI for the latest OS version for a %s unit\n" % (("Console" if family == 1 else "Power")))

    response = requests.get(fullurl)
    if (response.status_code == 200):
        result = response.json()
    else:
        print("Error Step 1: %s\n" % (response.status_code))
        exit(0)

    remote_release_version = result["config"]["firmware"]

    if ((float(local_release_version) < 6.58) & (family == 1)) | ((float(remote_release_version) < 2.15) & (family == 0)):
        print("Error: WTI Device does not support remote upgrade\n")
        exit(0)

    print("WTI reports the latest of a %s is Version: %s\n" % (("Console" if family == 1 else "Power"), remote_release_version))

    if (int(result["code"]) == 0):
        local_filename = None
        if ((float(local_release_version) < float(remote_release_version)) or (forceupgrade == 1)):
            if (checkonly == 0):
                online_file_location = result["config"]["imageurl"]

                local_filename = online_file_location[online_file_location.rfind("/")+1:]
                local_filename = tempfile.gettempdir() + "/" + local_filename

                print("Downloading %s --> %s\n" % (online_file_location, local_filename))

                response = requests.get(online_file_location, stream=True)
                handle = open(local_filename, "wb")
                for chunk in response.iter_content(chunk_size=512):
                    if chunk:  # filter out keep-alive new chunks
                        handle.write(chunk)
                handle.close()

                # SEND the file to the WTI device
                fullurl = ("%s%s/cgi-bin/getfile" % (URI, SITE_NAME))
                files = {'file': ('name.binary', open(local_filename, 'rb'), 'application/octet-stream')}

                print("Sending %s --> %s%s\n" % (local_filename, URI, SITE_NAME))

                response = requests.post(fullurl, files=files, auth=(USERNAME, PASSWORD), verify=False, stream=True)
                result = response.json()

                print("response: %s\n" % (response))
                print(response.text)

                if (response.status_code == 200):
                    parsed_json = response.json()
                    if (int(parsed_json['status']["code"]) == 0):
                        print("\n\nUpgrade Successful, please wait a few moments while [%s] processes the file.\n" % (SITE_NAME))
                    else:
                        print("\n\nUpgrade Failed for [%s].\n" % (SITE_NAME))

                os.remove(local_filename)
            else:
                print("Device at [%s] is out of date.\n" % (SITE_NAME))
        else:
            print("Device at [%s] is up to date.\n" % (SITE_NAME))

    else:
        print("Error: %s\n" % (response.status_code))

except requests.exceptions.RequestException as e:
    print (e)
