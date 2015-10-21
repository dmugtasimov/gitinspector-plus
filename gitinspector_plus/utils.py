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

import subprocess
from itertools import chain
import os
import logging

try:
    from shlex import quote  # TODO(dmu) MEDIUM: Why trying shlex?
except ImportError:
    from pipes import quote


logger = logging.getLogger(__name__)


class CustomPopen(subprocess.Popen):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()
        # Wait for the process to terminate, to avoid zombies.
        self.wait()


class InDirectory(object):

    def __init__(self, directory):
        self.pre_directory = None
        self.directory = directory

    @staticmethod
    def chdir(directory):
        logger.debug('change dir: {}'.format(directory))
        os.chdir(directory)

    def __enter__(self):
        current_directory = os.getcwd()
        if current_directory != os.path.abspath(self.directory):
            self.pre_directory = current_directory
            self.chdir(self.directory)

    def __exit__(self, type, value, traceback):
        if self.pre_directory:
            self.chdir(self.pre_directory)


def run_command(command_definition):
    command_text = ' '.join(command_definition)
    logger.debug(command_text)
    with CustomPopen(command_definition, bufsize=1, stdout=subprocess.PIPE) as process:
        if process.stdout:
            return [line.decode('utf-8', 'replace').rstrip('\r\n')
                    for line in process.stdout.readlines()]
        else:
            raise Exception(u'No output from: {}'. format(command_text))


def run_git_command(arguments):
    return run_command(tuple(chain(('git',), arguments)))


def run_git_rev_list_command(arguments):
    return run_git_command(tuple(chain(('rev-list',), arguments)))


def run_git_log_command(arguments):
    return run_git_command(tuple(chain(('log',), arguments)))


def run_git_ls_tree_command(arguments):
    return run_git_command(tuple(chain(('ls-tree',), arguments)))


def run_git_blame_command(arguments):
    return run_git_command(tuple(chain(('blame',), arguments)))


def run_git_config_command(arguments):
    return run_git_command(tuple(chain(('config',), arguments)))


def get_revision_range(revision_start=None, revision_end='HEAD'):
    if revision_start:
        return revision_start + '..' + revision_end
    else:
        return revision_end


def get_since_option(since):
    return '--since=' + quote(since) if since else None


def get_until_option(until):
    return '--until=' + quote(until) if until else None


REVISION_END_DEFAULT = 'HEAD'