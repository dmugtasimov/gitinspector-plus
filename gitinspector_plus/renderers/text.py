from __future__ import print_function

import textwrap
import sys

from gitinspector_plus.renderers.base import BaseRenderer
from gitinspector_plus import terminal
from gitinspector_plus.changes import HISTORICAL_INFO_TEXT, NO_COMMITED_FILES_TEXT
from gitinspector_plus.blame import BLAME_INFO_TEXT
from gitinspector_plus import format


class ChangesTextRenderer(BaseRenderer):

    def __init__(self, changes):
        self.changes = changes

    def render(self):
        authorinfo_list = self.changes.get_authorinfo_list()
        total_changes = 0.0

        for i in authorinfo_list:
            total_changes += authorinfo_list.get(i).insertions
            total_changes += authorinfo_list.get(i).deletions

        if authorinfo_list:
            print(textwrap.fill(_(HISTORICAL_INFO_TEXT) + ":", width=terminal.get_size()[0]) + "\n")
            terminal.print_bold(terminal.ljust(_("Author"), 21) + terminal.rjust(_("Commits"), 13) +
                            terminal.rjust(_("Insertions"), 14) + terminal.rjust(_("Deletions"), 15) +
                    terminal.rjust(_("% of changes"), 16))

            for i in sorted(authorinfo_list):
                authorinfo = authorinfo_list.get(i)
                percentage = (0 if total_changes == 0 else
                              (authorinfo.insertions + authorinfo.deletions) / total_changes * 100)

                print(terminal.ljust(i, 20)[0:20 - terminal.get_excess_column_count(i)], end=" ")
                print(str(authorinfo.commits).rjust(13), end=" ")
                print(str(authorinfo.insertions).rjust(13), end=" ")
                print(str(authorinfo.deletions).rjust(14), end=" ")
                print("{0:.2f}".format(percentage).rjust(15))
        else:
            print(_(NO_COMMITED_FILES_TEXT) + ".")


class BlameTextRenderer(BaseRenderer):

    def __init__(self, changes, blame):
        self.changes = changes
        self.blame = blame

    def render(self):
        if sys.stdout.isatty() and format.is_interactive_format():
            terminal.clear_row()

        print(textwrap.fill(_(BLAME_INFO_TEXT) + ":", width=terminal.get_size()[0]) + '\n')

        terminal.print_bold(terminal.ljust(_('Author'), 21) +
                            terminal.rjust(_('Rows'), 10) +
                            terminal.rjust(_('Stability'), 15) +
                            terminal.rjust(_('Age (days)'), 13) +
                            terminal.rjust(_('% in comments'), 20))

        for item in sorted(self.blame.get_summed_blames().items()):
            print(terminal.ljust(item[0], 20)[0:20 - terminal.get_excess_column_count(item[0])],
                  end=' ')  # Author
            print(str(item[1].rows).rjust(10), end=' ')  # Rows
            print("{0:.1f}".format(self.blame.get_stability(item[0], item[1].rows, self.changes)
                                   ).rjust(14), end=' ')  # Stability
            print("{0:.1f}".format(float(item[1].skew) / item[1].rows).rjust(12), end=' ')  # Age
            print("{0:.2f}".format(100.0 * item[1].comments / item[1].rows).rjust(19))  # last
