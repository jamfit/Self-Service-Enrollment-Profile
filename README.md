# Self Service Enrollment Profile

## What were we trying to solve?

The majority of technical staff at JAMF Software are provisioned multiple OS X and iOS devices for production and testing use. Submission of inventory of these test devices is a requirement of the JAMF Software security policies. As logging into the over-the-air enrollment page on each of these devices can be a chore (some staff manage entire kits of devices), we created an option in Self Service for them to generate an iOS enrollment profile for inventory purposes.

Only JSS admins have the privileges to create enrollment profiles. We wanted to provide this ability without elevating permissions to the JSS, but at the same time take steps to ensure the inventory of the JSS was properly maintained and devices were correctly assigned as staff used these profiles to enroll them.

## What does it do?

This script makes use of the JSS API. When run from Self Service the script checks the JSS for an existing enrollment profile for the user who is running the policy. This is done by checking for the expected name of a profile had the script generated it (e.g. "Staff Enrollment Profile: bryson.tyrrell"). If the profile exists, the script will obtain the existing enrollment invitation from it. If not, the script will create a new enrollment profile for the user (using their username for the location data - ensuring all uses of this enrollment invitation associate the device to them) and then read back the enrollment invitation.

Once the enrollment invitation has been obtained, the script will build the .mobileconfig file and save it to the user's desktop. The user can then use this enrollment profile on their iOS devices to submit inventory.

There are numerous comments throughout the code that explain what is being done at the various stages.

## How to deploy this script in a policy

Upload the script to your JSS and create a policy. You will want to modify some of the variables in the script (e.g. the package's 'jss_url' on line 28, the 'PayloadOrganization' value on line 123 and the 'PayloadIdentifier' value on line 125) for your organization.
The basic authorization string for the JSS API is passed on line 96. Opposed to reading in both the username and password as separate values, the script expects the parameter to be the base64 string that would be used. You can generate this string using the following shell command:

```
~$ echo "username:password" | base64
``` 

This is only a shortcut to allow us to pass a single parameter for the JSS API user instead of two. You can modify the script to accept the two parameters with the following Python code:

```
import base64
jss_user = sys.argv[4]
jss_pass = sys.argv[5]
jss_auth = base64.b64encode(jss_user + ':' + jss_pass)
```

## License

```
Copyright (c) 2015, JAMF Software, LLC. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this
      list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this
      list of conditions and the following disclaimer in the documentation and/or
      other materials provided with the distribution.
    * Neither the name of the JAMF Software, LLC nor the names of its contributors
      may be used to endorse or promote products derived from this software without
      specific prior written permission.
      
THIS SOFTWARE IS PROVIDED BY JAMF SOFTWARE, LLC "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL JAMF SOFTWARE,
LLC BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```