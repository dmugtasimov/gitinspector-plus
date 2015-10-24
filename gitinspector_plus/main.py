#!/usr/bin/env python
# Copyright (c) 2012-2015 Ejwa Software. All rights reserved.
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

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from gitinspector_plus import localization
localization.init()

import logging
import argparse
import os
import sys
from collections import namedtuple

from gitinspector_plus.renderers.text import TextRenderer, render_blame_text
from gitinspector_plus.extractors.blame import calculate_blame_stats
from gitinspector_plus.extractors.base import INCLUDE_ALL_EXTENSIONS, EMPTY_EXTENSION_MARKER, \
    RepositoryStatistics, ExtensionFilter, ExcludeFilter
from gitinspector_plus.utils import InDirectory, REVISION_END_DEFAULT
from gitinspector_plus.extractors.configuration import get_git_config_options
from gitinspector_plus import (basedir, blame, changes, extensions, filtering,
                               format, interval, metrics, outputable, responsibilities, terminal,
                               timeline)
from gitinspector_plus.version import __version__

Argument = namedtuple('Argument', ('args', 'kwargs'))

HTML_OUTPUT_FORMAT = 'html'
HTML_EMDEDDED_OUTPUT_FORMAT = 'htmlembedded'
TEXT_OUTPUT_FORMAT = 'text'
XML_OUTPUT_FORMAT = 'xml'
OUTPUT_FORMATS = (HTML_OUTPUT_FORMAT, HTML_EMDEDDED_OUTPUT_FORMAT, TEXT_OUTPUT_FORMAT,
                  XML_OUTPUT_FORMAT)
FORMAT_RENDERER_MAP = {
    TEXT_OUTPUT_FORMAT: TextRenderer,
}


class Runner(object):

    def __init__(self, repo='.', hard=False, include_metrics=False, list_file_types=False,
                 localize_output=False, responsibilities=False, grading=False, timeline=False,
                 use_weeks=False, format='text', revision_start=None, revision_end='HEAD'):
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
        self.revision_start = revision_start
        self.revision_end = revision_end

    def output(self):

        if not self.localize_output:
            localization.disable()

        terminal.skip_escapes(not sys.stdout.isatty())
        terminal.set_stdout_encoding()
        previous_directory = os.getcwd()

        os.chdir(self.repo)
        absolute_path = basedir.get_basedir_git()
        os.chdir(absolute_path)
        format.output_header()

        if self.format != 'text':
            outputable_result = changes.ChangesOutput(self.hard)
            outputable.output(outputable_result)
            all_changes = changes.get(self.hard)
        else:
            changes_local = RepositoryStatistics(hard=self.hard,
                                    revision_start=self.revision_start,
                                    revision_end=self.revision_end)
            all_changes = changes_local
            text_renderer = ChangesTextRenderer(changes_local)
            text_renderer.render()

        if all_changes.commits:
            blame_stats = calculate_blame_stats(hard=self.hard,
                                                revision_start=self.revision_start,
                                                revision_end=self.revision_end)

            if self.format != 'text':
                # TODO(dmu) HIGH: Refactor blame.__blame__ = ...
                outputable_result = blame.BlameOutput(all_changes)
                outputable.output(outputable_result)
            else:
                render_blame_text(blame_stats)

            if self.timeline:
                outputable_result = timeline.Timeline(all_changes, self.use_weeks)
                outputable.output(outputable_result)

            if self.include_metrics:
                outputable_result = metrics.Metrics()
                outputable.output(outputable_result)

            if self.responsibilities:
                outputable_result = responsibilities.ResponsibilitiesOutput(self.hard,
                                                                            self.use_weeks)
                outputable.output(outputable_result)

            outputable_result = filtering.Filtering()
            outputable.output(outputable_result)

            if self.list_file_types:
                outputable_result = extensions.Extensions()
                outputable.output(outputable_result)

        format.output_footer()
        os.chdir(previous_directory)


# TODO(dmu) HIGH: Support Python 3.x
def check_python_version():
    if sys.version_info < (2, 7) or sys.version_info >= (3,):
        sys.exit(_('gitinspector_plus requires Python >= 2.7.x < 3.x version to run '
                   '(version {0} was found).').format(sys.version))


def get_commandline_options():
    return (
        Argument(args=('-f', '--file-types'),
                 kwargs=dict(metavar='EXTENSIONS', dest='file_types',
                             default='java,c,cc,cpp,h,hh,hpp,py,glsl,rb,js,sql',
                             help=u'a comma separated list of file extensions to include when '
                                  u'computing statistics. Specifying {} includes files with no '
                                  u'extension, while {} includes all files'.format(
                                  EMPTY_EXTENSION_MARKER, INCLUDE_ALL_EXTENSIONS))),
        Argument(args=('-F', '--format'),
                 kwargs=dict(dest='format', default='text',
                             choices=OUTPUT_FORMATS,
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
        Argument(args=('--until',),
                 kwargs=dict(metavar='DATE', default=None,
                             help='only show statistics for commits older than a specific '
                                  'date')),
        Argument(args=('--revision-start',),
                 kwargs=dict(default=None, dest='revision_start',
                             help='only show statistics for commits starting from this '
                                  'revision (inclusive), any proper git revision is '
                                  'applicable')),
        Argument(args=('--revision-end',),
                 kwargs=dict(default=REVISION_END_DEFAULT, dest='revision_end',
                             help='only show statistics for commits starting from this '
                                  'revision (exclusive), any proper git revision is '
                                  'applicable')),
        Argument(args=('-T', '--timeline'),
                 kwargs=dict(action='store_true', dest='timeline',
                             help='show commit timeline, including author names')),
        Argument(args=('-w', '--weeks'),
                 kwargs=dict(action='store_true', dest='weeks',
                             help='show all statistical information in weeks instead of in '
                                  'months')),
        Argument(args=('-x', '--exclude'),
                 kwargs=dict(metavar='PATTERN', action='append', dest='excludes',
                             help='an exclusion pattern describing the file paths, revisions, '
                                  'revisions with certain commit messages, author names or '
                                  'author emails that should be excluded from the statistics; '
                                  'can be specified multiple times (examples: -x author:Dmitry '
                                  '-x setup.py -x revision:d67a567192757509e853f2f3db0d2bf1783fa508'
                                  ' -x email:admin@example.com)')),
        Argument(args=('--log-level',), kwargs=dict(dest='log_level', default='INFO',
                                                    help='Not configurable via git config '
                                                         'options')),
    )


def main():
    terminal.check_terminal_encoding()
    terminal.set_stdin_encoding()

    check_python_version()

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

    commandline_options = get_commandline_options()
    for commandline_option in commandline_options:
        parser.add_argument(*commandline_option.args, **commandline_option.kwargs)

    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format='> %(message)s')

    with InDirectory(directory=args.repository):
        git_config_options = get_git_config_options(commandline_options, skip=('log_level',))

    parser.set_defaults(**git_config_options)
    args = parser.parse_args()

    exclude_filters = [ExcludeFilter.create_filter(fe) for exclude in args.excludes or ()
                       for fe in exclude.split(',')]

    repo_stats = RepositoryStatistics(hard=args.hard, since=args.since, until=args.until,
                                      revision_start=args.revision_start,
                                      revision_end=args.revision_end,
                                      extension_filter=ExtensionFilter(args.file_types),
                                      exclude_filters=exclude_filters)

    with InDirectory(args.repository):
        repo_stats.process_commits()

    renderer_class = FORMAT_RENDERER_MAP[args.format]
    renderer = renderer_class()
    renderer.render_commit_statistics(repo_stats)

    return
    runner = Runner(repo=args.repository, grading=args.grading, hard=args.hard,
                    list_file_types=args.list_file_types, include_metrics=args.metrics,
                    responsibilities=args.responsibilities, use_weeks=args.weeks,
                    timeline=args.timeline, localize_output=args.localize_output,
                    format=args.format, revision_start=args.revision_start,
                    revision_end=args.revision_end)

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

    runner.output()


if __name__ == "__main__":
    sys.exit(main())
