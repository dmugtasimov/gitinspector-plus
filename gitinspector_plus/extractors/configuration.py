# Copyright (c) 2013 Ejwa Software. All rights reserved.
# Copyright (c) 2015 Dmitry Mugtasimov. All rights reserved.
#
# This file is part of gitinspector_plus.
#
# gitinspector_plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector_plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector_plus. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from gitinspector_plus.utils import run_git_config_command


BOOLEAN_ACTION_TYPES = ('store_true', 'store_false')
BOOLEAN_REPRESENTATIONS = {'1': True, 'yes': True, 'true': True, 't': True, 'on': True,
                           '0': False, 'no': False, 'false': False, 'f': False, 'off': False}


def convert_to_boolean(value):
    try:
        return BOOLEAN_REPRESENTATIONS[value.lower()]
    except KeyError:
        raise ValueError(_("The given option argument is not a valid boolean."))


def get_git_config_option_name(commandline_option):
    option_names = filter(lambda s: s.startswith('--'), commandline_option.args)
    if len(option_names) == 1:
        return option_names[0].lstrip('-')
    else:
        raise ValueError('Could not get option string for '
                         'commandline option: {}'.format(commandline_option.args))


def get_git_config_option_type(commandline_option):
    if commandline_option.kwargs.get('action') in BOOLEAN_ACTION_TYPES:
        return bool
    return None


def get_git_config_option_value(name, type_):
    lines = run_git_config_command(('gitinspector-plus.' + name,))
    if not lines:
        return None

    value = lines[0]
    if type_ is bool:
        value = convert_to_boolean(value)

    return value


def get_git_config_options(commandline_options, skip):
    git_config_options = {}
    for clo in commandline_options:
        name = get_git_config_option_name(clo)
        if name in skip:
            continue

        type_ = get_git_config_option_type(clo)
        value = get_git_config_option_value(name, type_)
        if value is not None:
            git_config_options[name] = get_git_config_option_value(name, type_)

    return git_config_options
