#!/usr/bin/env python

from __future__ import print_function

import datetime
from jira.client import JIRA
import iso8601
import keyring
import re
import textwrap
import sys
import numpy as np
import matplotlib.pyplot as plt

# Connect to the server
server = 'https://projects.linaro.org'
username = 'jason.liu@linaro.org'
password = 'xxxx'
jira = JIRA(options={'server': server}, basic_auth=(username, password))

since = '2015-08-01'
until = '2016-04-06'

def worklog(issues):
    sum_effort = 0
    for issue_id in issues:
        # calculate the worklog of the linked cards which is out of PSE domain
        links = jira.issue(issue_id).fields.issuelinks
        if len(links) != 0:
            for link in links:
                if hasattr(link, 'outwardIssue'):
                    rel = link.outwardIssue.key
                else:
                    rel = link.inwardIssue.key
                print('xxxxxxxxxxxxxxx:-------- %s' %(rel))
                for logid in jira.worklogs(rel):
                    time_spent = jira.worklog(rel, logid).timeSpent
                    start_date = jira.worklog(rel, logid).started            
                    start_date = start_date[:10]
                    if int(start_date.replace('-', '')) >= int(since.replace('-', '')) and int(start_date.replace('-', '')) <= int(until.replace('-', '')):
                        #print('work_timestamp:-------- %s' %(start_date))
                        #print('               -------- %s' %(time_spent))
                        for i in range(len(time_spent)):
                            if time_spent[i] == 'w':
                                sum_effort = sum_effort + int(time_spent[i-1])*5*8*60
                            if time_spent[i] == 'd':
                                sum_effort = sum_effort + int(time_spent[i-1])*8*60
                            if time_spent[i] == 'h':
                                sum_effort = sum_effort + int(time_spent[i-1])*60
                            if time_spent[i] == 'm':
                                sum_effort = sum_effort + int(time_spent[i-1])
        else:
            # calculate the worklog of PSE domain cards
            for logid in jira.worklogs(issue_id):
                time_spent = jira.worklog(issue_id, logid).timeSpent
                start_date = jira.worklog(issue_id, logid).started            
                start_date = start_date[:10]
                if int(start_date.replace('-', '')) >= int(since.replace('-', '')) and int(start_date.replace('-', '')) <= int(until.replace('-', '')):
                    #print('work_timestamp:-------- %s' %(start_date))
                    #print('               -------- %s' %(time_spent))
                    for i in range(len(time_spent)):
                        if time_spent[i] == 'w':
                            sum_effort = sum_effort + int(time_spent[i-1])*5*8*60
                        if time_spent[i] == 'd':
                            sum_effort = sum_effort + int(time_spent[i-1])*8*60
                        if time_spent[i] == 'h':
                            sum_effort = sum_effort + int(time_spent[i-1])*60
                        if time_spent[i] == 'm':
                            sum_effort = sum_effort + int(time_spent[i-1])
    
    #print('sum-------- %d' %(sum_effort))
    return sum_effort
  
labels=[]
sizes=[]
colors=[]
wl=[]
# member---------------------------
query = 'project = PSE AND component = "Member Build"'
all = jira.search_issues(query)
w_1 = worklog(all)
wl.append(w_1)
print('[Jason] member******************************')
print('[Jason] sum of Member Build:-------- %d' %(w_1))


# member---------------------------
query = 'project = PSE AND component = 96Boards'
all = jira.search_issues(query)
w_2 = worklog(all)
wl.append(w_2)
print('[Jason] member******************************')
print('[Jason] sum of 96Boards:-------- %d' %(w_2))


# member---------------------------
query = 'project = PSE AND component = "Engineering works"'
all = jira.search_issues(query)
w_3 = worklog(all)
wl.append(w_3)
print('[Jason] member******************************')
print('[Jason] sum of Engineering works:-------- %d' %(w_3))


# member---------------------------
query = 'project = PSE AND component = LAVA'
all = jira.search_issues(query)
w_4 = worklog(all)
wl.append(w_4)
print('[Jason] member******************************')
print('[Jason] sum of LAVA:-------- %d' %(w_4))


# member---------------------------
query = 'project = PSE AND component = Training'
all = jira.search_issues(query)
w_5 = worklog(all)
wl.append(w_5)
print('[Jason] member******************************')
print('[Jason] sum of Training:-------- %d' %(w_5))


# member---------------------------
query = 'project = PSE AND component = "BSP Analysis"'
all = jira.search_issues(query)
w_6 = worklog(all)
wl.append(w_6)
print('[Jason] member******************************')
print('[Jason] sum of BSP Analysis:-------- %d' %(w_6))


# member---------------------------
query = 'project = PSE AND component = "Upstream Consultancy"'
all = jira.search_issues(query)
w_7 = worklog(all)
wl.append(w_7)
print('[Jason] member******************************')
print('[Jason] sum of Upstream Consultancy:-------- %d' %(w_7))


w = w_1+w_2+w_3+w_4+w_5+w_6+w_7
wl.sort(reverse = True)

flag1, flag2, flag3, flag4, flag5, flag6, flag7 = 0,0,0,0,0,0,0
for i in range(len(wl)):
    if wl[i] == w_1 and wl[i]!= 0 and flag1 == 0:
        labels.append('Member Build (%1.1f%%)' %(100*(w_1/float(w))))
        sizes.append(w_1)
        colors.append('green')
        flag1 = 1
    if wl[i] == w_2 and wl[i]!= 0 and flag2 == 0:
        labels.append('96Boards (%1.1f%%)' %(100*(w_2/float(w))))
        sizes.append(w_2)
        colors.append('yellowgreen')
        flag2 = 1
    if wl[i] == w_3 and wl[i]!= 0 and flag3 == 0:
        labels.append('Uncategorized engineering work (%1.1f%%)' %(100*(w_3/float(w))))
        sizes.append(w_3)
        colors.append('gold')
        flag3 = 1
    if wl[i] == w_4 and wl[i]!= 0 and flag4 == 0:
        labels.append('LAVA (%1.1f%%)' %(100*(w_4/float(w))))
        sizes.append(w_4)
        colors.append('lightskyblue')
        flag4 = 1
    if wl[i] == w_5 and wl[i]!= 0 and flag5 == 0:
        labels.append('Training (%1.1f%%)' %(100*(w_5/float(w))))
        sizes.append(w_5)
        colors.append('lightcoral')
        flag5 = 1
    if wl[i] == w_6 and wl[i]!= 0 and flag6 == 0:
        labels.append('BSP Analysis (%1.1f%%)' %(100*(w_6/float(w))))
        sizes.append(w_6)
        colors.append('lightgreen')
        flag6 = 1
    if wl[i] == w_7 and wl[i]!= 0 and flag7 == 0:
        labels.append('Upstream Consultancy (%1.1f%%)' %(100*(w_7/float(w))))
        sizes.append(w_7)
        colors.append('pink')
        flag7 = 1

# The slices will be ordered and plotted counter-clockwise.
patches, texts = plt.pie(sizes, colors=colors, startangle=90)
plt.legend(patches, labels, loc="best")
#leg = plt.gca().get_legend()
#ltext  = leg.get_texts()
#plt.setp(ltext, fontsize='small')

plt.axis('equal')
plt.text(0.6, -1.2, 'Period: Aug 2015 - Mar 2016', color='black', fontsize=14)#, fontweight='bold')
#plt.title('Premium Services: Work Summary By Service Type' + '\n' + '\n')

plt.show()
