from __future__ import print_function

import textwrap
import sys

from gitinspector_plus.renderers.base import BaseRenderer
from gitinspector_plus import terminal
from gitinspector_plus.changes import HISTORICAL_INFO_TEXT, NO_COMMITED_FILES_TEXT
from gitinspector_plus.blame import BLAME_INFO_TEXT
from gitinspector_plus import format


def render_changes_text(changes):

    if changes.author_information:
        print(textwrap.fill(_(HISTORICAL_INFO_TEXT) + ':', width=terminal.get_size()[0]) + '\n')
        terminal.print_bold(terminal.ljust(_('Author'), 21) + terminal.rjust(_('Commits'), 13) +
                        terminal.rjust(_('Insertions'), 14) + terminal.rjust(_('Deletions'), 15) +
                terminal.rjust(_('% of changes'), 16))

        changes_count = changes.changes
        for author_key in sorted(changes.author_information.iterkeys()):
            author_information = changes.author_information[author_key]
            if changes_count:
                percentage = 100 * author_information.changes / float(changes_count)
            else:
                percentage = None

            author_string = author_information.author
            print(terminal.ljust(author_string, 20)[
                  0:20 - terminal.get_excess_column_count(author_string)], end=' ')
            print(str(len(author_information.commits)).rjust(13), end=' ')
            print(str(author_information.insertions).rjust(13), end=' ')
            print(str(author_information.deletions).rjust(14), end=' ')
            if percentage is None:
                print('-'.rjust(15))
            else:
                print('{0:.2f}'.format(percentage).rjust(15))
    else:
        print(_(NO_COMMITED_FILES_TEXT) + ".")


def render_blame_text(blame_stats):
    if sys.stdout.isatty() and format.is_interactive_format():
        terminal.clear_row()

    print(textwrap.fill(_(BLAME_INFO_TEXT) + ":", width=terminal.get_size()[0]) + '\n')

    terminal.print_bold(terminal.ljust(_('Author'), 21) +
                        terminal.rjust(_('Rows'), 10)) # +
#                        terminal.rjust(_('Stability'), 15) +
#                        terminal.rjust(_('Age (days)'), 13) +
#                        terminal.rjust(_('% in comments'), 20))

    for author, rows in sorted(blame_stats.get_stats_by_author().iteritems(),
                               key=lambda t: -t[1]):
        print(terminal.ljust(author, 20)[0:20 - terminal.get_excess_column_count(author)],
              end=' ')  # Author
        print(str(rows).rjust(10))  # Rows
        #print("{0:.1f}".format(self.blame.get_stability(item[0], item[1].rows, self.changes)
#                               ).rjust(14), end=' ')  # Stability
#        print("{0:.1f}".format(float(item[1].skew) / item[1].rows).rjust(12), end=' ')  # Age
#        print("{0:.2f}".format(100.0 * item[1].comments / item[1].rows).rjust(19))  # last
