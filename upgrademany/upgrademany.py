#!/usr/bin/env python3

# 1.0 Initial Release
# 1.1 Added user token authentication support
#
# sample command line examples:
# python3 upgrade.py
# python3 upgrade.py --mode force
# python3 upgrade.py --consolefile /tmp/uimage_3352_tsm_arm.md5
# python3 upgrade.py --consolefile /tmp/uimage_3352_tsm_arm.md5 --consolepower /tmp/uimage_3352_vmr_arm.md5

#import json
import os
import tempfile
#import shutil
import sys
import getopt
import configparser
import re
from datetime import datetime

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
#SITE_NAME = "192.168.0.223"

# put in the username and password to your WTI device here
USERNAME = "super"
PASSWORD = "super"
TOKEN = ""

usersuppliedfilename = None
result = ""
authtype = 0   # 0 - username/password, 1 = token
forceupgrade = 0
family = 1
iFilesRemoteDownload = 0    # 1 = power, 2 = console, 2 = both
dryrun = 0
parameterspassed = 0
ConsoleFileName = ""
PowerFileName = ""
UnitUpdateStatus = ""

assert sys.version_info >= (3, 0)

# Get the Family of the filename, -1 = None, 0 = Power, 1 = Console
def FileNameFamily(usersuppliedfilename):
    iFam = -1

    try:
        ifilesize = os.path.getsize(usersuppliedfilename)
        file = open(usersuppliedfilename, 'rb')
        file.seek(ifilesize-20)
        fileread = file.read()
        if (fileread.find(b'TSM') >= 0):
            iFam = 1
        elif (fileread.find(b'VMR') >= 0):
            iFam = 0
        file.close()
        print("FileNameFamily - User Supplied file [%s] is a %s type." % (usersuppliedfilename, ("Console" if iFam == 1 else "Power")))
    except Exception as ex:
        print("FileNameFamily - User Supplied file [%s] does not exist\n\n" % (usersuppliedfilename))
        print(ex)
    return iFam

print("WTI Many Device Upgrade Program 2.0 (Python)\n")

# Get the status file name, based on date/time
now = datetime.now()

# Format the date and time as a string
StatusFileName = now.strftime("%Y-%m-%d-%H:%M:%S.txt")

try:
    argv = sys.argv[1:]
    opts, args = getopt.getopt(argv, 'hm:c:p:d:', ["mode=", "consolefile=", "powerfile=", "dryrun="])

    for opt, arg in opts:
        if opt == '-h':
            print ('upgrademany.py --consolefile <localimagefilename> --powerfile <localimagefilename> --dryrun yes --mode force')
            exit(0)
        elif opt in ("-m", "--mode"):
            if (arg == "force"):
                forceupgrade = 1
            parameterspassed = (parameterspassed | 1)
        elif opt in ("-c", "--consolefile"):
            ConsoleFileName = arg
            parameterspassed = (parameterspassed | 2)
        elif opt in ("-p", "--powerfile"):
            PowerFileName = arg
            parameterspassed = (parameterspassed | 4)
        elif opt in ("-d", "--dryrun"):
            if ((arg.upper() == "YES") or (arg.upper() == "Y")):
                dryrun = 1
            parameterspassed = (parameterspassed | 8)

except getopt.GetoptError:
    print ('upgrademany.py --consolefile <localimagefilename> --powerfile <localimagefilename> --dryrun yes --mode force')
    exit(2)

try:
    config = configparser.ConfigParser()

    config.sections()
    # Open the file wit hthe hostname, username and password entries
    config.read('wtiupgrade.ini')
    config.sections()

    for section_name in config.sections():
        URI = "http://"
        SITE_NAME = ""
        USERNAME = ""
        PASSWORD = ""
        TOKEN = ""
        VERIFY = False
        sNewPassword = ""
        UnitUpdateStatus = "fail"

        SITE_NAME = section_name
        for name, value in config.items(section_name):
            if (name == "username"):
                USERNAME = value
            if (name == "userpassword"):
                PASSWORD = value
            if (name == "token"):
                TOKEN = value                
            if (name == "secure"):
                if (value == "yes"):
                    URI = "https://"
            if (name == "verify"):
                if (value == "yes"):
                    VERIFY = True

        if ((len(URI) == 0) or (len(SITE_NAME) == 0) or ((len(USERNAME) == 0) or (len(PASSWORD) == 0) and (len(TOKEN) == 0))):
            print("Zero length something, Stop and check your .ini file")
            exit(0)

        # 1. Get the current version and the device type of a WTI device
        print("\nChecking version and type of WTI device at: %s%s" % (URI, SITE_NAME))

        try:
            response = requests.get(URI+SITE_NAME+"/api/v2/status/firmware", auth=(USERNAME, PASSWORD), verify=False)
            if (response.status_code == 200):
                result = response.json()

                statuscode = result["status"]["code"]
                if (int(statuscode) != 0):
                    exit(1)

#	        	Uncomment to see the JSON return by the unit
#               print(response.text)
                local_release_version = result["config"]["firmware"]
                try:
                    family = int(result["config"]["family"])    # 0 Power, 1 Console
                except Exception as ex:
                    family = 1

                print("  Device reports Version: %s, Family: %s" % (local_release_version, ("Console" if family == 1 else "Power")))

                # Console, lets see if the defined file is the right type
                if ((family == 1) & (len(ConsoleFileName) > 0)):
                    if (family != FileNameFamily(ConsoleFileName)):
                        print("  FAMILY MISMATCH: Your local file is Console, remote is %s" % ("Console" if family == 1 else "Power"))
                        exit(3)
                elif ((family == 0) & (len(PowerFileName) > 0)):
                    if (family != FileNameFamily(PowerFileName)):
                        print("  FAMILY MISMATCH: Your local file is Power, remote is %s" % ("Console" if family == 1 else "Power"))
                        exit(3)

            else:
                if (response.status_code == 404):
                    # lets see its its an older PPC unit
                    response = requests.get(URI+SITE_NAME+"/cgi-bin/gethtml?formWTIProductStatus.html", auth=(USERNAME, PASSWORD), verify=False)
                    if (response.status_code == 200):
                        result = response.text.find('PPC / ')
                        if (result >= 0):
                            print("\n[%s] is a PPC type unit. These units are EOL and do not support the RESTFUL API command set." % (SITE_NAME))
                            exit(4)

                print("  Error Step 1: %s\n" % (response.status_code))
                exit(5)

            # 2. Go online (if file does not exist) and find the latest version of software for this WTI device if there was not local file defined
            fullurl = ("https://my.wti.com/update/version.aspx?fam=%s" % (family))

            # print("Checking WTI for the latest OS version for a %s unit\n" % (("Console" if family == 1 else "Power")))

            response = requests.get(fullurl)
            if (response.status_code == 200):
                result = response.json()

                remote_release_version = result["config"]["firmware"]

                # remove any 'alpha' or 'beta' designations
                match = re.match(r"^\d+(\.\d+)?", local_release_version)
                if match:
                    local_release_version = float(match.group())

                if ((float(local_release_version) < 6.58) & (family == 1)) | ((float(remote_release_version) < 2.15) & (family == 0)):
                    print("  Error: WTI Device does not support remote upgrade (%d)\n" % (family))
                else:
                    print("  WTI (online) reports the latest %s Version: %s" % (("Console" if family == 1 else "Power"), remote_release_version))
                    statuscode = result['status']["code"]

                    if (int(statuscode) == 0):
                        local_filename = None
                        if ((float(local_release_version) < float(remote_release_version)) or (forceupgrade == 1)):
                            if (dryrun == 0):
                                iNeedFile = 0

                                if ((family == 1) & (len(ConsoleFileName) == 0)):
                                    iNeedFile = 1

                                if ((family == 0) & (len(PowerFileName) == 0)):
                                    iNeedFile = 1

                                if (iNeedFile == 1):
                                    online_file_location = result["config"]["imageurl"]

                                    local_filename = online_file_location[online_file_location.rfind("/")+1:]
                                    local_filename = tempfile.gettempdir() + "/" + local_filename

                                    print("  Downloading %s --> %s\n" % (online_file_location, local_filename))

                                    response = requests.get(online_file_location, stream=True)
                                    handle = open(local_filename, "wb")
                                    for chunk in response.iter_content(chunk_size=512):
                                        if chunk:  # filter out keep-alive new chunks
                                            handle.write(chunk)
                                    handle.close ()

                                    if (family == 1):
                                        ConsoleFileName = local_filename
                                        iFilesRemoteDownload = (iFilesRemoteDownload | 2)
                                    else:
                                        PowerFileName = local_filename
                                        iFilesRemoteDownload = (iFilesRemoteDownload | 1)
                                else:
                                    print("  File already downloaded [%s]" % ( ConsoleFileName if family == 1 else PowerFileName))
                                # SEND the file to the WTI device
                                files = {'file': ('name.binary', open(ConsoleFileName if family == 1 else PowerFileName, 'rb'), 'application/octet-stream')}

                                print("  Sending %s --> %s%s\n" % (ConsoleFileName if family == 1 else PowerFileName, URI, SITE_NAME))

                                if (len(TOKEN) == 0):
                                    fullurl = ("%s%s/cgi-bin/getfile" % (URI, SITE_NAME))
                                    response = requests.post(fullurl, files=files, auth=(USERNAME, PASSWORD), verify=False, stream=True)
                                else:
                                    fullurl = ("%s%s/api/getfile" % (URI, SITE_NAME))
                                    header = {'X-WTI-API-KEY': "%s" % (TOKEN)}
                                    response = requests.post(fullurl, files=files, verify=False, stream=True, headers=header)

                                result = response.json()

                                print("  response: %s\n" % (response))
                                print(response.text)

                                if (response.status_code == 200):
                                    parsed_json = response.json()
                                    if (int(parsed_json['status']["code"]) == 0):
                                        print("\n\n  Upgrade Successful, please wait a few moments while [%s] processes the file.\n" % (SITE_NAME))
                                        UnitUpdateStatus = "updated"
                                    else:
                                        print("\n\n  Upgrade Failed for [%s].\n" % (SITE_NAME))
                            else:
                                UnitUpdateStatus = "dry run"                                
                                print("  Device at [%s] is out of date (dryrun was set to yes, no update performed).\n" % (SITE_NAME))
                        else:
                            print("  Device at [%s] is up to date.\n" % (SITE_NAME))
                            UnitUpdateStatus = "up to date"
                    else:
                        print("  Error: %s\n" % (response.status_code))
            else:
                print("  Error Place 1: (%d) (my.wti.com)" % (response.status_code))

        except requests.exceptions.RequestException as e:
            print (e)
            UnitUpdateStatus = "not responding"

        # write status file
        now = datetime.now()
        WriteLine = "%s%s,%s,%s\n" % (URI, SITE_NAME, UnitUpdateStatus, now.strftime("%Y-%m-%d %H:%M:%S"))
#        print("%s" % (WriteLine))

        file = open(StatusFileName, 'a+')
        file.write(WriteLine)
        file.close()

    print ("iFilesRemoteDownload = (%d)" % (iFilesRemoteDownload))
    # only remove if the file was downloaded
    if ((iFilesRemoteDownload & 2) == 2):
        if (len(ConsoleFileName) > 0):
            os.remove(ConsoleFileName)

    if ((iFilesRemoteDownload & 1) == 1):
        if (len(PowerFileName) > 0):
            os.remove(PowerFileName)

except requests.exceptions.RequestException as e:
    print (e)
