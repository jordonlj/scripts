#!/usr/bin/env python

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

#PARAMETERS------------------------------------------------
dict_old = {"2015-02-01":"2015-03-01", "2015-03-01":"2015-04-01", "2015-04-01":"2015-05-01", "2015-05-01":"2015-06-01", "2015-06-01":"2015-07-01", "2015-07-01":"2015-08-01", "2015-08-01":"2015-09-01", "2015-09-01":"2015-10-01"}
dict = {"2015-10-01":"2015-11-01", "2015-11-01":"2015-12-01", "2015-12-01":"2016-01-07", "2016-01-07":"2016-02-01", "2016-02-01":"2016-03-03", "2016-03-03":"2016-04-06"}
ticks = ('Feb-15', 'Mar-15', 'Apr-15', 'May-15', 'Jun-15', 'Jul-15', 'Aug-15', 'Sep-15', 'Oct-15', "Nov-15", "Dec-15", "Jan-16", "Feb-16", "Mar-16")

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
        query = 'project = PS AND status in (Resolved, Closed) AND resolutiondate >= ' + start_date + ' AND resolutiondate < ' + end_date
        all = jira.search_issues(query)
        m_closed = len(all)
        print('[Jason] month******************************')
        print('[Jason] sum of closed:-------- %d' %(m_closed))
        # Collect the created tasks
        query = 'project = PS AND created >= ' + start_date + ' AND created < ' + end_date
        all = jira.search_issues(query)
        m_created = len(all)
        print('[Jason] sum of created:-------- %d' %(m_created))
        # Collect the active tasks
        query = '(project = PS AND status in (Open, "In Progress", Reopened, TODO) AND created >= 2015-01-01 AND created < ' + end_date + ') OR (project = PS AND status in (Closed, Resolved) AND created >= 2015-01-01 AND created < ' + end_date + ' AND resolutiondate >= ' + end_date + ')'
        all = jira.search_issues(query)
        m_active = len(all)
        print('[Jason] sum of active:-------- %d' %(m_active))
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
        query = 'project = PSE AND status in (Resolved, Closed) AND resolved >= ' + start_date + ' AND resolved < ' + end_date
        all = jira.search_issues(query)
        m_closed = len(all)
        print('[Jason] month******************************')
        print('[Jason] sum of closed:-------- %d' %(m_closed))
        # Collect the created tasks
        query = 'project = PSE AND created >= ' + start_date + ' AND created < ' + end_date
        all = jira.search_issues(query)
        m_created = len(all)
        print('[Jason] sum of created:-------- %d' %(m_created))
        # Collect the active tasks
        query = '(project = PSE AND status in (Open, "In Progress", Reopened, "To Do", Blocked) AND created >= 2015-01-01 AND created < ' + end_date + ') OR (project = PSE AND status in (Closed, Resolved) AND created >= 2015-01-01 AND created < ' + end_date + ' AND resolved >= ' + end_date + ')'
        all = jira.search_issues(query)
        m_active = len(all)
        print('[Jason] sum of active:-------- %d' %(m_active))
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
