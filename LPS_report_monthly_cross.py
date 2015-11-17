#!/usr/bin/env python

#
# weekly-report
#
# Extract JIRA status to generate a template weekly report
#

#
# TODO: 
#
#  - Add command line processing (configurable time windows,
#    include URL in draft versions of reports to make it quicker
#    to update engineering status fields, restrict to single
#    engineer).
#
#  - Improve processing of idiomatic text from engineering status
#    field (more flexibility on numbers, stripping out of dates to
#    I don't have to manually reflow text).
#
#  - Bring the final loops into the report class.
#
#  - Include KWG cards assigned to me in the report.
#

from __future__ import print_function

import datetime
from jira.client import JIRA
import iso8601
import keyring
import re
import textwrap
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt

class UTC(datetime.tzinfo):
    ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
	return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO

utc = UTC()

#
# Collection of find/replace strings to massage a summary for
# readability.
#
# Ideally all we would do with hacks is strip our redundant idioms
# such as including the issuetype in the summary.
#
# However for now we go a bit deeper and try to remove other
# redundant information from the summary (such as member name) or
# excessive use of verbs.
#
hacks = (
	('CARD:', ''),
	('BLUEPRINT:', ''),
	('backport feature', 'backport'),
	('found in 3.18 LSK to the', 'to'),
	('Prepare presentation', 'Presentation'),
	('and its relationship to', 'and'),
	('for u-boot/linux for', 'for'),
	('Execute initial test plan ltp-ddt test cases to LAVA for BBB',
		'LTP-DDT: Initial LAVA integration (using BBB)'),
	('ZTE power management', 'Power management')
)

def warn(issue, msg):
	lines = textwrap.wrap('{} {}'.format(issue.url, msg),
			initial_indent=   'WARNING: ',
			subsequent_indent='         ')
	print('\n'.join(lines))

class Issue(object):
	re_ymd = re.compile('(20[0-9][0-9]).?([0-9][0-9]).?([0-9][0-9])')
	re_progress = re.compile('^(h[123456]\.|#+)?\s*[Pp]rogress')
	re_plans = re.compile('^(h[123456]\.|#+)?\s*[Pp]lans?')

	def __init__(self, issue, jira):
		self._raw = issue

		summary = issue.fields.summary
		for (old, new) in hacks:
			summary = summary.replace(old, new)
		self.summary = summary.strip()

		if issue.fields.assignee:
			self.assignees = set((issue.fields.assignee.displayName,))
		else:
			self.assignees = set(("Noone",))
		self.fields = issue.fields
		self.engineering_status = issue.fields.customfield_10204
		self.key = issue.key
		if self.is_blueprint():
			self.parent = issue.fields.customfield_10301
		self.url = 'https://cards.linaro.org/browse/' + issue.key

		self._get_comments(jira)
		self._get_worklog(jira)
	
	def _get_comments(self, jira):
		self.comments = []

		for id in jira.comments(self.key):
			self.comments.append(jira.comment(self.key, id))

		# Interpret paragraphs
		for comment in self.comments:
			comment.comment = []
			for ln in comment.body.replace('\r', '').split('\n\n'):
				comment.comment.append(
						ln.replace('\n', ' ').strip())

	def _get_worklog(self, jira):
		self.worklog = []

		for id in jira.worklogs(self.key):
			self.worklog.append(jira.worklog(self.key, id))

		# Parse into progress and plans
		for log in self.worklog:
			log.progress = []
			log.plans = []
			active = log.progress

			for ln in log.comment.replace('\r', '').split('\n\n'):
				ln = ln.replace('\n', ' ').strip()
				if re.match(self.re_progress, ln):
					continue
				if re.match(self.re_plans, ln):
					active = log.plans
					continue
				active.append(ln)

	def is_blueprint(self):
		return self.fields.issuetype.name == 'Blueprint'

	def is_card(self):
		return self.fields.issuetype.name == 'Engineering card'

	def categorize(self):
		lookup = {
			'Open': (),
			'TODO': ('Plan',),
			'In Progress' : ('Plan', 'Progress'),
			'Resolved' : ('Progress',),
			'Closed' : ('Progress',),
		}

		if self.fields.status.name in lookup:
			return set(lookup[self.fields.status.name])

		warn(self, 'has bad status ({})'.format(self.fields.status.name))
		return set()

	def fmt_assignees(self):
		msg = ""
		for a in sorted(self.assignees):
			msg += ", {}".format(a.partition(' ')[0])
		return msg.lstrip(', ')

	def _fmt_engineering_status(self, filt):
		es = self.engineering_status
		if es == None:
			return ()

		es = es.replace('\r', '')
		es = [ln.replace('plans: ', '').replace('Plans: ', '') for ln in es.split('\n') if filt(ln)]

		return es

	def fmt_engineering_status(self, max_age):
		def is_current(ln):
			if len(ln) == 0:
				return False

			match = re.search(self.re_ymd, ln)
			if match:
				try:
					tstamp = datetime.datetime(
							int(match.group(1)),
							int(match.group(2)),
							int(match.group(3)))
					age = tstamp.now() - tstamp
					if age.days > max_age:
						return False
					return True
				except ValueError:
					warn(self, 'contains bad date ({})'.format(
						match.group(0)))
		
			if ln.startswith("plan") or ln.startswith("Plan"):
				return False

			warn(self, 'has missing date in engineering status')
			return True

		return self._fmt_engineering_status(is_current)

	def fmt_engineering_plans(self):
		def is_plan(ln):
			return ln.startswith("plan") or ln.startswith("Plan")

		return self._fmt_engineering_status(is_plan)

	def fmt_summary(self, member):
		return '{}: {} [{}] ({})'.format(member, self.summary, 
				self.fmt_assignees(), self.key)

	def fmt_comments(self, jira, age=None, recurse=False):
		comments = list(self.comments)
		if recurse and self.is_card():
			for bp in self.blueprints:
				comments += bp.comments

		# Filter by date if requested
		if age:
			now = datetime.datetime.utcnow().replace(tzinfo=utc)
			threshold = now - age
			comments = [g for g in comments
				if iso8601.parse_date(g.updated) > threshold]

		# Return comments in time sorted order
		return sorted(comments, key=lambda g: g.updated)

	def fmt_worklog(self, jira, age=None, recurse=False):
		logs = list(self.worklog)
		if recurse and self.is_card():
			for bp in self.blueprints:
				logs += bp.worklog

		# Filter by date if requested
		if age:
			now = datetime.datetime.utcnow().replace(tzinfo=utc)
			threshold = now - age
			logs = [g for g in logs
				if iso8601.parse_date(g.started) > threshold]

		# Return work log in time sorted order
		return sorted(logs, key=lambda g: g.started)

class Report(object):
	wrappers = (
		textwrap.TextWrapper(),
		textwrap.TextWrapper(initial_indent=' * ', subsequent_indent='   '),
		textwrap.TextWrapper(initial_indent='   - ', subsequent_indent='     ')
	)

	def __init__(self, jira):
		self.jira = jira
		self.issues = {}
		self.cards = {}
		self.blueprints = {}
		self.members = {}

	def add(self, raw):
		issue = Issue(raw, jira)
		self.issues[issue.key] = issue

		if issue.is_blueprint():
			self.blueprints[issue.key] = issue
		elif issue.is_card():
			self.cards[issue.key] = issue

			if len(issue.fields.components) == 0:
				warn(issue, 'has no component')
			for m in issue.fields.components:
				if m.name not in self.members:
					self.members[m.name] = []
				self.members[m.name].append(issue)
			issue.blueprints = []
		else:
			warn(self, 'has unexpected issuetype {}'.format(
				self.fields.issuetype.name))
	
	def link_blueprints(self):
		'''Iterate over the blueprints and link them to their cards.'''
		for b in self.blueprints.itervalues():
			if b.parent == None:
				warn(b, 'is not linked to an EPIC')
				continue
			elif b.parent not in report.cards:
				warn(b, 'is linked to non-existant {}'.format(b.parent))
				continue
	
			card = report.cards[b.parent]
			card.assignees |= b.assignees
			card.blueprints.append(b)
	
	@staticmethod
	def print(msg, level=0):
		print('\n'.join(Report.wrappers[level].wrap(msg)))


#PARAMETERS------------------------------------------------
dict_old = {"2015-02-01":"2015-02-28", "2015-03-01":"2015-03-31", "2015-04-01":"2015-04-30", "2015-05-01":"2015-05-31", "2015-06-01":"2015-06-30", "2015-07-01":"2015-07-31", "2015-08-01":"2015-08-31", "2015-09-01":"2015-09-30"}
dict = {"2015-10-01":"2015-10-31"}
ticks = ('February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October')

#DO NOT CHANGE-------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()
l_closed=[]
l_created=[]
l_active=[]

def calculateCardsStatus_old(dict, jira):
    items = dict.items() 
    items.sort()
    for (k,v) in items:
        log.info('analyzing start_date: %s, end_date: %s', k, v)
        start_date = k
        end_date = v
        # Collect the closed tasks
        query = 'project = PS AND status in (Resolved, Closed) AND resolutiondate >= ' + start_date + ' AND resolutiondate <= ' + end_date
        all = jira.search_issues(query)
        report = Report(jira)
        m_closed = len(all)
        report.print('[Jason] month******************************')
        report.print('[Jason] sum of closed:-------- %d' %(m_closed))
        # Collect the created tasks
        query = 'project = PS AND created >= ' + start_date + ' AND created <= ' + end_date
        all = jira.search_issues(query)
        report = Report(jira)
        m_created = len(all)
        report.print('[Jason] sum of created:-------- %d' %(m_created))
        # Collect the active tasks
        query = '(project = PS AND status in (Open, "In Progress", Reopened, TODO) AND created >= 2015-01-01 AND created <= ' + end_date + ') OR (project = PS AND status in (Closed, Resolved) AND created >= 2015-01-01 AND created <= ' + end_date + ' AND resolutiondate >=' + end_date + ')'
        all = jira.search_issues(query)
        report = Report(jira)
        m_active = len(all)
        report.print('[Jason] sum of active:-------- %d' %(m_active))
        l_closed.append(m_closed)
        l_created.append(m_created)
        l_active.append(m_active)

def calculateCardsStatus(dict, jira):
    items = dict.items() 
    items.sort()
    for (k,v) in items:
        log.info('analyzing start_date: %s, end_date: %s', k, v)
        start_date = k
        end_date = v
        # Collect the closed tasks
        query = 'project = PSE AND status in (Resolved, Closed) AND resolved >= ' + start_date + ' AND resolved <= ' + end_date
        all = jira.search_issues(query)
        report = Report(jira)
        m_closed = len(all)
        report.print('[Jason] month******************************')
        report.print('[Jason] sum of closed:-------- %d' %(m_closed))
        # Collect the created tasks
        query = 'project = PSE AND created >= ' + start_date + ' AND created <= ' + end_date
        all = jira.search_issues(query)
        report = Report(jira)
        m_created = len(all)
        report.print('[Jason] sum of created:-------- %d' %(m_created))
        # Collect the active tasks
        query = '(project = PSE AND status in (Open, "In Progress", Reopened, "To Do", Blocked) AND created >= 2015-01-01 AND created <= ' + end_date + ') OR (project = PSE AND status in (Closed, Resolved) AND created >= 2015-01-01 AND created <= ' + end_date + ' AND resolved > ' + end_date + ')'
        all = jira.search_issues(query)
        report = Report(jira)
        m_active = len(all)
        report.print('[Jason] sum of active:-------- %d' %(m_active))
        l_closed.append(m_closed)
        l_created.append(m_created)
        l_active.append(m_active)

# Connect to the server
username = 'jason.liu@linaro.org'
password = 'xxxx'
server_old = 'https://cards.linaro.org'
server = 'https://projects.linaro.org'
jira_old = JIRA(options={'server': server_old}, basic_auth=(username, password))
jira = JIRA(options={'server': server}, basic_auth=(username, password))

calculateCardsStatus_old(dict_old, jira_old)
calculateCardsStatus(dict, jira)

n_groups = len(dict_old) + len(dict)
means_created = l_created
means_closed = l_closed
means_active = l_active

fig, ax = plt.subplots()
index = np.arange(n_groups)
bar_width = 0.25
opacity = 0.4

plt.plot(index + bar_width, means_active, color='b', linestyle='--', marker='o', label='Work to be completed')
rects1 = plt.bar(index, means_created, bar_width,alpha=opacity, color='b',label='New work')
rects2 = plt.bar(index + bar_width, means_closed, bar_width,alpha=opacity,color='r',label='Completed work')

plt.xlabel('Time')
plt.ylabel('Work (Cards & Blueprints)')
#plt.title('Premium Services Engineering: Work Summary')
plt.grid(zorder=0)
plt.xticks(index + bar_width, ticks)
plt.ylim(0,40)
plt.legend()
 
plt.tight_layout()
plt.show()
