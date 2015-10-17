import re
import datetime

from gitinspector_plus.utils import (run_git_ls_tree_command, run_git_rev_list_command,
                                     run_git_blame_command, get_revision_range)

from gitinspector_plus import interval


class BlameStats(object):

    def __init__(self):
        self.total = 0
        self.by_author = {}
        self.by_author_and_filename = {}

    def add(self, author, filename):
        self.total += 1

        try:
            self.by_author[author] += 1
        except KeyError:
            self.by_author[author] = 1

        try:
            self.by_author_and_filename[(author, filename)] += 1
        except KeyError:
            self.by_author_and_filename[(author, filename)] = 1

    def get_stats_by_author(self):
        return self.by_author

    def get_stats_by_author_and_filename(self):
        return self.by_author_and_filename


class BlameLine(object):

    def __init__(self):
        self.revision = None
        self.time = None
        self.email = None
        self.filename = None
        self.line = None

REVISION_REGEX = re.compile(r'[0-9a-f]{40}')


def blame_lines(rows):
    rows_iterator = iter(rows)
    while True:
        blame_line = BlameLine()
        take = True
        for row in rows_iterator:
            row = row.decode('utf-8', 'replace').strip()
            t = row.split(' ', 1)
            key, value = t if len(t) == 2 else (t[0], None)
            if key == 'boundary' and interval.get_since():
                take = False
            elif key == 'author-mail':
                blame_line.email = value.lstrip('<').rstrip('>')
            elif key == 'author-time':
                blame_line.time = datetime.date.fromtimestamp(int(value))
            elif key == 'filename':
                blame_line.filename = value
                blame_line.line = rows_iterator.next()
                break
            elif REVISION_REGEX.match(key):
                blame_line.revision = key
        else:
            break

        if take:
            yield blame_line


def get_revision_filenames(revision):
    return run_git_ls_tree_command(('--name-only', '-r', revision))


def get_revisions(revision_start=None, revision_end='HEAD', type_=frozenset):
    revision_range = get_revision_range(revision_start, revision_end)
    return type_(
        run_git_rev_list_command(
            filter(None, ('--reverse', '--no-merges',
                          interval.get_since(),
                          interval.get_until(), revision_range))))


def normalize_line(line):
    # TODO(dmu) HIGH: Refactor this strange encoding/decodings
    line = line.strip().decode('unicode_escape', 'ignore')
    line = line.encode('latin-1', 'replace')
    line = line.decode('utf-8', 'replace').strip('"').strip("'").strip()
    return line


# TODO(dmu) HIGH: Recover file filtering
# TODO(dmu) HIGH: Recover extention filtering
def calculate_blame_stats(hard=False, revision_start=None, revision_end='HEAD'):
    revision_range = get_revision_range(revision_start, revision_end)
    filenames = get_revision_filenames(revision_end)
    revisions = get_revisions(revision_start, revision_end)
    blame_stats = BlameStats()
    for filename in filenames:
        filename = normalize_line(filename)
        blame_arguments = filter(None, ('--line-porcelain', '-w') +
                                       (('-C', '-C', '-M') if hard else ()) +
                                       (interval.get_since(), revision_range, "--",
                                       filename))

        output_lines = run_git_blame_command(blame_arguments)
        for blame_line in blame_lines(output_lines):
            if blame_line.revision in revisions:
                blame_stats.add(blame_line.email, blame_line.filename)

    return blame_stats
