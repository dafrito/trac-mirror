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
import string
from types import *

from util import *
from Module import Module
import perm
from Wiki import wiki_to_html
from Notify import TicketNotifyEmail

fields = ['time', 'component', 'severity', 'priority', 'milestone', 'reporter',
          'owner', 'cc', 'url', 'version', 'status', 'resolution',
          'keywords', 'summary', 'description']

def get_ticket (db, id, escape_values=1):
    global fields
    cursor = db.cursor ()

    fetch = string.join(fields, ',')
    cursor.execute(('SELECT %s FROM ticket ' % fetch) + 'WHERE id=%s', id)
    row = cursor.fetchone ()
    cursor.close ()

    if not row:
        raise TracError('Ticket %d does not exist.' % id,
                        'Invalid Ticket Number')

    info = {'id': id }
    # Escape the values so that they are safe to have as html parameters
    for i in range(len(fields)):
        # We shouldn't escape the description
        # wiki_to_html will take care of that
        if fields[i] == 'description':
            info[fields[i]] = row[i] or ''
        elif escape_values:
            info[fields[i]] = escape(row[i])
        else:
            info[fields[i]] = row[i]
    return info


class Newticket (Module):
    template_name = 'newticket.cs'
    
    def create_ticket(self):
        """
        Insert a new ticket into the database.

        The values are taken from the html form
        """
        self.perm.assert_permission(perm.TICKET_CREATE)
        
        global fields
        data = {}
        for field in fields:
            if self.args.has_key(field):
                data[field] = self.args.get(field)
        now = int(time.time())
        data['time'] = now
        data['changetime'] = now
        data.setdefault('reporter',self.req.authname)

        cursor = self.db.cursor()

        # The owner field defaults to the component owner
        if data.has_key('component') and \
               (not data.has_key('owner') or data['owner'] == ''):
            # Assign it to the default owner
            cursor.execute('SELECT owner FROM component '
                           'WHERE name=%s', data['component'])
            owner = cursor.fetchone()[0]
            data['owner'] = owner
        
        nstr = string.join(data.keys(), ',')
        vstr = ('%s,' * len(data.keys()))[:-1]

        cursor.execute('INSERT INTO ticket (%s) VALUES(%s)' % (nstr, vstr),
                       *data.values())
        id = self.db.db.sqlite_last_insert_rowid()
        self.db.commit()

        # Notify
        tn = TicketNotifyEmail(self.env)
        tn.notify(id, newticket=1)
        
        # redirect to the Ticket module to get a GET request
        self.req.redirect(self.env.href.ticket(id))
        
    def render (self):
        if self.args.has_key('create'):
            self.create_ticket()
            
        default_component = self.env.get_config('ticket', 'default_component')
        default_milestone = self.env.get_config('ticket', 'default_milestone')
        default_priority  = self.env.get_config('ticket', 'default_priority')
        default_severity  = self.env.get_config('ticket', 'default_severity')
        default_version   = self.env.get_config('ticket', 'default_version')

        component = self.args.get('component', default_component)
        milestone = self.args.get('milestone', default_milestone)
        priority = self.args.get('priority', default_priority)
        severity = self.args.get('severity', default_severity)
        version = self.args.get('version', default_version)
        
        cc = self.args.get('cc', '')
        owner = self.args.get('owner', '')
        summary = self.args.get('summary', '')
        keywords = self.args.get('keywords', '')
        description = self.args.get('description', '')
        
        if description:
            self.req.hdf.setValue('newticket.description_preview',
                                  wiki_to_html(description, self.req.hdf, self.env))
        self.req.hdf.setValue('title', 'New Ticket')
        self.req.hdf.setValue('newticket.component', component)
        self.req.hdf.setValue('newticket.milestone', milestone)
        self.req.hdf.setValue('newticket.priority', priority)
        self.req.hdf.setValue('newticket.severity', severity)
        self.req.hdf.setValue('newticket.version', version)
        self.req.hdf.setValue('newticket.summary', escape(summary))
        self.req.hdf.setValue('newticket.description', escape(description))
        self.req.hdf.setValue('newticket.cc', escape(cc))
        self.req.hdf.setValue('newticket.owner', escape(owner))
        self.req.hdf.setValue('newticket.keywords', escape(keywords))
        
        sql_to_hdf(self.db, 'SELECT name FROM component ORDER BY name',
                   self.req.hdf, 'newticket.components')
        sql_to_hdf(self.db, 'SELECT name FROM milestone ORDER BY name',
                   self.req.hdf, 'newticket.milestones')
        sql_to_hdf(self.db, 'SELECT name FROM version ORDER BY name',
                   self.req.hdf, 'newticket.versions')
            

class Ticket (Module):
    template_name = 'ticket.cs'

    def get_ticket (self, id, escape_values=1):
        return get_ticket(self.db, id, escape_values)

    def save_changes (self, id, old, new): 
        global fields

        action = new.get('action', None)
        if action == 'accept':
            new['status'] = 'assigned'
            new['owner'] = self.req.authname
        if action == 'resolve':
            new['status'] = 'closed'
            new['resolution'] = new['resolve_resolution']
        elif action == 'reassign':
            new['owner'] = new['reassign_owner']
            new['status'] = 'assigned'
        elif action == 'reopen':
            new['status'] = 'reopened'
            new['resolution'] = ''
                
        changed = 0
        change = ''
        cursor = self.db.cursor()
        now = int(time.time())
        if new.has_key('reporter'):
            author = new['reporter']
            del new['reporter']
        else:
            author = self.req.authname
        for name in fields:
            # Make sure to only log changes of interest. For example
            # we consider field values of '' and NULL to be identical
            if new.has_key(name) and \
               ((not old[name] and new[name]) or \
                (old[name] and not new[name]) or \
                (old[name] and new[name] and old[name] != new[name])):

                cursor.execute ('INSERT INTO ticket_change '
                                '(ticket, time, author, field, oldvalue, newvalue) '
                                'VALUES (%s, %s, %s, %s, %s, %s)',
                                id, now, author, name, old[name], new[name])
                cursor.execute ('UPDATE ticket SET %s=%s WHERE id=%s',
                                name, new[name], id)
                changed = 1
        if new.has_key('comment') and len(new['comment']) > 0:
            cursor.execute ('INSERT INTO ticket_change '
                            '(ticket,time,author,field,oldvalue,newvalue) '
                            "VALUES (%s, %s, %s, 'comment', '', %s)",
                            id, now, author, new['comment'])
            changed = 1
        if changed:
            cursor.execute ('UPDATE ticket SET changetime=%s WHERE id=%s',
                            now, id)
            self.db.commit()

	tn = TicketNotifyEmail(self.env)
	tn.notify(id, newticket=0, modtime=now)

    def insert_ticket_data(self, hdf, id):
        """Inserts ticket data into the hdf"""
        cursor = self.db.cursor()
        cursor.execute('SELECT time, author, field, oldvalue, newvalue '
                       'FROM ticket_change '
                       'WHERE ticket=%s ORDER BY time', id)
        
        curr_author = None
        curr_date   = 0
        comment = None
        idx = 0
        while 1:
            row = cursor.fetchone()
            if row == None:
                break

            date   = int(row[0])
            author = row[1] or ''
            field  = row[2] or ''
            old    = row[3] or ''
            new    = row[4] or ''

            hdf.setValue('ticket.changes.%d.date' % idx,
                         time.strftime('%c', time.localtime(date)))
            hdf.setValue('ticket.changes.%d.time' % idx, str(date))
            hdf.setValue('ticket.changes.%d.author' % idx, author)
            hdf.setValue('ticket.changes.%d.field' % idx, field)
            hdf.setValue('ticket.changes.%d.old' % idx, old)
            if field == 'comment':
                hdf.setValue('ticket.changes.%d.new' % idx,
                             wiki_to_html(new, self.req.hdf, self.env))
            else:
                hdf.setValue('ticket.changes.%d.new' % idx, new)
            idx = idx + 1
            
        # List attached files
        self.env.get_attachments_hdf(self.db, 'ticket', str(id), self.req.hdf,
                                     'ticket.attachments')

    def render (self):
        action = self.args.get('action', 'view')
            
        if not self.args.has_key('id'):
            self.req.redirect(self.env.href.wiki())
            
        id = int(self.args.get('id'))

        if action in ['leave', 'accept', 'reopen', 'resolve', 'reassign']:
            # save changes and redirect to avoid the POST request
            self.perm.assert_permission (perm.TICKET_MODIFY)
            old = self.get_ticket(id, 0)
            new = {}
            for name in self.args.keys():
                new[name] = self.args[name].value
            self.save_changes (id, old, new)
            self.req.redirect(self.env.href.ticket(id))
        
        self.perm.assert_permission (perm.TICKET_VIEW)
        
        info = self.get_ticket(id)
        add_dict_to_hdf(info, self.req.hdf, 'ticket')
        
        sql_to_hdf(self.db, 'SELECT name FROM component ORDER BY name',
                   self.req.hdf, 'ticket.components')
        sql_to_hdf(self.db, 'SELECT name FROM milestone ORDER BY name',
                   self.req.hdf, 'ticket.milestones')
        sql_to_hdf(self.db, 'SELECT name FROM version ORDER BY name',
                   self.req.hdf, 'ticket.versions')
        hdf_add_if_missing(self.req.hdf, 'ticket.components', info['component'])
        hdf_add_if_missing(self.req.hdf, 'ticket.milestones', info['milestone'])
        hdf_add_if_missing(self.req.hdf, 'ticket.versions', info['version'])
        hdf_add_if_missing(self.req.hdf, 'enums.priority', info['priority'])
        hdf_add_if_missing(self.req.hdf, 'enums.severity', info['severity'])
        
        # Page title
        self.req.hdf.setValue('title', '#%d (ticket)' % id)
        self.insert_ticket_data(self.req.hdf, id)
        self.req.hdf.setValue('ticket.description',
                              wiki_to_html(info['description'], self.req.hdf,
                                           self.env))
        self.req.hdf.setValue('ticket.opened',
                              time.strftime('%c',
                                            time.localtime(int(info['time']))))
       
