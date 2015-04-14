#!/usr/bin/python2.7
import datetime
import logging
from logging.handlers import SysLogHandler
import os
import plistlib
import pwd
import subprocess
import sys
from SystemConfiguration import SCDynamicStoreCopyConsoleUser
import urllib
import urllib2
import xml.etree.cElementTree as etree

# Setup logging to output to the console as well as system messages
logger = logging.getLogger("system-log-tag") # JAMF IT uses the tag "jamfsw-it-logs"
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
syslog_handler = SysLogHandler(address='/var/run/syslog')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)

# Obtain the logged in username for the Mac as well as Self Service
console_user = pwd.getpwnam(SCDynamicStoreCopyConsoleUser(None, None, None)[0])
jss_url = 'com.yourorg.package' # For example: com.jamfsw.inventorypkg
logged_in_user = sys.argv[3]
logger.info("Logged in user: {0}".format(logged_in_user))

# The 'jss_auth' string is expected to be a base64 string:
# ~$ echo "username:password" | base64
# This is a handy shortcut opposed to passing the two values as separate parameters
jss_auth = sys.argv[4]

# Strings for the name and description fields for the enrollment profile
profile_name = "Staff Enrollment Profile: {0}".format(logged_in_user)
profile_description = "Personal enrollment profile for {0}".format(logged_in_user)

# Set values for the Enrollment Profile
profile_identifier = '00000000-0000-0000-A000-4B424E470111' # Replace this with the UUID that can be found in one of your JSS's existing enrollment profiles
profile_org = 'Your Org' # Replace with your org's name


class JSS(object):
    def __init__(self, url, auth):
        self.auth = auth
        self.server = url + '/JSSResource'

    def get_enrollment_profile(self, id_name):
        try:
            int(id_name)
        except ValueError:
            jss_type = 'name'
        else:
            jss_type = 'id'

        request_url = '{0}/mobiledeviceenrollmentprofiles/{1}/{2}'.format(self.server, jss_type, urllib.quote(id_name))
        request = urllib2.Request(request_url)
        logger.debug("GET {0}".format(request_url))
        return self.request(request)

    def create_enrollment_profile(self, name, description, username):
        root = etree.Element('mobile_device_enrollment_profile')
        general = etree.SubElement(root, 'general')
        etree.SubElement(general, 'name').text = name
        etree.SubElement(general, 'description').text = description
        location = etree.SubElement(root, 'location')
        etree.SubElement(location, 'username').text = username

        post_data = etree.tostring(root)
        logger.debug("New enrollment profile data:\n{0}".format(post_data))

        request_url = '{0}/mobiledeviceenrollmentprofiles/id/0'.format(self.server)
        request = urllib2.Request(request_url, post_data)
        request.get_method = lambda: 'POST'
        logger.debug("POST {0}".format(request_url))
        return etree.fromstring(self.request(request)).findtext('id')

    def request(self, request):
        request.add_header('Authorization', 'Basic ' + self.auth)
        request.add_header('Content-Type', 'text/xml')
        try:
            response = urllib2.urlopen(request)
        # except ValueError as e:
        #     print("an error occurred during the search: {0}".format(e.message))
        #     print("check the URL used and try again\n")
        #     sys.exit(1)
        except urllib2.HTTPError as e:
            logger.warning("{0}: {1}".format(e.code, e.reason))
            if e.code == 404:
                return False
            else:
                logger.error("Response headers:\n{0}".format(e.hdrs))
                logger.error("Response text:\n{0}".format(e.read()))
                logger.exception("Traceback:")
                sys.exit(1)
        except Exception as e:
            logger.exception("an unknown error has occurred: {0}: {1}\n".format(type(e).__name__, e.message))
            sys.exit(1)

        return response.read()


jss = JSS(jss_url, jss_auth)

# The script will attempt to lookup an existing profile of the above name
# If it exists the data in that profile will be used and a new one will not be created
jss_enrollment_profile = jss.get_enrollment_profile(profile_name)
if not jss_enrollment_profile:
    # If there is no pre-existing enrollment profile for the user, one will be created now
    logger.info("Creating new personal enrollment profile for {0}".format(logged_in_user))
    new_profile = jss.create_enrollment_profile(profile_name, profile_description, logged_in_user)
    # The created profile returns an ID value that is used to read back its information
    logger.info("Created new enrollment profile at ID: {0}".format(new_profile))
    jss_enrollment_profile = jss.get_enrollment_profile(new_profile)
else:
    logger.info("Found existing enrollment profile for {0}".format(logged_in_user))

# Convert the returned data from the API into an ElementTree object
jss_enrollment_profile = etree.fromstring(jss_enrollment_profile)

# The .mobileconfig profile is now constructed as a Python dictionary
logger.info("Building .mobileconfig data")
mobile_config = dict()
mobile_config['PayloadUUID'] = jss_enrollment_profile.findtext('general/uuid')
mobile_config['PayloadOrganization'] = profile_org
mobile_config['PayloadVersion'] = 1
mobile_config['PayloadIdentifier'] = profile_identifier
mobile_config['PayloadDescription'] = profile_description
mobile_config['PayloadType'] = 'Profile Service'
mobile_config['PayloadDisplayName'] = profile_name
profile_payload_content = dict()
profile_payload_content['Challenge'] = jss_enrollment_profile.findtext('general/invitation')
profile_payload_content['URL'] = '{0}//otaenroll/'.format(jss_url)
profile_payload_content['DeviceAttributes'] = ['UDID', 'PRODUCT', 'SERIAL', 'VERSION', 'DEVICE_NAME', 'COMPROMISED']
mobile_config['PayloadContent'] = profile_payload_content

# Filename and path values are generated
filename = 'personal-enrollment-{0}-{1}.mobileconfig'.format(logged_in_user.split('.')[0],
                                                             datetime.datetime.today().strftime('%Y-%m-%d'))
file_path = '{0}/Desktop/{1}'.format(console_user.pw_dir, filename)

# The .mobileconfig profile is saved to the user's Desktop with the correct permissions and ownership
logger.info("Saving .mobileconfig file to: {0}".format(file_path))
with open(file_path, 'w') as f:
    plistlib.writePlist(dict(mobile_config), f)
    os.chmod(file_path, 0640)
    os.chown(file_path, console_user.pw_uid, 20)

# A Finder window will be opened revealing the new .mobileconfig file
logger.info("Revealing .mobileconfig file in Finder")
subprocess.Popen(['/usr/bin/open', '-R', file_path]).communicate()

logger.info("Done")
sys.exit(0)