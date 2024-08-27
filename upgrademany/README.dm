# WTI Multi-Device Upgrade Demonstration

This WTI Multi-Device Upgrade program will query WTI devices for their version and device type, then go online to see if there is a newer version available. If there is a newer version it will be downloaded and the WTI device updated.

This `Multi-Device Upgrade` Python script will work on any modern WTI device, the device upgrade automation calls are universal on all WTI OOB and PDU type devices.

If no upgrade local files are defined on the command line, then the newest software update will be downloaded from the WTI website.

# To Configure Python Script:
This Python script requires Python 3.0 and above and the `requests` module.

# wtiupgrade.ini configuration file
A WTI device login parameters can be configured via a txt .ini file, a sample one is included with this project called wtiupgrade.ini.

Valid parameters are:

[192.168.168.168] - This is the main header, either an IP address (i.e. 192.168.168.168) or a URL (wti.example.com)
username - username to access WTI device
userpassword - password to access WTI device
secure - yes: use https or no: use http
verify = yes: if using secure will validate certificates or no: will ignore certificates


# To Run:
`python3 upgrademany.py`

# To Run is Dry Run mode

If you want to only check the devices without updating, you can run the program in 'Dry Run' mode:
python3 upgrademany.py --dryrun yes


To get any command line parameters that can be used, you can issue this command.
`python3 upgrademany.py -h`

# Contact US
This software is presented for demonstration purposes only, but if you have any questions, comments or suggestions you can email us at kenp@wti.com

# About Us
WTI - Western Telematic, Inc.
5 Sterling, Irvine, California 92618

Western Telematic Inc. was founded in 1964 and is an industry leader in designing and manufacturing power management and remote console management solutions for data centers and global network locations. 
Our extensive product line includes Intelligent PDUs for remote power distribution, metering, reporting and control, Serial Console Servers, RJ45 A/B Fallback Switches and Automatic Power Transfer Switches.