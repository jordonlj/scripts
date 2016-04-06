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
query = 'project = PSE AND component = Actions'
all = jira.search_issues(query)
w_1 = worklog(all)
wl.append(w_1)
print('[Jason] member******************************')
print('[Jason] sum of Actions:-------- %d' %(w_1))


# member---------------------------
query = 'project = PSE AND component = Hisilicon'
all = jira.search_issues(query)
w_2 = worklog(all)
wl.append(w_2)
print('[Jason] member******************************')
print('[Jason] sum of Hisilicon:-------- %d' %(w_2))


# member---------------------------
query = 'project = PSE AND component = Linaro'
all = jira.search_issues(query)
w_3 = worklog(all)
wl.append(w_3)
print('[Jason] member******************************')
print('[Jason] sum of Linaro:-------- %d' %(w_3))


# member---------------------------
query = 'project = PSE AND component = MediaTek'
all = jira.search_issues(query)
w_4 = worklog(all)
wl.append(w_4)
print('[Jason] member******************************')
print('[Jason] sum of MediaTek:-------- %d' %(w_4))


# member---------------------------
query = 'project = PSE AND component = Qualcomm'
all = jira.search_issues(query)
w_5 = worklog(all)
wl.append(w_5)
print('[Jason] member******************************')
print('[Jason] sum of Qualcomm:-------- %d' %(w_5))


# member---------------------------
query = 'project = PSE AND component = Spreadtrum'
all = jira.search_issues(query)
w_6 = worklog(all)
wl.append(w_6)
print('[Jason] member******************************')
print('[Jason] sum of Spreadtrum:-------- %d' %(w_6))


# member---------------------------
query = 'project = PSE AND component = TI'
all = jira.search_issues(query)
w_7 = worklog(all)
wl.append(w_7)
print('[Jason] member******************************')
print('[Jason] sum of TI:-------- %d' %(w_7))


# member---------------------------
query = 'project = PSE AND component = ZTE'
all = jira.search_issues(query)
w_8 = worklog(all)
wl.append(w_8)
print('[Jason] member******************************')
print('[Jason] sum of ZTE:-------- %d' %(w_8))

# member---------------------------
query = 'project = PSE AND component = ST'
all = jira.search_issues(query)
w_9 = worklog(all)
wl.append(w_9)
print('[Jason] member******************************')
print('[Jason] sum of ST:-------- %d' %(w_9))

# member---------------------------
query = 'project = PSE AND component = ARM'
all = jira.search_issues(query)
w_10 = worklog(all)
wl.append(w_10)
print('[Jason] member******************************')
print('[Jason] sum of ARM:-------- %d' %(w_10))

# member---------------------------
query = 'project = PSE AND component = Socionext'
all = jira.search_issues(query)
w_11 = worklog(all)
wl.append(w_11)
print('[Jason] member******************************')
print('[Jason] sum of Socionext:-------- %d' %(w_11))

# member---------------------------
query = 'project = PSE AND component = Marvell'
all = jira.search_issues(query)
w_12 = worklog(all)
wl.append(w_12)
print('[Jason] member******************************')
print('[Jason] sum of Marvell:-------- %d' %(w_12))

w = w_1+w_2+w_3+w_4+w_5+w_6+w_7+w_8+w_9+w_10+w_11+w_12
wl.sort(reverse = True)


flag1, flag2, flag3, flag4, flag5, flag6, flag7, flag8, flag9, flag10, flag11, flag12 = 0,0,0,0,0,0,0,0,0,0,0,0
for i in range(len(wl)):
    if wl[i] == w_1 and wl[i]!= 0 and flag1 == 0:
        labels.append('Actions (%1.1f%%)' %(100*(w_1/float(w))))
        sizes.append(w_1)
        colors.append('green')
        flag1 = 1
    if wl[i] == w_2 and wl[i]!= 0 and flag2 == 0:
        labels.append('Hisilicon (%1.1f%%)' %(100*(w_2/float(w))))
        sizes.append(w_2)
        colors.append('yellowgreen')
        flag2 = 1
    if wl[i] == w_3 and wl[i]!= 0 and flag3 == 0:
        labels.append('Linaro (%1.1f%%)' %(100*(w_3/float(w))))
        sizes.append(w_3)
        colors.append('gold')
        flag3 = 1
    if wl[i] == w_4 and wl[i]!= 0 and flag4 == 0:
        labels.append('MediaTek (%1.1f%%)' %(100*(w_4/float(w))))
        sizes.append(w_4)
        colors.append('yellow')
        flag4 = 1
    if wl[i] == w_5 and wl[i]!= 0 and flag5 == 0:
        labels.append('Qualcomm (%1.1f%%)' %(100*(w_5/float(w))))
        sizes.append(w_5)
        colors.append('lightskyblue')
        flag5 = 1
    if wl[i] == w_6 and wl[i]!= 0 and flag6 == 0:
        labels.append('Spreadtrum (%1.1f%%)' %(100*(w_6/float(w))))
        sizes.append(w_6)
        colors.append('blue')
        flag6 = 1
    if wl[i] == w_7 and wl[i]!= 0 and flag7 == 0:
        labels.append('TI (%1.1f%%)' %(100*(w_7/float(w))))
        sizes.append(w_7)
        colors.append('lightcoral')
        flag7 = 1
    if wl[i] == w_8 and wl[i]!= 0 and flag8 == 0:
        labels.append('ZTE (%1.1f%%)' %(100*(w_8/float(w))))
        sizes.append(w_8)
        colors.append('pink')
        flag8 = 1
    if wl[i] == w_9 and wl[i]!= 0 and flag9 == 0:
        labels.append('ST (%1.1f%%)' %(100*(w_9/float(w))))
        sizes.append(w_9)
        colors.append('red')
        flag9 = 1
    if wl[i] == w_10 and wl[i]!= 0 and flag10 == 0:
        labels.append('ARM (%1.1f%%)' %(100*(w_10/float(w))))
        sizes.append(w_10)
        colors.append('cyan')
        flag10 = 1
    if wl[i] == w_11 and wl[i]!= 0 and flag11 == 0:
        labels.append('Socionext (%1.1f%%)' %(100*(w_11/float(w))))
        sizes.append(w_11)
        colors.append('magenta')
        flag11 = 1
    if wl[i] == w_12 and wl[i]!= 0 and flag12 == 0:
        labels.append('Marvell (%1.1f%%)' %(100*(w_12/float(w))))
        sizes.append(w_12)
        colors.append('lightgreen')
        flag12 = 1


# The slices will be ordered and plotted counter-clockwise.
patches, texts = plt.pie(sizes, colors=colors, startangle=90)
plt.legend(patches, labels, loc="best")
#leg = plt.gca().get_legend()
#ltext  = leg.get_texts()
#plt.setp(ltext, fontsize='small')

plt.axis('equal')
plt.text(0.6, -1.2, 'Period: Aug 2015 - Mar 2016', color='black', fontsize=14)#, fontweight='bold')
#plt.title('Premium Services: Work Summary By Member' + '\n' + '\n')

plt.show()
