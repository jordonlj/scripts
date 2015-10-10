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


# Connect to the server
server = 'https://cards.linaro.org'
username = 'jason.liu@linaro.org'
password = 'xxxx'
# To store the password, run this from an interactive python session
# import keyring; keyring.set_password(server, username, "mysecret")
# password = keyring.get_password(server, username)
jira = JIRA(options={'server': server}, basic_auth=(username, password))

since = '2015-08-31'
until = '2015-09-18'

def worklog(issues):
    sum_effort = 0
    for issue_id in issues:
        for logid in jira.worklogs(issue_id):
            time_spent = jira.worklog(issue_id, logid).timeSpent
            start_date = jira.worklog(issue_id, logid).started            
            start_date = start_date[:10]
            if int(start_date.replace('-', '')) >= int(since.replace('-', '')) and int(start_date.replace('-', '')) <= int(until.replace('-', '')):
                #report.print('work_timestamp:-------- %s' %(start_date))
                #report.print('               -------- %s' %(time_spent))
                for i in range(len(time_spent)):
                    if time_spent[i] == 'w':
                        sum_effort = sum_effort + int(time_spent[i-1])*5*8*60
                    if time_spent[i] == 'd':
                        sum_effort = sum_effort + int(time_spent[i-1])*8*60
                    if time_spent[i] == 'h':
                        sum_effort = sum_effort + int(time_spent[i-1])*60
                    if time_spent[i] == 'm':
                        sum_effort = sum_effort + int(time_spent[i-1])
    #report.print('sum-------- %d' %(sum_effort))
    return sum_effort
                        

# member---------------------------
query = 'project = PS AND component = Actions'
all = jira.search_issues(query)
report = Report(jira)
w_1 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of Actions:-------- %d' %(w_1))


# member---------------------------
query = 'project = PS AND component = Hisilicon'
all = jira.search_issues(query)
report = Report(jira)
w_2 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of Hisilicon:-------- %d' %(w_2))


# member---------------------------
query = 'project = PS AND component = Linaro'
all = jira.search_issues(query)
report = Report(jira)
w_3 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of Linaro:-------- %d' %(w_3))


# member---------------------------
query = 'project = PS AND component = MediaTek'
all = jira.search_issues(query)
report = Report(jira)
w_4 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of MediaTek:-------- %d' %(w_4))


# member---------------------------
query = 'project = PS AND component = Qualcomm'
all = jira.search_issues(query)
report = Report(jira)
w_5 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of Qualcomm:-------- %d' %(w_5))


# member---------------------------
query = 'project = PS AND component = Spreadtrum'
all = jira.search_issues(query)
report = Report(jira)
w_6 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of Spreadtrum:-------- %d' %(w_6))


# member---------------------------
query = 'project = PS AND component = TI'
all = jira.search_issues(query)
report = Report(jira)
w_7 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of TI:-------- %d' %(w_7))


# member---------------------------
query = 'project = PS AND component = ZTE'
all = jira.search_issues(query)
report = Report(jira)
w_8 = worklog(all)
report.print('[Jason] member******************************')
report.print('[Jason] sum of ZTE:-------- %d' %(w_8))


w = w_1+w_2+w_3+w_4+w_5+w_6+w_7+w_8
 
import numpy as np
import matplotlib.pyplot as plt

# The slices will be ordered and plotted counter-clockwise.
labels = 'Actions (%1.1f%%)' %(100*(w_1/float(w))), 'Hisilicon (%1.1f%%)' %(100*(w_2/float(w))), 'Linaro (%1.1f%%)' %(100*(w_3/float(w))), 'MediaTek (%1.1f%%)' %(100*(w_4/float(w))), 'Qualcomm (%1.1f%%)' %(100*(w_5/float(w))), 'Spreadtrum (%1.1f%%)' %(100*(w_6/float(w))), 'TI (%1.1f%%)' %(100*(w_7/float(w))), 'ZTE (%1.1f%%)' %(100*(w_8/float(w)))
sizes = [w_1, w_2, w_3, w_4, w_5, w_6, w_7, w_8]
colors = ['green', 'yellowgreen', 'gold', 'yellow', 'lightskyblue', 'blue', 'lightcoral', 'pink']

plt.pie(sizes, labels=labels, colors=colors, startangle=90)
plt.axis('equal')
plt.text(0.6, -1.2, 'Period: February-August 2015', color='black', fontsize=12, fontweight='bold')
plt.title('Linaro Premium Services: Work Summary By Member' + '\n' + '\n')

plt.show()