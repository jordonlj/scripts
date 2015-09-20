from __future__ import print_function

import datetime
from jira.client import JIRA
import iso8601
import keyring
import re
import textwrap
import sys
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator, SecondLocator
import numpy as np
from StringIO import StringIO
import datetime as dt

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
password = 'xxxxx'
# To store the password, run this from an interactive python session
# import keyring; keyring.set_password(server, username, "mysecret")
# password = keyring.get_password(server, username)
jira = JIRA(options={'server': server}, basic_auth=(username, password))

# member---------------------------
query = 'project = PS AND issuetype = "Engineering card"'
all = jira.search_issues(query)
report = Report(jira)

w = len(all)
a=StringIO()
now = datetime.datetime.now()
today = now.strftime("%Y-%m-%d")
ok = ''

report.print('[Jason] member******************************')
report.print('[Jason] sum of Actions:-------- %d' %(w))
for id in all:
    created_date = jira.issue(id).fields.created
    created_date = created_date[:10]
    resolved_date = jira.issue(id).fields.resolutiondate
    if resolved_date == None:
        resolved_date = today
        ok = 'NOT_OK'
    else:
        resolved_date = resolved_date[:10]
        ok = 'OK'

    report.print('input-------- %s' %(id.key + ' ' + created_date + ' ' + resolved_date + ' ' + ok + '\n'))
    a.writelines(id.key + ' ' + created_date + ' ' + resolved_date + ' ' + ok + '\n')
a.seek(0)

#Converts str into a datetime object.
conv = lambda s: dt.datetime.strptime(s, '%Y-%m-%d')

#Use numpy to read the data in. 
data = np.genfromtxt(a, converters={1: conv, 2: conv},
                     names=['caption', 'start', 'stop', 'state'], dtype=None)
cap, start, stop = data['caption'], data['start'], data['stop']

#Check the status, because we paint all lines with the same color 
#together
is_ok = (data['state'] == 'OK')
not_ok = np.logical_not(is_ok)

#Get unique captions and there indices and the inverse mapping
captions, unique_idx, caption_inv = np.unique(cap, 1, 1)

#Build y values from the number of unique captions.
y = (caption_inv + 1) / float(len(captions) + 2)

#Plot function
def timelines(y, xstart, xstop, color='b'):
    """Plot timelines at y from xstart to xstop with given color."""
    if color == 'blue':
        plt.hlines(y, xstart, xstop, color, lw=4, label="Closed & Resolved Cards")
        plt.vlines(xstart, y+0.015, y-0.015, color, lw=4)
        plt.vlines(xstop, y+0.015, y-0.015, color, lw=4)
    elif color == 'red':
        plt.hlines(y, xstart, xstop, color, lw=4, label="Active Cards")
        plt.vlines(xstart, y+0.015, y-0.015, color, lw=4)
        plt.vlines(xstop, y, y, color)

#Plot ok tl black    
timelines(y[is_ok], start[is_ok], stop[is_ok], 'blue')
#Plot fail tl red
timelines(y[not_ok], start[not_ok], stop[not_ok], 'red')

#Setup the plot
ax = plt.gca()
ax.xaxis_date()
myFmt = DateFormatter('%m-%d')
ax.xaxis.set_major_formatter(myFmt)
ax.xaxis.set_major_locator(MinuteLocator(interval=1440*10)) # 1440min = 1day
labelsx = ax.get_xticklabels()
plt.setp(labelsx, rotation=30, fontsize=12)

#To adjust the xlimits a timedelta is needed.
delta = (stop.max() - start.min())/10

plt.yticks(y[unique_idx], captions)
plt.ylim(0,1)
plt.xlim(start.min()-delta, stop.max()+delta)

plt.xlabel('Time')
plt.ylabel('Card ID')
plt.title('Linaro Premium Services: Card Timeline For Actions Semi')
plt.grid(zorder=0)
plt.legend(loc=2)
plt.show()
