from __future__ import print_function

import textwrap
import sys
from terminaltables.base_table import BaseTable

from gitinspector_plus import terminal
from gitinspector_plus.renderers.base import BaseRenderer
from gitinspector_plus.changes import HISTORICAL_INFO_TEXT, NO_COMMITED_FILES_TEXT
from gitinspector_plus.blame import BLAME_INFO_TEXT
from gitinspector_plus import format


class TextRenderer(BaseRenderer):

    def render_commit_statistics(self, repo_stats):
        if not repo_stats.author_information:
            print(_(NO_COMMITED_FILES_TEXT) + ".")
            return

        table_data = [
            [_('Author'), _('Commits'), _('Files'), _('Insertions'), _('Deletions'),
             _('Total changes'), _('% of changes')],
        ]

        total_changes = repo_stats.total_changes
        for key, info in sorted(repo_stats.author_information.iteritems(), key=lambda x: x[0]):
            if (info.author in repo_stats.ambiguous_authors or
                    info.email in repo_stats.ambiguous_emails):
                name = u'{} ({})'.format(info.author, info.email)
            else:
                name = info.author

            table_data.append(
                [name, str(len(info.commits)), str(info.files_changed), str(info.insertions),
                 str(info.deletions), str(info.total_changes),
                 '{0:.2f}'.format(100 * info.total_changes / float(total_changes)) if total_changes
                 else '-']
            )

        table = BaseTable(table_data)
        table.inner_column_border = False
        table.inner_heading_row_border = False
        table.outer_border = False
        table.padding_left = 0
        table.padding_right = 2
        table.justify_columns = {0: 'left', 1: 'right', 2: 'right', 3: 'right', 4: 'right',
                                 5: 'right', 6: 'right'}

        print(textwrap.fill(_(HISTORICAL_INFO_TEXT) + ':', width=terminal.get_size()[0]) + '\n')
        print(table.table)


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
