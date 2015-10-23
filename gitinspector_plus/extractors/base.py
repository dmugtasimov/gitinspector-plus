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


import os
import re
from gitinspector_plus.utils import (REVISION_END_DEFAULT, get_revision_range, run_git_log_command,
                                     get_since_option, get_until_option)

INCLUDE_ALL_EXTENSIONS = '**'
EMPTY_EXTENSION_MARKER = '*'


class AddLineException(Exception):
    pass


class ExtensionFilter(object):

    INCLUDE_ALL_EXTENSIONS = '**'
    EMPTY_EXTENSION_MARKER = '*'

    def __init__(self, include_extensions):
        self.allow_any_extension = include_extensions == self.INCLUDE_ALL_EXTENSIONS
        self.include_extensions = (() if self.allow_any_extension else
                                   frozenset(include_extensions.split(',')))
        self.allow_empty_extension = (self.allow_any_extension or
                                      EMPTY_EXTENSION_MARKER in self.include_extensions)

    def is_allowed(self, extension):
        return (self.allow_any_extension or (extension == '' and self.allow_empty_extension) or
                extension in self.include_extensions)


class ExcludeFilter(object):

    FILE_TYPE = 'file'
    TYPE_ATTR_MAP = {
        'author': 'author',
        'email': 'email',
        'revision': 'revision',
# TODO(dmu) LOW: Support original message filtering
#        'message': '?',
    }

    @classmethod
    def create_filter(cls, filter_expression):
        filter_expression_splitted = filter_expression.split(':', 1)
        if len(filter_expression_splitted) == 1:
            filter_type, filter_regex = 'file', filter_expression
        elif len(filter_expression_splitted) == 2:
            filter_type, filter_regex = filter_expression_splitted
        else:
            raise ValueError('Invalid filter expression format')

        if filter_type == cls.FILE_TYPE:
            return ExcludeFileFilter(filter_type, filter_regex)
        else:
            return ExcludeCommitFilter(filter_type, filter_regex)

    def __init__(self, filter_type, filter_regex):
        self.filter_type = filter_type
        self.filter_regex = re.compile(filter_regex)

    def is_excluded(self, filtered_object):
        raise NotImplementedError()


class ExcludeCommitFilter(ExcludeFilter):

    def __init__(self, filter_type, filter_regex):
        super(ExcludeCommitFilter, self).__init__(filter_type, filter_regex)
        self.commit_attr = self.TYPE_ATTR_MAP.get(self.filter_type)
        if not self.commit_attr:
            raise ValueError(u'Unknown filter type: {}'.format(self.filter_type))

    def is_excluded(self, commit):
        return bool(self.filter_regex.search(getattr(commit, self.commit_attr, '')))


class ExcludeFileFilter(ExcludeFilter):

    def is_excluded(self, file_path):
        return bool(self.filter_regex.match(file_path))


class FileDiff(object):

    INSERTIONS_DELETIONS_REGEX = re.compile(r'^ +(\d+|Bin)')

    def __init__(self, line, file_path, insertions=0, deletions=0, binary=False):
        self.line = line
        self.file_path = file_path
        self.insertions = insertions
        self.deletions = deletions
        self.total_changes = self.insertions + self.deletions
        self.binary = binary

    @property
    def extension(self):
        return os.path.splitext(self.file_path)[1][1:]

    @classmethod
    def build_instance_or_none(cls, line):
        splitted_line = line.split('|')
        if len(splitted_line) == 2:
            insertions_deletions = splitted_line[1]
            m = cls.INSERTIONS_DELETIONS_REGEX.match(insertions_deletions)
            if m:
                group_1 = m.group(1)
                if group_1 == 'Bin':
                    return cls(line=line,
                               file_path=splitted_line[0].strip(),
                               binary=True)
                else:
                    insertions = insertions_deletions.count('+')
                    deletions = insertions_deletions.count('-')
                    changes = int(group_1)
                    if int(group_1) != insertions + deletions:
                        raise ValueError(u'Total changes of {} do not match sum of insertions '
                                         u'({}) and deletions ({})'.format(changes, insertions,
                                                                     deletions))
                    return cls(line=line,
                               file_path=splitted_line[0].strip(),
                               insertions=insertions,
                               deletions=deletions)
            else:
                raise ValueError(u'Unexpected syntax of change details: {}'.format(line))


class Commit(object):
    SUMMARY_REGEX = re.compile(r'^ (?P<files_changed>\d+) files changed'
                               r'(?:, (?P<insertions>\d+) insertions\(\+\))'
                               r'(?:, (?P<deletions>\d+) deletions\(-\))')

    @classmethod
    def build_instance_or_none(cls, line, extension_filter=None, file_filters=()):
        splitted_line = line.split('|')
        if len(splitted_line) == 4:
            return cls(line=line,
                       date=splitted_line[0],
                       revision=splitted_line[1],
                       author=splitted_line[2],
                       email=splitted_line[3],
                       extension_filter=extension_filter,
                       file_filters=file_filters)

    def __init__(self, line, date, revision, author, email, extension_filter=None,
                 file_filters=None):
        self.line = line
        self.date = date
        self.revision = revision
        self.author = author
        self.email = email
        self.extension_filter = extension_filter
        self.file_filters = file_filters

        self.author_email = u'{} ({})'.format(author, email)
        self.extensions = set()
        self.file_diffs = []

    @property
    def insertions(self):
        return sum(file_diff.insertions for file_diff in self.file_diffs)

    @property
    def deletions(self):
        return sum(file_diff.deletions for file_diff in self.file_diffs)

    @property
    def total_changes(self):
        return sum(file_diff.total_changes for file_diff in self.file_diffs)

    @property
    def files_changed(self):
        return len(self.file_diffs)

    def append_file_diff(self, file_diff):
        extension = file_diff.extension
        self.extensions.add(extension)

        if not (self.extension_filter and self.extension_filter.is_allowed(extension)):
            return

        if not any(ff.is_excluded(file_diff.file_path) for ff in self.file_filters):
            self.file_diffs.append(file_diff)

    def add_line(self, line):
        if not line:
            # Empty line is fine too
            return

        m = self.SUMMARY_REGEX.match(line)
        if m:
            return

        file_diff = FileDiff.build_instance_or_none(line)
        if file_diff:
            self.append_file_diff(file_diff)
            return

        raise AddLineException()


def count_changed_files(commits):
    return len(set(file_diff.file_path for commit in commits for file_diff in commit.file_diffs))


class AuthorInformation(object):

    def __init__(self, author, email):
        self.author = author
        self.email = email
        self.commits = []
        self.insertions = 0
        self.deletions = 0
        self.total_changes = 0

    def append_commit(self, commit):
        self.commits.append(commit)
        self.add_insertions(commit.insertions)
        self.add_deletions(commit.deletions)

    def add_insertions(self, insertions):
        self.insertions += insertions
        self.total_changes += insertions

    def add_deletions(self, deletions):
        self.deletions += deletions
        self.total_changes += deletions

    @property
    def files_changed(self):
        return count_changed_files(self.commits)


class RepositoryStatistics(object):

    def __init__(self, hard=False, since=None, until=None, revision_start=None,
                 revision_end=REVISION_END_DEFAULT, extension_filter=None, exclude_filters=()):

        self.hard = hard
        self.since = since
        self.until = until
        self.revision_start = revision_start
        self.revision_end = revision_end
        self.revision_range = get_revision_range(self.revision_start, self.revision_end)
        self.extension_filter = extension_filter
        self.file_filters = [ef for ef in exclude_filters if isinstance(ef, ExcludeFileFilter)]
        self.commit_filters = [ef for ef in exclude_filters if isinstance(ef, ExcludeCommitFilter)]

        self.commits = []
        self.insertions = 0
        self.deletions = 0
        self.total_changes = 0
        self.extensions = set()

        self.author_information = {}
        self.author_to_email_map = {}
        self.email_to_author_map = {}
        self.ambiguous_authors = set()
        self.ambiguous_emails = set()

    def append_commit(self, commit):
        self.commits.append(commit)
        self.add_insertions(commit.insertions)
        self.add_deletions(commit.deletions)
        self.extensions.update(commit.extensions)

    def add_insertions(self, insertions):
        self.insertions += insertions
        self.total_changes += insertions

    def add_deletions(self, deletions):
        self.deletions += deletions
        self.total_changes += deletions

    @property
    def files_changed(self):
        return count_changed_files(self.commits)

    def build_commit_or_none(self, line):
        return Commit.build_instance_or_none(line, self.extension_filter, self.file_filters)

    def process_commits(self):

        lines = run_git_log_command(
            filter(None, (('--reverse', '--pretty=%cd|%H|%aN|%aE',
                           '--stat=1000000,8192', '--no-merges', '-w', get_since_option(self.since),
                           get_until_option(self.until), '--date=short') +
                          (('-C', '-C', '-M') if self.hard else ()) + (self.revision_range,))))

        commit = None
        line = None
        lines_iterator = iter(lines)
        while True:
            try:
                while not commit:
                    commit = self.build_commit_or_none(lines_iterator.next())

                while True:
                    line = lines_iterator.next()
                    commit.add_line(line)
            except (StopIteration, AddLineException) as e:
                if commit and commit.files_changed and not any(cf.is_excluded(commit) for cf
                                                               in self.commit_filters):
                    author_information_item = self.author_information.get(commit.author_email)
                    if not author_information_item:
                        email_set = self.author_to_email_map.setdefault(commit.author, set())
                        email_set.add(commit.email)
                        if len(email_set) > 1:
                            # Same author with different emails
                            self.ambiguous_authors.add(commit.author)

                        author_set = self.email_to_author_map.setdefault(commit.email, set())
                        author_set.add(commit.author)
                        if len(author_set) > 1:
                            # Same email with different names
                            self.ambiguous_emails.add(commit.email)

                        author_information_item = AuthorInformation(commit.author, commit.email)
                        self.author_information[commit.author_email] = author_information_item

                    author_information_item.append_commit(commit)
                    self.append_commit(commit)
                if isinstance(e, StopIteration):
                    break
                elif line:
                    commit = self.build_commit_or_none(line)
