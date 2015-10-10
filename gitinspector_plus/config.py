# coding: utf-8
#
# Copyright © 2013 Ejwa Software. All rights reserved.
#
# This file is part of gitinspector.
#
# gitinspector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from collections import namedtuple
import os
import subprocess


BOOLEAN_REPRESENTATIONS = {'1': True, 'yes': True, 'true': True, 't': True, 'on': True,
                           '0': False, 'no': False, 'false': False, 'f': False, 'off': False}

GitConfigArg = namedtuple('GitConfigArg', ('name', 'type'))


def read_git_config_variable(repo, variable):
    previous_directory = os.getcwd()
    os.chdir(repo)
    output = subprocess.Popen(('git', 'config', 'gitinspector-plus.' + variable),
                              bufsize=1, stdout=subprocess.PIPE).stdout
    os.chdir(previous_directory)

    try:
        setting = output.readlines()[0]
    except IndexError:
        return None

    return setting.decode('utf-8', 'replace').strip()


def convert_to_boolean(value):
    try:
        return BOOLEAN_REPRESENTATIONS[value.lower()]
    except KeyError:
        raise ValueError(_("The given option argument is not a valid boolean."))


def get_git_configuration(repo, args):
    config_dict = {}
    for arg in args:
        value = read_git_config_variable(repo, arg.name)
        if value is None:
            continue

        if arg.type in (None, str, unicode):
            pass
        elif arg.type is bool:
            value = convert_to_boolean(value)
        else:
            raise ValueError('Unknown argument type: {}'.format(arg.type))

        config_dict[arg.name] = value

    return config_dict
