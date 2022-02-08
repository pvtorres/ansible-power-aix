 #!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2022- IBM, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
 Module to show, create or remove NIM object resources
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
short_description: show/define/delete nim object resources
description:
- This module facilitates the display/creation/removal of nim resource objects.
- Root user access is required.
- Not all the module variables are needed for all the operations.
options:
  action:
    description:
    - Specifies the action to be performed:
    - C(show) shows NIM resource object or a NIM resource provied by I(name)
      into a "nim_resources" type=dic .
    - C(present) define (create) a NIM resource object with provided I(name),
      I(object_type) and I(attributes).
    - C(absent) remove a NIM resource object with provided I(name).
    type: str
    choices: [ show, present, absent ]
    default: None
    required: true
  name:
    description:
    - Specifies the NIM object name.
    type: str
    default: None
    required: true
  object_type:
    description:
    - Type of the resource for action I(state=present), I(state=absent),
      I(state=show).
    - Example of the object_types:
      -- lpp_source
      -- spot
      -- bosinst_data
      -- mksysb
      -- fb_script
      -- res_group
    - For details of the supported resources, refer to the IBM documentation at
      U(https://www.ibm.com/docs/en/aix/7.2?topic=management-using-nim-resources)
    type: str
    default: None
    required: true for I(state=present)
  attributes:
    description:
    - Specifies the attribute-value pairs for I(state=present) or I(state=show)
    - Examples:
      - source: Source device, absolute path for the images or ISO image to
                create a copy to the "location"
      - location: Specifies directory that contatins the code to define
                the resource.
    default: None
    required: None

'''


EXAMPLES = r'''

  - name: Show all NIM resource objects.
    ibm.power_aix.nim_resource:
      action: show

  - name: Create a copy of the images from source to location and
          define a NIM lpp_source resource from the location.
    ibm.power_aix.nim_resource:
      action: present
      name: lpp_730
      object_type: lpp_resource
      attributes:
        source: /software/AIX7300
        location: /nim1/copy_AIX7300_resource

  - name: Define a NIM lpp_source resource object from a directory that
          contains the installation images.
    ibm.power_aix.nim_resource:
      action: present
      name: lpp_730
      object_type: lpp_resource
      attributes:
        location: /nim1/copy_AIX7300_resource

  - name: Define a NIM spot (Shared Product Object Tree) resource
          using a defined lpp_source.
    ibm.power_aix.nim_resource:
      action: present
      name: spot_730
      object_type: spot
      attributes:
        source: lpp_730
        location: /nim1/spot_730_resource

  - name: Show a NIM resource object.
    ibm.power_aix.nim_resource:
      action: show
      name: lpp_730

  - name: Remove a resource NIM object.
    ibm.power_aix.nim_resource:
      action: absent
      name: spot_730

  - name: Create a NIM resource group object.
    ibm.power_aix.nim_resource:
      action: present
      name: ResGrp730
      object_type: res_group
      attributes:
        lpp_source: lpp_730
        spot: spot_730
        bosinst_data: bosinst_data730
        comments: "730 Resources"

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
nim_resource_found:
    description: Return if a queried object resource exist.
    returned: for C(show), 1 if an object is found, 0 if it is not.
    type: bool
nim_resources:
    description: Dictionary output with the NIM resource object information.
    returned: for C(show)
    type: dict
    sample:{
           lpp_source_test:
             'Rstate': ready for use,
             'alloc_count': '0',
             'arch': power,
             'class': resources,
             'location': /nim1/lpp_source_test4,
             'prev_state': unavailable for use,
             'server': master,
             'simages': 'yes',
             'type': lpp_source,
           }

'''

'''

'''


results = None

def res_show(module):
    '''
    Show nim resources.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        updated results dictionary.
    '''

    global results

    msg = ''
    cmd = '/usr/sbin/lsnim -l'
    name = module.params['name']
    object_type = module.params['object_type']

    # This module will only show general information about the resource
    # object class.
    if not object_type and not name:
        cmd += ' -c resources'

    if object_type:
        cmd += ' -t {0}'.format(object_type)

    if name:
        cmd += ' ' + name

    if module.check_mode:
        results['msg'] = 'Command \'{0}\' preview mode, execution skipped.'.format(cmd)
        return

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd
    results['nim_resources'] = {}
    results['nim_resource_found'] = '0'

    if return_code != 0:

        # 0042-053 The NIM objefct is not there.
        pattern = r"0042-053"
        found = re.search(pattern, stderr)

        if found:
            results['msg'] = 'There is no NIM object resource named {0} '.format(name)
        else:
            results['msg'] = 'Error trying to display object {0}'.format(name)
            results['rc'] = return_code
            module.fail_json(**results)
    else:
        results['nim_resources'] = build_dic(stdout)
        results['nim_resource_found'] = '1'

    return

def res_present(module):
    '''
    Define a NIM resource object.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        updated results dictionary.
    '''

    cmd = '/usr/sbin/nim -a server=master -o define '
    msg = ''
    opts = ""

    name = module.params['name']
    object_type = module.params['object_type']
    attributes = module.params['attributes']

    if object_type:
        cmd += ' -t ' + object_type

    if attributes is not None:
        for attr, val in attributes.items():
             opts += " -a {0}=\"{1}\" ".format(attr, val)
        cmd += opts

    if name:
        cmd += ' ' + name

    if module.check_mode:
        results['msg'] = 'Command \'{0}\' preview mode, execution skipped.'.format(cmd)
        return

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd

    if return_code != 0:

       # 0042-081 The resource already exists on "master"
        pattern = r"0042-081"
        found = re.search(pattern, stderr)
        if not found:
            results['rc'] = return_code
            results['msg'] = 'Error trying to define resource {0} '.format(name)
            module.fail_json(**results)
        else:
            results['msg'] = 'Resource already exist'

    else:
        results['msg'] = 'Creation of resource {0} was a success'.format(name)
        results['changed'] = True

    return

def res_absent(module):
    '''
    Remove a NIM resource object.

    arguments:
        module  (dict): The Ansible module
    note:
        Exits with fail_json in case of error
    return:
        updated results dictionary.
    '''

    name = module.params['name']
    cmd = '/usr/sbin/nim -o remove {0}'.format(name)
    msg = ''

    if module.check_mode:
        results['msg'] = 'Command \'{0}\' in preview mode, execution skipped.'.format(cmd)
        return

    return_code, stdout, stderr = module.run_command(cmd)

    results['stderr'] = stderr
    results['stdout'] = stdout
    results['cmd'] = cmd

    if return_code != 0:

        # 0042-053 The NIM objefct is not there.
        pattern = r"0042-053"
        found = re.search(pattern, stderr)

        if found:
            results['msg'] = 'There is no NIM object resource named {0} '.format(name)
        else:
            results['msg'] = 'Error trying to remove NIM object {0}'.format(name)
            results['rc'] = return_code
            module.fail_json(**results)

    else:
        results['msg'] = 'Resource {0} was removed.'.format(name)
        results['changed'] = True

    return


def build_dic(stdout):
    """
    Build dictionary with the stdout info

    arguments:
        stdout   (str): stdout of the command to parse
    returns:
        info    (dict): NIM object dictionary
    """

    info1 = {}
    info = {}

    lines = stdout.splitlines()

    for line in lines :

        key = (line.split('=')[0]).strip()
        size = len( line.split('='))

        if size > 1:
            value = (line.split('=')[1]).strip()
            info1[key] = value
        else:
            info[key[:-1]] = info1
            info1.clear()

    return info

def main():
    global results
    module = AnsibleModule(
        argument_spec=dict(
            action=dict(type='str', required=True, choices=['show', 'present', 'absent']),
            name=dict(type='str'),
            object_type=dict(type='str'),
            attributes=dict(type='dict'),
        ),
        supports_check_mode=True
    )

    results = dict(
        changed=False,
        msg='',
        stdout='',
        stderr='',
    )

    msg = ""

    action = module.params['action']

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
