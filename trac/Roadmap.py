# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2004-2005 Edgewall Software
# Copyright (C) 2004-2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.com/license.html.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://projects.edgewall.com/trac/.
#
# Author: Christopher Lenz <cmlenz@gmx.de>

from __future__ import generators
import re
from time import localtime, strftime, time

from trac import __version__
from trac.core import *
from trac.Milestone import Milestone, calc_ticket_stats, get_query_links, \
                           get_tickets_for_milestone, milestone_to_hdf
from trac.perm import IPermissionRequestor
from trac.util import enum, escape, pretty_timedelta, CRLF
from trac.ticket import Ticket
from trac.web import IRequestHandler
from trac.web.chrome import add_link, add_stylesheet, INavigationContributor


class RoadmapModule(Component):

    implements(INavigationContributor, IPermissionRequestor, IRequestHandler)

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'roadmap'

    def get_navigation_items(self, req):
        if not req.perm.has_permission('ROADMAP_VIEW'):
            return
        yield 'mainnav', 'roadmap', '<a href="%s" accesskey="3">Roadmap</a>' \
                                    % self.env.href.roadmap()

    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['ROADMAP_VIEW']

    # IRequestHandler methods

    def match_request(self, req):
        return re.match(r'/roadmap/?', req.path_info) is not None

    def process_request(self, req):
        req.perm.assert_permission('ROADMAP_VIEW')
        req.hdf['title'] = 'Roadmap'

        showall = req.args.get('show') == 'all'
        req.hdf['roadmap.showall'] = showall

        db = self.env.get_db_cnx()
        milestones = []
        for idx, milestone in enum(Milestone.select(self.env, showall)):
            hdf = milestone_to_hdf(self.env, db, req, milestone)
            milestones.append(hdf)
        req.hdf['roadmap.milestones'] = milestones

        for idx,milestone in enum(milestones):
            prefix = 'roadmap.milestones.%d.' % idx
            tickets = get_tickets_for_milestone(self.env, db, milestone['name'],
                                                'owner')
            req.hdf[prefix + 'stats'] = calc_ticket_stats(tickets)
            for k, v in get_query_links(self.env, milestone['name']).items():
                req.hdf[prefix + 'queries.' + k] = escape(v)
            milestone['tickets'] = tickets # for the iCalendar view

        if req.args.get('format') == 'ics':
            self.render_ics(req, db, milestones)
            return

        add_stylesheet(req, 'common/css/roadmap.css')

        # FIXME should use the 'webcal:' scheme, probably
        username = None
        if req.authname and req.authname != 'anonymous':
            username = req.authname
        icshref = self.env.href.roadmap(show=req.args.get('show'),
                                        user=username, format='ics')
        add_link(req, 'alternate', icshref, 'iCalendar', 'text/calendar', 'ics')

        return 'roadmap.cs', None

    # Internal methods

    def render_ics(self, req, db, milestones):
        req.send_response(200)
        req.send_header('Content-Type', 'text/calendar;charset=utf-8')
        req.end_headers()

        from trac.ticket import Priority
        priorities = {}
        for priority in Priority.select(self.env):
            priorities[priority.name] = float(priority.value)
        def get_priority(ticket):
            value = priorities.get(ticket['priority'])
            if value:
                return int(value * 9 / len(priorities))

        def get_status(ticket):
            status = ticket['status']
            if status == 'new' or status == 'reopened' and not ticket['owner']:
                return 'NEEDS-ACTION'
            elif status == 'assigned' or status == 'reopened':
                return 'IN-PROCESS'
            elif status == 'closed':
                if ticket['resolution'] == 'fixed': return 'COMPLETED'
                else: return 'CANCELLED'
            else: return ''

        def write_prop(name, value, params={}):
            text = ';'.join([name] + [k + '=' + v for k, v in params.items()]) \
                 + ':' + '\\n'.join(re.split(r'[\r\n]+', value))
            firstline = 1
            while text:
                if not firstline: text = ' ' + text
                else: firstline = 0
                req.write(text[:75] + CRLF)
                text = text[75:]

        def write_date(name, value, params={}):
            params['VALUE'] = 'DATE'
            write_prop(name, strftime('%Y%m%d', value), params)

        def write_utctime(name, value, params={}):
            write_prop(name, strftime('%Y%m%dT%H%M%SZ', value), params)

        host = req.base_url[req.base_url.find('://') + 3:]
        user = req.args.get('user', 'anonymous')

        write_prop('BEGIN', 'VCALENDAR')
        write_prop('VERSION', '2.0')
        write_prop('PRODID', '-//Edgewall Software//NONSGML Trac %s//EN'
                   % __version__)
        write_prop('X-WR-CALNAME',
                   self.config.get('project', 'name') + ' - Roadmap')
        for milestone in milestones:
            uid = '<%s/milestone/%s@%s>' % (req.cgi_location,
                                            milestone['name'], host)
            if milestone.has_key('due'):
                write_prop('BEGIN', 'VEVENT')
                write_prop('UID', uid)
                write_date('DTSTART', localtime(milestone['due']))
                write_prop('SUMMARY', 'Milestone %s' % milestone['name'])
                write_prop('URL', req.base_url + '/milestone/' +
                           milestone['name'])
                if milestone.has_key('description_source'):
                    write_prop('DESCRIPTION', milestone['description_source'])
                write_prop('END', 'VEVENT')
            for tkt_id in [ticket['id'] for ticket in milestone['tickets']
                           if ticket['owner'] == user]:
                ticket = Ticket(self.env, tkt_id)
                write_prop('BEGIN', 'VTODO')
                if milestone.has_key('date'):
                    write_prop('RELATED-TO', uid)
                    write_date('DUE', localtime(milestone['due']))
                write_prop('SUMMARY', 'Ticket #%i: %s' % (ticket.id,
                                                          ticket['summary']))
                write_prop('URL', self.env.abs_href.ticket(ticket.id))
                write_prop('DESCRIPTION', ticket['description'])
                priority = get_priority(ticket)
                if priority:
                    write_prop('PRIORITY', str(priority))
                write_prop('STATUS', get_status(ticket))
                if ticket['status'] == 'closed':
                    cursor = db.cursor()
                    cursor.execute("SELECT time FROM ticket_change "
                                   "WHERE ticket=%s AND field='status' "
                                   "ORDER BY time desc LIMIT 1",
                                   (ticket.id,))
                    row = cursor.fetchone()
                    if row:
                        write_utctime('COMPLETED', localtime(row[0]))
                write_prop('END', 'VTODO')
        write_prop('END', 'VCALENDAR')
