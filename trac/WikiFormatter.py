 # -*- coding: iso8859-1 -*-
#
# Copyright (C) 2003, 2004, 2005 Edgewall Software
# Copyright (C) 2003, 2004, 2005 Jonas Borgstr�m <jonas@edgewall.com>
#
# Trac is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Trac is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Jonas Borgstr�m <jonas@edgewall.com>

import re
import os
import imp
import string
import StringIO
import urllib

import util
import Mimeview

__all__ = ['Formatter', 'OneLinerFormatter', 'wiki_to_html', 'wiki_to_oneliner']


def system_message(msg, text):
    return """<div class="system-message">
 <strong>%s</strong>
 <pre>%s</pre>
</div>
""" % (msg, util.escape(text))


class WikiProcessor:

    mime_type = ""

    def __init__(self, env, name):
        self.env = env
        self.name = name
        self.error = self.set_code_processor(name)
    
    def default_processor(hdf, text, env):
        return '<pre class="wiki">' + util.escape(text) + '</pre>\n'
    
    def html_processor(hdf, text, env):
        if Formatter._htmlproc_disallow_rule.search(text):
            err = system_message('Error: HTML block contains disallowed tags.', text)
            env.log.error(err)
            return err
        if Formatter._htmlproc_disallow_attribute.search(text):
            err = system_message('Error: HTML block contains disallowed attributes.', text)
            env.log.error(err)
            return err
        return text

    def mime_processor(self, hdf, text, env):
        return env.mimeview.display(text, self.mime_type)
    
    builtin_processors = { 'html': html_processor,
                           'default': default_processor}

    def process(self, hdf, text, inline=False):
        if self.error:
            return system_message('Error: Failed to load processor <code>%s</code>' % self.name, self.error)
        text = self.code_processor(hdf, text, self.env)
        if inline:
            code_block_start = re.compile('^<div class="code-block">')
            code_block_end = re.compile('</div>$')
            text, nr = code_block_start.subn('<span class="code-block">', text, 1 )
            if nr:
                text, nr = code_block_end.subn('</span>', text, 1 )
            return text
        else:
            return text
    

    def set_code_processor(self, name):
        if  self.builtin_processors.has_key(name):
            self.code_processor = self.builtin_processors[name]
        else:
            try:
                self.code_processor = self.load_macro(name)
            except Exception, e:
                if Mimeview.MIME_MAP.has_key(name):
                    name = Mimeview.MIME_MAP[name]
                mimeviewer, exists = self.env.mimeview.get_viewer(name)
                if exists != -1:
                    self.mime_type = name
                    self.code_processor = self.mime_processor
                else:
                    self.code_processor = self.builtin_processors['default']
                    return e
        return 0
    
    def load_macro(self, name):
        # Look in envdir/wiki-macros/ first
        try:
            module = imp.load_source(name, os.path.join(self.env.path, 'wiki-macros', name+'.py'))
        except IOError:
            # fall back to site-wide macros
            macros = util.safe__import__('wikimacros.' + name)
            module = getattr(macros, name)
        return module.execute


class CommonFormatter:
    """This class contains the patterns common to both Formatter and
    OneLinerFormatter"""

    _rules = [r"(?P<bold>''')",
              r"(?P<italic>'')",
              r"(?P<underline>__)",
              r"(?P<strike>~~)",
              r"(?P<subscript>,,)",
              r"(?P<superscript>\^)",
              r"(?P<inlinecode>!?\{\{\{(?P<inline>.*?)\}\}\})",
              r"(?P<htmlescapeentity>!?&#\d+;)",
              r"(?P<tickethref>!?#\d+)",
              r"(?P<changesethref>!?(\[\d+\]|\br\d+\b))",
              r"(?P<reporthref>!?\{\d+\})",
              r"(?P<modulehref>!?((?P<modulename>bug|ticket|browser|source|repos|report|query|changeset|wiki|milestone|search):(?P<moduleargs>(&#34;(.*?)&#34;|'(.*?)')|([^ ]*[^'~_\., \)]))))",
              r"(?P<wikihref>!?(^|(?<=[^A-Za-z]))[A-Z][a-z]+(?:[A-Z][a-z]*[a-z/])+(?:#[A-Za-z0-9]+)?(?=\Z|\s|[.,;:!?\)}\]]))",
              r"(?P<fancylink>!?\[(?P<fancyurl>([a-z]+:[^ ]+)) (?P<linkname>.*?)\])"]

    _open_tags = []
    env = None
    absurls = 0

    def __init__(self, env, db, absurls=0):
        self.env = env
        self.db = db
        self._href = absurls and env.abs_href or env.href
        self._local = env.config.get('project', 'url', '') or env.abs_href.base

    def replace(self, fullmatch):
        for itype, match in fullmatch.groupdict().items():
            if match and not itype in Formatter._helper_patterns:
                # Check for preceding escape character '!'
                if match[0] == '!':
                    return match[1:]
                return getattr(self, '_' + itype + '_formatter')(match, fullmatch)

    def tag_open_p(self, tag):
        """Do we currently have any open tag with @tag as end-tag"""
        return tag in self._open_tags

    def close_tag(self, tag):
        tmp = s = ''
        while self._open_tags != [] and tag != tmp:
            tmp = self._open_tags.pop()
            s += tmp
        return s

    def open_tag(self, tag):
        self._open_tags.append(tag)

    def simple_tag_handler(self, open_tag, close_tag):
        """Generic handler for simple binary style tags"""
        if self.tag_open_p(close_tag):
            return self.close_tag(close_tag)
        else:
            self.open_tag(close_tag)
            return open_tag

    def _bold_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<strong>', '</strong>')

    def _italic_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<i>', '</i>')

    def _underline_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<span class="underline">', '</span>')

    def _strike_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<del>', '</del>')

    def _subscript_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<sub>', '</sub>')

    def _superscript_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<sup>', '</sup>')

    def _inlinecode_formatter(self, match, fullmatch):
        return '<tt>%s</tt>' % fullmatch.group('inline')

    def _htmlescapeentity_formatter(self, match, fullmatch):
        #dummy function that match html escape entities in the format:
        # &#[0-9]+;
        # This function is used to avoid these being matched by
        # the tickethref regexp
        return match

    def _tickethref_formatter(self, match, fullmatch):
        return self._make_ticket_link(match[1:], match)

    def _changesethref_formatter(self, match, fullmatch):
        if match[0] == 'r':
            rev = match[1:]
        else:
            rev = match[1:-1]
        return self._make_changeset_link(rev, match)

    def _reporthref_formatter(self, match, fullmatch):
        return self._make_report_link(match[1:-1], match)

    def _modulehref_formatter(self, match, fullmatch):
        return self._make_module_link(match, match)

    def _wikihref_formatter(self, match, fullmatch):
        return self._make_wiki_link(match, match)

    def _url_formatter(self, match, fullmatch):
        return self._make_ext_link(match, match)

    def _fancylink_formatter(self, match, fullmatch):
        link = fullmatch.group('fancyurl')
        text = fullmatch.group('linkname')
        return self._make_module_link(link, text)

    def _make_module_link(self, link, text):
        sep = link.find(':')
        if sep == -1:
            return None, None
        module = link[:sep]
        args = link[sep + 1:]
        make_link = getattr(self, '_make_' + module + '_link', None)
        if make_link:
            return make_link(args, text)
        else:
            return self._make_ext_link(link, text)

    def _make_ext_link(self, url, text):
        if not url.startswith(self._local):
            return '<a class="ext-link" href="%s">%s</a>' % (url, text)
        else:
            return '<a href="%s">%s</a>' % (url, text)

    def _make_wiki_link(self, page, text):
        anchor = ''
        if page.find('#') != -1:
            anchor = page[page.find('#'):]
            page = page[:page.find('#')]
        page = urllib.unquote(page)
        text = urllib.unquote(text)
        if not self.env._wiki_pages.has_key(page):
            return '<a class="missing wiki" href="%s" rel="nofollow">%s?</a>' \
                   % (self._href.wiki(page) + anchor, text)
        else:
            return '<a class="wiki" href="%s">%s</a>' \
                   % (self._href.wiki(page) + anchor, text)

    def _make_changeset_link(self, rev, text):
        cursor = self.db.cursor()
        cursor.execute('SELECT message FROM revision WHERE rev=%s', (rev,))
        row = cursor.fetchone()
        if row:
            return '<a class="changeset" title="%s" href="%s">%s</a>' \
                   % (util.escape(util.shorten_line(row[0])),
                      self._href.changeset(rev), text)
        else:
            return '<a class="missing changeset" href="%s" rel="nofollow">%s</a>' \
                   % (self._href.changeset(rev), text)

    def _make_ticket_link(self, id, text):
        cursor = self.db.cursor()
        cursor.execute("SELECT summary,status FROM ticket WHERE id=%s", (id,))
        row = cursor.fetchone()
        if row:
            summary = util.escape(util.shorten_line(row[0]))
            if row[1] in ('new', 'closed'):
                return '<a class="%s ticket" href="%s" title="%s (%s)">%s</a>' \
                       % (row[1], self._href.ticket(id), summary, row[1], text)
            else:
                return '<a class="ticket" href="%s" title="%s">%s</a>' \
                       % (self._href.ticket(id), summary, text)
        else:
            return '<a class="missing ticket" href="%s" rel="nofollow">%s</a>' \
                   % (self._href.ticket(id), text)
    _make_bug_link = _make_ticket_link # alias

    def _make_milestone_link(self, name, text):
        return '<a class="milestone" href="%s">%s</a>' \
               % (self._href.milestone(name), text)

    def _make_query_link(self, query, text):
        if query[0] == '?':
            return '<a class="query" href="%s">%s</a>' \
                   % (self.env.href.query() + query, text)
        else:
            from trac.Query import Query, QuerySyntaxError
            try:
                query = Query.from_string(self.env, query)
                return '<a class="query" href="%s">%s</a>' \
                       % (query.get_href(), text)
            except QuerySyntaxError, e:
                return '<em class="error">[Error: %s]</em>' % util.escape(e)

    def _make_report_link(self, id, text):
        return '<a class="report" href="%s">%s</a>' \
               % (self._href.report(id), text)

    def _make_search_link(self, query, text):
        return '<a class="search" href="%s">%s</a>' \
               % (self._href.search(query), text)

    def _make_source_link(self, path, text):
        rev = None
        match = re.search('([^#]+)#(.+)', path)
        if match:
            path = match.group(1)
            rev = match.group(2)
        text = urllib.unquote(text)
        path = urllib.unquote(path)
        if rev:
            return '<a class="source" href="%s">%s</a>' \
                   % (self._href.browser(path, rev=rev), text)
        else:
            return '<a class="source" href="%s">%s</a>' \
                   % (self._href.browser(path), text)
    _make_browser_link = _make_source_link # alias
    _make_repos_link = _make_source_link # alias


class OneLinerFormatter(CommonFormatter):
    """
    A special version of the wiki formatter that only implement a
    subset of the wiki formatting functions. This version is useful
    for rendering short wiki-formatted messages on a single line
    """

    _rules = CommonFormatter._rules + \
             [r"""(?P<url>([a-z]+://[^ ]+[^\., ]))"""]

    _compiled_rules = re.compile('(?:' + string.join(_rules, '|') + ')')

    def format(self, text, out):
        if not text:
            return
        self.out = out
        self._open_tags = []

        rules = self._compiled_rules

        result = re.sub(rules, self.replace, util.escape(text.strip()))
        # Close all open 'one line'-tags
        result += self.close_tag(None)
        out.write(result)


class Formatter(CommonFormatter):
    """
    A simple Wiki formatter
    """
    _rules = [r"""(?P<svnimg>(source|repos):([^ ]+)\.(PNG|png|JPG|jpg|JPEG|jpeg|GIF|gif))"""] + \
             CommonFormatter._rules + \
             [r"""(?P<macro>!?\[\[(?P<macroname>[\w/+-]+)(\]\]|\((?P<macroargs>.*?)\)\]\]))""",
              r"""(?P<heading>^\s*(?P<hdepth>=+)\s.*\s(?P=hdepth)\s*$)""",
              r"""(?P<list>^(?P<ldepth>\s+)(?:\*|[0-9]+\.) )""",
              r"""(?P<indent>^(?P<idepth>\s+)(?=\S))""",
              r"""(?P<imgurl>!?([a-z]+://[^ ]+)\.(PNG|png|JPG|jpg|JPEG|jpeg|GIF|gif)(\?\S+)?)""",
              r"""(?P<url>!?([a-z]+://[^ ]+[^\.,' \)\]\}]))""",
              r"""(?P<last_table_cell>\|\|$)""",
              r"""(?P<table_cell>\|\|)"""]

    _compiled_rules = re.compile('(?:' + string.join(_rules, '|') + ')')
    _processor_re = re.compile('#\!([\w+-][\w+-/]*)')
    _anchor_re = re.compile('[^\w\d\.-:]+', re.UNICODE)
    anchors = None

    hdf = None

    # RE patterns used by other patterna
    _helper_patterns = ('idepth', 'ldepth', 'hdepth', 'fancyurl',
                        'linkname', 'macroname', 'macroargs', 'inline',
                        'modulename', 'moduleargs')

    # Forbid "dangerous" HTML tags and attributes
    _htmlproc_disallow_rule = re.compile('(?i)<(script|noscript|embed|object|'
                                         'iframe|frame|frameset|link|style|'
                                         'meta|param|doctype)')
    _htmlproc_disallow_attribute = re.compile('(?i)<[^>]*\s+(on\w+)=')

    def __init__(self, hdf, env, db, absurls=0):
        CommonFormatter.__init__(self, env, db, absurls)
        self.hdf = hdf
        self.anchors = []

    def _macro_formatter(self, match, fullmatch):
        name = fullmatch.group('macroname')
        if name in ['br', 'BR']:
            return '<br />'
        args = fullmatch.group('macroargs')
        args = util.unescape(args)
        try:
            macro = WikiProcessor(self.env, name)
            return macro.process(self.hdf, args, 1)
        except Exception, e:
            return system_message('Error: Macro %s(%s) failed' % (name, args), e)

    def _heading_formatter(self, match, fullmatch):
        match = match.strip()
        self.close_table()
        self.close_paragraph()
        self.close_indentation()
        self.close_list()

        depth = min(len(fullmatch.group('hdepth')), 5)
        heading = match[depth + 1:len(match) - depth - 1]
        anchor = anchor_base = self._anchor_re.sub('', heading.decode('utf-8'))
        if not anchor or not anchor[0].isalpha():
            # an ID must start with a letter in HTML
            anchor = 'a' + anchor
        i = 1
        while anchor in self.anchors:
            anchor = anchor_base + str(i)
            i += 1
        self.anchors.append(anchor)
        self.out.write('<h%d id="%s">%s</h%d>' % (depth, anchor.encode('utf-8'),
                                                  heading, depth))

    def _svnimg_formatter(self, match, fullmatch):
        prefix_len = match.find(':') + 1
        return '<img src="%s" alt="%s" />' % \
               (self._href.file(match[prefix_len:], format='raw'),
                match[prefix_len:])

    def _imgurl_formatter(self, match, fullmatch):
        return '<img src="%s" alt="%s" />' % (match, match)

    def _indent_formatter(self, match, fullmatch):
        depth = int((len(fullmatch.group('idepth')) + 1) / 2)
        list_depth = len(self._list_stack)
        if list_depth > 0 and depth == list_depth + 1:
            self.in_list_item = 1
        else:
            self.open_indentation(depth)
        return ''

    def _last_table_cell_formatter(self, match, fullmatch):
        return ''

    def _table_cell_formatter(self, match, fullmatch):
        self.open_table()
        self.open_table_row()
        if self.in_table_cell:
            return '</td><td>'
        else:
            self.in_table_cell = 1
            return '<td>'

    def close_indentation(self):
        self.out.write(('</blockquote>' + os.linesep) * self.indent_level)
        self.indent_level = 0

    def open_indentation(self, depth):
        diff = depth - self.indent_level
        if diff != 0:
            self.close_paragraph()
            self.close_indentation()
            self.close_list()
            self.indent_level = depth
            self.out.write(('<blockquote>' + os.linesep) * depth)

    def _list_formatter(self, match, fullmatch):
        ldepth = len(fullmatch.group('ldepth'))
        depth = int((len(fullmatch.group('ldepth')) + 1) / 2)
        self.in_list_item = depth > 0
        type_ = ['ol', 'ul'][match[ldepth] == '*']
        self._set_list_depth(depth, type_)
        return ''

    def _set_list_depth(self, depth, type_):
        current_depth = len(self._list_stack)
        diff = depth - current_depth
        self.close_table()
        self.close_paragraph()
        self.close_indentation()
        if diff > 0:
            for i in range(diff):
                self._list_stack.append(type_)
                self.out.write('<%s><li>' % type_)
        elif diff < 0:
            for i in range(-diff):
                tmp = self._list_stack.pop()
                self.out.write('</li></%s>' % tmp)
            if self._list_stack != [] and type_ != self._list_stack[-1]:
                tmp = self._list_stack.pop()
                self._list_stack.append(type_)
                self.out.write('</li></%s><%s><li>' % (tmp, type_))
            if depth > 0:
                self.out.write('</li><li>')
        # diff == 0
        elif self._list_stack != [] and type_ != self._list_stack[-1]:
            tmp = self._list_stack.pop()
            self._list_stack.append(type_)
            self.out.write('</li></%s><%s><li>' % (tmp, type_))
        elif depth > 0:
            self.out.write('</li><li>')

    def close_list(self):
        if self._list_stack != []:
            self._set_list_depth(0, None)

    def open_paragraph(self):
        if not self.paragraph_open:
            self.out.write('<p>' + os.linesep)
            self.paragraph_open = 1

    def close_paragraph(self):
        if self.paragraph_open:
            self.out.write('</p>' + os.linesep)
            self.paragraph_open = 0

    def open_table(self):
        if not self.in_table:
            self.close_paragraph()
            self.close_indentation()
            self.close_list()
            self.in_table = 1
            self.out.write('<table class="wiki">' + os.linesep)

    def open_table_row(self):
        if not self.in_table_row:
            self.open_table()
            self.in_table_row = 1
            self.out.write('<tr>')

    def close_table_row(self):
        if self.in_table_row:
            self.in_table_row = 0
            if self.in_table_cell:
                self.in_table_cell = 0
                self.out.write('</td>')

            self.out.write('</tr>')

    def close_table(self):
        if self.in_table:
            self.close_table_row()
            self.out.write('</table>' + os.linesep)
            self.in_table = 0

    def handle_code_block(self, line):
        if line.strip() == '{{{':
            self.in_code_block += 1
            if self.in_code_block == 1:
                self.code_processor = None
                self.code_text = ''
            else:
                self.code_text += line + os.linesep
                if not self.code_processor:
                    self.code_processor = WikiProcessor(self.env, 'default')
        elif line.strip() == '}}}':
            self.in_code_block -= 1
            if self.in_code_block == 0 and self.code_processor:
                self.close_paragraph()
                self.close_table()
                self.out.write(self.code_processor.process(self.hdf, self.code_text))
            else:
                self.code_text += line + os.linesep
        elif not self.code_processor:
            match = Formatter._processor_re.search(line)
            if match:
                name = match.group(1)
                self.code_processor = WikiProcessor(self.env, name)
            else:
                self.code_text += line + os.linesep 
                self.code_processor = WikiProcessor(self.env, 'default')
        else:
            self.code_text += line + os.linesep

    def format(self, text, out):
        self.out = out
        self._open_tags = []
        self._list_stack = []

        self.in_code_block = 0
        self.in_table = 0
        self.in_table_row = 0
        self.in_table_cell = 0
        self.indent_level = 0
        self.paragraph_open = 0

        rules = self._compiled_rules

        for line in text.splitlines():
            # Handle code block
            if self.in_code_block or line.strip() == '{{{':
                self.handle_code_block(line)
                continue
            # Handle Horizontal ruler
            elif line[0:4] == '----':
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                self.close_table()
                self.out.write('<hr />' + os.linesep)
                continue
            # Handle new paragraph
            elif line == '':
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                continue

            line = util.escape(line)
            self.in_list_item = 0
            # Throw a bunch of regexps on the problem
            result = re.sub(rules, self.replace, line)
            # Close all open 'one line'-tags
            result += self.close_tag(None)

            if not self.in_list_item:
                self.close_list()

            if self.in_table and line[0:2] != '||':
                self.close_table()

            if len(result) and not self.in_list_item and not self.in_table:
                self.open_paragraph()
            out.write(result + os.linesep)
            self.close_table_row()

        self.close_table()
        self.close_paragraph()
        self.close_indentation()
        self.close_list()


def wiki_to_html(wikitext, hdf, env, db, absurls=0):
    out = StringIO.StringIO()
    Formatter(hdf, env, db, absurls).format(wikitext, out)
    return out.getvalue()


def wiki_to_oneliner(wikitext, env, db, absurls=0):
    out = StringIO.StringIO()
    OneLinerFormatter(env, db, absurls).format(wikitext, out)
    return out.getvalue()
