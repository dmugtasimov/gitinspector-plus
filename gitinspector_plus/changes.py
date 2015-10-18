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

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import datetime
import json
import os
import operator

from cachetools import cachedmethod

from gitinspector_plus.localization import N_
from gitinspector_plus.outputable import Outputable
from gitinspector_plus import extensions
from gitinspector_plus import format
from gitinspector_plus import gravatar
from gitinspector_plus import interval


class FileDiff:
    def __init__(self, string):
        commit_line = string.split("|")

        if commit_line.__len__() == 2:
            self.name = commit_line[0].strip()
            self.insertions = commit_line[1].count("+")
            self.deletions = commit_line[1].count("-")

    @staticmethod
    def is_filediff_line(string):
        string = string.split("|")
        return string.__len__() == 2 and string[1].find("Bin") == -1 and ('+' in string[1] or '-' in string[1])

    @staticmethod
    def get_extension(string):
        string = string.split("|")[0].strip().strip("{}").strip("\"").strip("'")
        return os.path.splitext(string)[1][1:]

    @staticmethod
    def get_filename(string):
        return string.split("|")[0].strip().strip("{}").strip("\"").strip("'")

    @staticmethod
    def is_valid_extension(string):
        extension = FileDiff.get_extension(string)

        for i in extensions.get():
            if (extension == "" and i == "*") or extension == i or i == '**':
                return True
        return False


class AuthorInfo:
    email = None
    insertions = 0
    deletions = 0
    commits = 0


class Changes(object):

    authors = {}
    authors_dateinfo = {}
    authors_by_email = {}
    emails_by_author = {}

    def __init__(self, hard, revision_start=None, revision_end='HEAD'):

        self.cache = {}

        self.hard = hard
        self.revision_start = revision_start
        self.revision_end = revision_end

    @property
    @cachedmethod(operator.attrgetter('cache'))
    def commits(self):
        #commits = extract_changes(self.hard, self, revision_start=self.revision_start,
        #                          revision_end=self.revision_end)

        if commits:
            if interval.has_interval():
                interval.set_ref(commits[-1].sha)

            self.first_commit_date = datetime.date(int(commits[0].date[0:4]),
                                                   int(commits[0].date[5:7]),
                                                   int(commits[0].date[8:10]))
            self.last_commit_date = datetime.date(int(commits[-1].date[0:4]),
                                                  int(commits[-1].date[5:7]),
                                                  int(commits[-1].date[8:10]))

        return commits

    @staticmethod
    def modify_authorinfo(authors, key, commit):
        if authors.get(key, None) == None:
            authors[key] = AuthorInfo()

        if commit.get_filediffs():
            authors[key].commits += 1

        for j in commit.get_filediffs():
            authors[key].insertions += j.insertions
            authors[key].deletions += j.deletions

    def get_authorinfo_list(self):
        if not self.authors:
            for i in self.commits:
                Changes.modify_authorinfo(self.authors, i.author, i)

        return self.authors

    def get_authordateinfo_list(self):
        if not self.authors_dateinfo:
            for i in self.commits:
                Changes.modify_authorinfo(self.authors_dateinfo, (i.date, i.author), i)

        return self.authors_dateinfo

    def get_latest_author_by_email(self, name):
        if not hasattr(name, "decode"):
            name = str.encode(name)

        name = name.decode("unicode_escape", "ignore")
        return self.authors_by_email[name]

    def get_latest_email_by_author(self, name):
        return self.emails_by_author[name]

__changes__ = None


def get(hard):
    global __changes__
    if __changes__ == None:
        __changes__ = Changes(hard)

    return __changes__


HISTORICAL_INFO_TEXT = N_("The following historical commit information, by author, was found in the repository")
NO_COMMITED_FILES_TEXT = N_("No commited files with the specified extensions were found")


class ChangesOutput(Outputable):

    def __init__(self, hard):
        self.changes = get(hard)
        Outputable.__init__(self)

    def output_html(self):
        authorinfo_list = self.changes.get_authorinfo_list()
        total_changes = 0.0
        changes_xml = "<div><div class=\"box\">"
        chart_data = ""

        for i in authorinfo_list:
            total_changes += authorinfo_list.get(i).insertions
            total_changes += authorinfo_list.get(i).deletions

        if authorinfo_list:
            changes_xml += "<p>" + _(HISTORICAL_INFO_TEXT) + ".</p><div><table id=\"changes\" class=\"git\">"
            changes_xml += "<thead><tr> <th>{0}</th> <th>{1}</th> <th>{2}</th> <th>{3}</th> <th>{4}</th>".format(
                           _("Author"), _("Commits"), _("Insertions"), _("Deletions"), _("% of changes"))
            changes_xml += "</tr></thead><tbody>"

            for i, entry in enumerate(sorted(authorinfo_list)):
                authorinfo = authorinfo_list.get(entry)
                percentage = 0 if total_changes == 0 else (authorinfo.insertions + authorinfo.deletions) / total_changes * 100

                changes_xml += "<tr " + ("class=\"odd\">" if i % 2 == 1 else ">")

                if format.get_selected() == "html":
                    changes_xml += "<td><img src=\"{0}\"/>{1}</td>".format(
                                   gravatar.get_url(self.changes.get_latest_email_by_author(entry)), entry)
                else:
                    changes_xml += "<td>" + entry + "</td>"

                changes_xml += "<td>" + str(authorinfo.commits) + "</td>"
                changes_xml += "<td>" + str(authorinfo.insertions) + "</td>"
                changes_xml += "<td>" + str(authorinfo.deletions) + "</td>"
                changes_xml += "<td>" + "{0:.2f}".format(percentage) + "</td>"
                changes_xml += "</tr>"
                chart_data += "{{label: {0}, data: {1}}}".format(json.dumps(entry), "{0:.2f}".format(percentage))

                if sorted(authorinfo_list)[-1] != entry:
                    chart_data += ", "

            changes_xml += ("<tfoot><tr> <td colspan=\"5\">&nbsp;</td> </tr></tfoot></tbody></table>")
            changes_xml += "<div class=\"chart\" id=\"changes_chart\"></div></div>"
            changes_xml += "<script type=\"text/javascript\">"
            changes_xml += "    changes_plot = $.plot($(\"#changes_chart\"), [{0}], {{".format(chart_data)
            changes_xml += "        series: {"
            changes_xml += "            pie: {"
            changes_xml += "                innerRadius: 0.4,"
            changes_xml += "                show: true,"
            changes_xml += "                combine: {"
            changes_xml += "                    threshold: 0.01,"
            changes_xml += "                    label: \"" + _("Minor Authors") + "\""
            changes_xml += "                }"
            changes_xml += "            }"
            changes_xml += "        }, grid: {"
            changes_xml += "            hoverable: true"
            changes_xml += "        }"
            changes_xml += "    });"
            changes_xml += "</script>"
        else:
            changes_xml += "<p>" + _(NO_COMMITED_FILES_TEXT) + ".</p>"

        changes_xml += "</div></div>"
        print(changes_xml)

    def output_xml(self):
        authorinfo_list = self.changes.get_authorinfo_list()
        total_changes = 0.0

        for i in authorinfo_list:
            total_changes += authorinfo_list.get(i).insertions
            total_changes += authorinfo_list.get(i).deletions

        if authorinfo_list:
            message_xml = "\t\t<message>" + _(HISTORICAL_INFO_TEXT) + "</message>\n"
            changes_xml = ""

            for i in sorted(authorinfo_list):
                authorinfo = authorinfo_list.get(i)
                percentage = 0 if total_changes == 0 else (authorinfo.insertions + authorinfo.deletions) / total_changes * 100
                name_xml = "\t\t\t\t<name>" + i + "</name>\n"
                gravatar_xml = "\t\t\t\t<gravatar>" + gravatar.get_url(self.changes.get_latest_email_by_author(i)) + "</gravatar>\n"
                commits_xml = "\t\t\t\t<commits>" + str(authorinfo.commits) + "</commits>\n"
                insertions_xml = "\t\t\t\t<insertions>" + str(authorinfo.insertions) + "</insertions>\n"
                deletions_xml = "\t\t\t\t<deletions>" + str(authorinfo.deletions) + "</deletions>\n"
                percentage_xml = "\t\t\t\t<percentage-of-changes>" + "{0:.2f}".format(percentage) + "</percentage-of-changes>\n"

                changes_xml += ("\t\t\t<author>\n" + name_xml + gravatar_xml + commits_xml + insertions_xml +
                                deletions_xml + percentage_xml + "\t\t\t</author>\n")

            print("\t<changes>\n" + message_xml + "\t\t<authors>\n" + changes_xml + "\t\t</authors>\n\t</changes>")
        else:
            print("\t<changes>\n\t\t<exception>" + _(NO_COMMITED_FILES_TEXT) + "</exception>\n\t</changes>")
