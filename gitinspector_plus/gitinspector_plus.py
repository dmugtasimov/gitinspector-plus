#!/usr/bin/env python
# coding: utf-8
#
# Copyright © 2012-2015 Ejwa Software. All rights reserved.
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

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from gitinspector_plus import localization
localization.init()

import logging
import argparse
import atexit
import os
import sys

from collections import namedtuple
from gitinspector_plus.config import GitConfigArg
from gitinspector_plus import (basedir, blame, changes, clone, config, extensions, filtering,
                               format, interval, metrics, outputable, responsibilities, terminal,
                               timeline)
from gitinspector_plus.version import __version__


Argument = namedtuple('Argument', ('args', 'kwargs'))


class Runner(object):

    def __init__(self, repo='.', hard=False, include_metrics=False, list_file_types=False,
                 localize_output=False, responsibilities=False, grading=False, timeline=timeline,
                 use_weeks=False, format='text'):
        self.repo = repo

        self.grading = grading
        if self.grading:
            self.hard = True
            self.list_file_types = True
            self.include_metrics = True
            self.responsibilities = True
            self.use_weeks = True
            self.timeline = True
        else:
            self.hard = hard
            self.list_file_types = list_file_types
            self.include_metrics = include_metrics
            self.responsibilities = responsibilities
            self.use_weeks = use_weeks
            self.timeline = timeline

        self.localize_output = localize_output
        self.format = format

    def output_new(self):
        pass

    def output(self):
        #if self.format == 'text':
        #    self.output_new()
        #    return

        if not self.localize_output:
            localization.disable()

        terminal.skip_escapes(not sys.stdout.isatty())
        terminal.set_stdout_encoding()
        previous_directory = os.getcwd()

        os.chdir(self.repo)
        absolute_path = basedir.get_basedir_git()
        os.chdir(absolute_path)
        format.output_header()
        outputable.output(changes.ChangesOutput(self.hard))

        all_changes = changes.get(self.hard)
        if all_changes.get_commits():
            outputable.output(blame.BlameOutput(all_changes, self.hard, self.use_weeks))

            if self.timeline:
                outputable.output(timeline.Timeline(all_changes, self.use_weeks))

            if self.include_metrics:
                outputable.output(metrics.Metrics())

            if self.responsibilities:
                outputable.output(responsibilities.ResponsibilitiesOutput(self.hard,
                                                                          self.use_weeks))

            outputable.output(filtering.Filtering())

            if self.list_file_types:
                outputable.output(extensions.Extensions())

        format.output_footer()
        os.chdir(previous_directory)


def check_python_version():
    if sys.version_info < (2, 7):
        sys.exit(_('gitinspector requires at least Python 2.7.x to run '
                   '(version {0} was found).').format(sys.version))


class ForgivingArgumentParser(argparse.ArgumentParser):

    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        return args


def main():
    terminal.check_terminal_encoding()
    terminal.set_stdin_encoding()

    check_python_version()

    try:
        parser = argparse.ArgumentParser(
            description='List information about the repository in REPOSITORY. If no repository is '
                        'specified, the current directory is used. If multiple repositories are '
                        'given, information will be fetched from the last repository specified.',
            epilog='gitinspector_plus will filter statistics to only include commits that modify, '
                   'add or remove one of the specified extensions, see -f or --file-types for '
                   'more information. gitinspector_plus requires that the git executable is '
                   'available in your PATH. Please, report gitinspector_plus bugs to '
                   'dmugtasimov@gmail.com.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('repository', metavar='REPOSITORY', nargs='?', default='.')
        arguments = (
            Argument(args=('-f', '--file-types'),
                     kwargs=dict(metavar='EXTENSIONS', dest='file_types',
                                 default='java,c,cc,cpp,h,hh,hpp,py,glsl,rb,js,sql',
                                 help='a comma separated list of file extensions to include when '
                                      'computing statistics. Specifying * includes files with no '
                                      'extension, while ** includes all files')),
            Argument(args=('-F', '--format'),
                     kwargs=dict(dest='format', default='text',
                                 choices=('html', 'htmlembedded', 'text', 'xml'),
                                 help='define in which format output should be generated')),
            Argument(args=('--grading',),
                     kwargs=dict(action='store_true',
                                 help='show statistics and information in a way that is formatted '
                                      'for grading of student projects; this is the same as '
                                      'supplying the options -HlmrTw')),
            Argument(args=('-H', '--hard'),
                     kwargs=dict(action='store_true', dest='hard',
                                 help='dtrack rows and look for duplicates harder; this can be '
                                      'quite slow with big repositories')),
            Argument(args=('-l', '--list-file-types'),
                     kwargs=dict(action='store_true', dest='list_file_types',
                                 help='list all the file extensions available in the current '
                                      'branch of the repository')),
            Argument(args=('-L', '--localize-output'),
                     kwargs=dict(action='store_true', dest='localize_output',
                                 help='list all the file extensions available in the current '
                                      'branch of the repository')),
            Argument(args=('-m', '--metrics'),
                     kwargs=dict(action='store_true', dest='metrics',
                                 help='include checks for certain metrics during the analysis of '
                                      'commits')),
            Argument(args=('-r', '--responsibilities'),
                     kwargs=dict(action='store_true', dest='responsibilities',
                                 help='show which files the different authors seem most '
                                      'responsible for')),
            Argument(args=('--since',),
                     kwargs=dict(metavar='DATE', default=None,
                                 help='only show statistics for commits more recent than '
                                      'a specific date')),
            Argument(args=('-T', '--timeline'),
                     kwargs=dict(action='store_true', dest='timeline',
                                 help='show commit timeline, including author names')),
            Argument(args=('--until',),
                     kwargs=dict(metavar='DATE', default=None,
                                 help='only show statistics for commits older than a specific '
                                      'date')),
            Argument(args=('-w', '--weeks'),
                     kwargs=dict(action='store_true', dest='weeks',
                                 help='show all statistical information in weeks instead of in '
                                      'months')),
            Argument(args=('-x', '--exclude'),
                     kwargs=dict(metavar='PATTERN', action='append', dest='exclude',
                                 help='an exclusion pattern describing the file paths, revisions, '
                                      'revisions with certain commit messages, author names or '
                                      'author emails that should be excluded from the statistics; '
                                      'can be specified multiple times')),
            Argument(args=('--log-level',), kwargs=dict(dest='log_level', default='INFO')),
        )

        git_config_args = []
        for argument in arguments:
            parser.add_argument(*argument.args, **argument.kwargs)

            option_strings = filter(lambda s: s.startswith('--'), argument.args)
            if len(option_strings) == 1:
                option_string = option_strings[0]
            else:
                raise ValueError('Could not get option string for '
                                 'option: {}'.format(argument.args))

            action = argument.kwargs.get('action')
            if action in ('store_true', 'store_false'):
                action_type = bool
            else:
                action_type = None
            git_config_args.append(GitConfigArg(name=option_string.lstrip('-'), type=action_type))

        parser.add_argument('--version', action='version', version=__version__)

        args = parser.parse_args()
        # Try to clone the repo or return the same directory and bail out
        repo = clone.create(args.repository)
        git_configuration = config.get_git_configuration(repo, git_config_args)
        parser.set_defaults(**git_configuration)

        args = parser.parse_args()

        logging.basicConfig(level=args.log_level, format='> %(message)s')

        runner = Runner(repo=repo, grading=args.grading, hard=args.hard,
                        list_file_types=args.list_file_types, include_metrics=args.metrics,
                        responsibilities=args.responsibilities, use_weeks=args.weeks,
                        timeline=args.timeline, localize_output=args.localize_output,
                        format=args.format)

        extensions.define(args.file_types)
        if not format.select(args.format):
            raise format.InvalidFormatError(_('specified output format not supported.'))

        if args.since:
            interval.set_since(args.since)

        if args.until:
            interval.set_until(args.until)

        if args.exclude:
            filtering.clear()
            for item in args.exclude:
                filtering.add(item)

    except (filtering.InvalidRegExpError, format.InvalidFormatError) as exception:
        print(sys.argv[0], "\b:", exception.msg, file=sys.stderr)
        print(_('Try: {0} --help for more information.').format(sys.argv[0]), file=sys.stderr)
        return 2

    runner.output()


@atexit.register
def cleanup():
    clone.delete()


if __name__ == "__main__":
    sys.exit(main())
