# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2003, 2004 Edgewall Software
# Copyright (C) 2003, 2004 Jonas Borgstr�m <jonas@edgewall.com>
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

import time

import perm
import util
from Module import Module
from Wiki import wiki_to_oneliner

import svn

class Log (Module):
    template_name = 'log.cs'
    template_rss_name = 'log_rss.cs'

    def log_receiver (self, changed_paths, rev, author, date, log, pool):
        if not changed_paths: return

        # Store the copyfrom-information so we can follow the file/dir
        # through tags/banches/copy/renames.
        for newpath in changed_paths.keys():
            change = changed_paths[newpath]
            if change.copyfrom_path:
                self.branch_info.setdefault(rev, []).append((change.copyfrom_path, newpath))

        shortlog = util.shorten_line(util.wiki_escape_newline(log))
        t = svn.util.svn_time_from_cstring(date, pool) / 1000000
        gmt = time.gmtime(t)
        item = {
            'rev'      : rev,
            'author'   : author and util.escape(author) or 'None',
            'date'     : util.svn_date_to_string (date, pool),
            'gmt'      : time.strftime('%a, %d %b %Y %H:%M:%S GMT', gmt),
            'log.raw'  : util.escape(log),
            'log'      : wiki_to_oneliner(util.shorten_line(util.wiki_escape_newline(log)), self.req.hdf, self.env,self.db),
            'shortlog' : util.escape(shortlog),
            'file_href': self.env.href.browser(self.path, rev),
            'changeset_href': self.env.href.changeset(rev)
            }
        self.log_info.insert (0, item)

    def get_info (self, path, rev):
        self.log_info = []
        self.branch_info = {}
        # We need to really make sure it's an ordinary string. The FieldStorage
        # class provided by modpython might give us some strange string-like object
        # that svn doesn't like.
        path = str(path)
        svn.repos.svn_repos_get_logs (self.repos, [path],
                                   0, rev, 1, 0, self.log_receiver,
                                   self.pool)
        # Loop through all revisions and update the path
        # after each tag/branch/copy/rename.
        path = self.path
        for item in self.log_info:
            item['file_href'] = self.env.href.browser(path, item['rev'])
            if self.branch_info.has_key(item['rev']):
                for info in self.branch_info[item['rev']]:
                    if path[:len(info[1])] == info[1]:
                        rel_path = path[len(info[1]):]
                        path = info[0]+rel_path
        return self.log_info

    def generate_path_links(self, rev, rev_specified):
        list = self.path.split('/')
        path = '/'
        self.req.hdf.setValue('log.filename', list[-1])
        self.req.hdf.setValue('log.href' , self.env.href.log(self.path))
        self.req.hdf.setValue('log.path.0', 'root')
        if rev_specified:
            self.req.hdf.setValue('log.path.0.url' ,
                                  self.env.href.browser(path, rev))
        else:
            self.req.hdf.setValue('log.path.0.url' , self.env.href.browser(path))
        i = 0
        for part in list[:-1]:
            i = i + 1
            if part == '':
                continue
            path = path + part + '/'
            self.req.hdf.setValue('log.path.%d' % i, part)

            url = ''
            if rev_specified:
                url = self.env.href.browser(path, rev)
            else:
                url = self.env.href.browser(path)
            self.req.hdf.setValue('log.path.%d.url' % i, url)
            if i == len(list) - 1:
                self.add_link('up', url, 'Parent directory')

    def render (self):
        self.perm.assert_permission (perm.LOG_VIEW)

        self.add_link('alternate', '?format=rss', 'RSS Feed',
            'application/rss+xml', 'rss')

        self.path = self.args.get('path', '/')
        if self.args.has_key('rev'):
            try:
                rev = int(self.args.get('rev'))
                rev_specified = 1
            except ValueError:
                rev = svn.fs.youngest_rev(self.fs_ptr, self.pool)
                rev_specified = 0
        else:
            rev = svn.fs.youngest_rev(self.fs_ptr, self.pool)
            rev_specified = 0

        try:
            root = svn.fs.revision_root(self.fs_ptr, rev, self.pool)
        except svn.core.SubversionException:
            raise util.TracError('Invalid revision number: %d' % rev)
        
        # We display an error message if the file doesn't exist (any more).
        # All we know is that the path isn't valid in the youngest
        # revision of the repository. The file might have existed
        # before, but we don't know for sure...
        if not svn.fs.check_path(root, self.path, self.pool) in \
               [svn.core.svn_node_file, svn.core.svn_node_dir]:
            raise util.TracError('The file or directory "%s" doesn\'t exist in the '
                                 'repository at revision %d.' % (self.path, rev),
                                 'Nonexistent path')
        else:
            info = self.get_info (self.path, rev)
            util.add_dictlist_to_hdf(info, self.req.hdf, 'log.items')

        self.generate_path_links(rev, rev_specified)
        self.req.hdf.setValue('title', self.path + ' (log)')
        self.req.hdf.setValue('log.path', self.path)

    def display_rss(self):
        self.req.display(self.template_rss_name, 'application/rss+xml')
