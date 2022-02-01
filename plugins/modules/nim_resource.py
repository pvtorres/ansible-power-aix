#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2022- IBM, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
 Module to display, create and remove nim resources
"""

from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule
import re

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
author:
- AIX Development Team (@pvtorres1703)
module: nim_resource
short_description: Display/define/delete nim object resources
description:
- This module facilitates the display/creation/removal of nim resources 
- Root user is required.
options:
  action:
    description:
    - Specifies the action to be performed for the tunables.
    - C(show) displays the current nim allocated resources
    - C(present) creates a nim resource.
    - C(absent) remove a nim resource
    type: str
    choices: [ show, display, present, absent ]
    default: None
    required: true
  name:
    description:
    - Specifies the resource name
    type: str
    default: None
    required: true
  object_type:
    description:
    - Type of the resource to be allocated. Example: spot, lpp_source
    - It must be provided when "action" option is "created" or "delete"
    type: str
    default: None
    required: true
  source:
    descrition:
    - Specifies the path of the LPP source
    type: path
    required: no
  location:
    descrition:
    - Specifies the path of the software code to create the resource.
    type: path
    required: no
'''


EXAMPLES = r'''
- hosts: nim_server
  gather_facts: no
- tasks:

  - name: Display/show all NIM objects.
    ibm.power_aix.nim_resource:
      action: show

  - name: Define a NIM lpp_source resource
    ibm.power_aix.nim_resource:
      action: present
      name: lpp_730
      object_type: lpp_resource
      source: /software/AIX7300
      location: /nim1/lpp_730_resource

  - name: Define a NIM spot (Shared product Object Tree)
          using and defined lpp_source.
    ibm.power_aix.nim_resource:
      action: present
      name: spot_730
      object_type: spot
      location: /nim1/spot_730_resource
      source: lpp_730

  - name: Display/show a NIM object resource.
    ibm.power_aix.nim_resource:
      action: show
      name: lpp_730

  - name: Remove a resource NIM object.
    ibm.power_aix.nim_resource:
      action: absent
      name: spot_730

'''

RETURN = r'''
msg:
    description: The execution message.
    returned: always
    type: str
    sample: 'Resource spot_730 was removed.'
rc:
    description: The return code.
    returned: If the command failed.
    type: int
stdout:
    description: The standard output.
    returned: If the command failed.
    type: str
stderr:
    description: The standard error.
    returned: If the command failed.
    type: str
'''

'''

'''


results = None

def res_show(module):
    '''
    Display nim resources.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        Message for successfull command
    '''

    global results

    msg = ''
    cmd = '/usr/sbin/lsnim -l'
    name = module.params['name']
    object_type = module.params['object_type']

    # This module will only display general information about resource object class
    if not object_type and not name:
        cmd += ' -c resources'

    if object_type:
        cmd += ' -t {0}'.format(object_type)

    if name:
        cmd += ' ' + name

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd

    if return_code != 0:

        pattern = "0042-053"
        found = re.search(pattern, stderr)

        if found:
            results['msg'] = 'There is no NIM object resource named {0} '.format(name)
        else:
            results['msg'] = 'Error trying to display object {0}'.format(name)
            results['rc'] = return_code
            module.fail_json(**results)

    return 0

def res_present(module):
    '''
    Createa a NIM resource.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        Message for successfull command
    '''

    cmd = '/usr/sbin/nim -a server=master -o define '
    msg = ''
    changed = True
    name = module.params['name']
    object_type = module.params['object_type']
    source = module.params['source']
    location = module.params['location']

    if object_type:
        cmd += ' -t ' + object_type

    if source:
        cmd += ' -a source=' + source

    if location:
        cmd += ' -a location=' + location

    if name:
        cmd += ' ' + name

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd

    if return_code != 0:

        pattern = "0042-081"
        found = re.search(pattern, stderr)
        if not found:
            results['rc'] = return_code
            results['msg'] = 'Error trying to define resource {0} '.format(name)
            module.fail_json(**results)
        else:
            results['msg'] = 'Resource already exist'
            changed = False
    else:
        results['msg'] = 'Creation of resource {0} was a success'.format(name)

    return 0

def res_absent(module):
    '''
    Remove a NIM resource.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        Message for successfull command
    '''

    name = module.params['name']
    cmd = '/usr/sbin/nim -o remove {0}'.format(name)
    msg = ''
    name = module.params['name']

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd

    if return_code != 0:

        pattern = "0042-053"
        found = re.search(pattern, stderr)

        if found:
            results['msg'] = 'There is no NIM object resource named {0} '.format(name)
        else:
            results['msg'] = 'Error trying to remove NIM object {0}'.format(name)
            results['rc'] = return_code
            module.fail_json(**results)

    else:
        results['msg'] = 'Resource {0} was removed.'.format(name)

    return 0


def main():
    global results
    module = AnsibleModule(
        argument_spec=dict(
            action=dict(type='str', required=True, choices=['show', 'display', 'present', 'absent']),
            name=dict(type='str'),
            object_type=dict(type='str'),
            source=dict(type='path'),
            location=dict(type='path'),
        ),
#        mutally_exclusive=[
#           ["object_type", "bbb"]
#        ],
        supports_check_mode=False
    )

    results = dict(
        changed=False,
        msg='',
        stdout='',
        stderr='',
    )

    msg = ""
    msg_temp = ""

    action = module.params['action']

    if action == 'display':
        action = 'show'

    if action == 'remove':
        action = 'absent'

    if action == 'allocate':
        action = 'present'

    if action == 'show':
        res_show(module)
    elif action == 'present':
        res_present(module)
    elif action == 'absent':
        res_absent(module)
    else :
        msg += 'The action selected is NOT recognized. Please check again.'
        module.fail_json(msg=msg)

    module.exit_json(**results)


if __name__ == '__main__':
    main()
