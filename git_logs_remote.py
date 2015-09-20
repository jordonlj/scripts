#!/usr/bin/python

#git_logs.py fetch -u jason.liu@linaro.org -p <my password>
#git_logs.py analyze --since 20150818 --until 20150819
#PYTHONPATH=/srv/weblogs python git_logs.py analyze --since 20150818 --until 20150819

#scp git_logs.py jason.liu@weblogs.linaro.org:/srv/weblogs.linaro.org/restricted
#ssh -X jason.liu@weblogs.linaro.org

#http://stackoverflow.com/questions/3453188/matplotlib-display-plot-on-a-remote-machine


import argparse
import codecs
import gzip
import logging
import os
import re
import urllib2
from urllib2 import Request
import numpy as np
import matplotlib
matplotlib.use('GTKAgg')

import matplotlib.pyplot as plt
import IP2Location_cached

BASE_URL = 'https://weblogs.linaro.org'
GIT_SERVERS = ['git-ie.linaro.org', 'git-ap.linaro.org', 'git-us.linaro.org']

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

base = '(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<date>.*)\] '
GIT_PATTERNS = {
    #'check': re.compile(
    #    base + '"GET /(?P<repo>\S+)/info/refs\?service=git-upload-pack HTTP.+" 200'),
    'smart_update': re.compile(
        base + '"POST /(?P<repo>\S+)/git-upload-pack HTTP.+" 200'),
    # TODO dumb_update
}

IP2LOC_FILE = '/home/weblogs/db/ip2location/current_database/IP-COUNTRY-REGION-CITY-ISP.BIN'

dic_IP={}
dic_date={}
ipList=[]
keyList=[]
valueList=[]

def _weblogs_get(resource):
    return urllib2.urlopen(BASE_URL + resource)


def _download(url, path):
    resp = _weblogs_get(url)
    with open(path, 'wb') as f:
        f.write(resp.read())


def _dir_list(resource):
    resp = _weblogs_get(resource)
    pat = re.compile('.+<a href="(\S+)">')
    with codecs.getreader('utf-8')(resp) as f:
        for line in f:
            m = pat.match(line)
            if m:
                yield m.group(1)


def _sync_logs(gitserver, local_path):
    url = '/restricted/%s/' % gitserver
    log.info(' syncing logs for: %s', gitserver)
    for link in _dir_list(url):
        if '-access.log-201' in link:
            p = os.path.join(local_path, link)
            if os.path.exists(p):
                log.debug('file exists locally skipping: %s', link)
            else:
                log.info('downloading %s', link)
                _download(url + link, p)


def _fetch(args):
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, BASE_URL, args.user, args.password)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)

    for s in GIT_SERVERS:
        p = os.path.join(args.logs_dir, s)
        if not os.path.isdir(p):
            os.mkdir(p)
        _sync_logs(s, p)


def _git_hits(filename):
    with gzip.open(filename) as f:
        with codecs.getreader('utf-8')(f) as f:
            for entry in f:
                for method, pat in GIT_PATTERNS.items():
                    m = pat.match(entry)
                    if m:
                        yield method, m


def _analyze(args):
    for s in GIT_SERVERS:
        log.info('Analyzing logs since %s for %s', args.since, s)
        path = os.path.join(args.logs_dir, s)
        for logfile in os.listdir(path):
            if '-access.log-' not in logfile:
                # old stuff, skip
                continue
            date = logfile.rsplit('-')[-1].replace('.gz', '')
            if int(date) >= args.since and int(date) <= args.until:
                log.info('analyzing: %s', logfile)
                i = 0
                for method, match in _git_hits(os.path.join(path, logfile)):
                    if "landing-teams/working/arm" in match.group('repo'):
                        log.info('TODO %s: %s  %s %s', method, match.group('repo'), match.group('ip'), match.group('date'))
                        i = i+1
                        ipList.append(match.group('ip'))
                if dic_date.has_key(date) == False:
                    dic_date[date] = i
                else:
                    dic_date[date] = dic_date[date] + i


    ipl = IP2Location_cached.IP2Location(IP2LOC_FILE)
    IPlistSet = set(ipList)
    for item in IPlistSet:
        log.info('ip: %s(country=%s, region=%s, city=%s) ---- hits: %d', 
            item, 
            ipl.get_country_short(item), 
            ipl.get_region(item), 
            ipl.get_city(item), 
            ipList.count(item))
        dic_IP['country=' + ipl.get_country_short(item) + ', city=' + ipl.get_city(item)] = ipList.count(item)

    #IP-----------------------------------
    items = dic_IP.items()
    for (k,v) in items:
        log.info('analyzing IP: %s, hits: %d', k, v)
        keyList.append(k)
        valueList.append(v)

    n_groups = len(dic_IP)
    means_created = valueList
    index = np.arange(n_groups)
    opacity = 0.6

    rects = plt.bar(index, means_created, 1, alpha=opacity, color='b',label='Clone & Fetch Activities by Geographic Location')

    ax = plt.gca()
    plt.xticks(index, keyList)
    labelsx = ax.get_xticklabels()
    plt.setp(labelsx, rotation=90, fontsize=10)

    plt.xlabel('September')
    plt.ylabel('hits')
    plt.title('LT git statistic')
    plt.ylim(0,400)
    plt.legend()
    plt.tight_layout()
    plt.show()          


def main(args):
    if getattr(args, 'func', None):
        args.func(args)


def get_args():
    parser = argparse.ArgumentParser('Build git usage stats')
    parser.add_argument('--logs-dir', default='./',
                        help='local copy of logs. default=%(default)s')

    sub = parser.add_subparsers(help='sub-command help')
    p = sub.add_parser('fetch', help='Fetch logs from weblogs')
    p.add_argument('-u', '--user', required=True, help='linaro email')
    p.add_argument('-p', '--password', required=True, help='ldap password')
    p.set_defaults(func=_fetch)

    p = sub.add_parser('analyze', help='Analyze metrics stored locally')
    p.add_argument('--since', type=int, required=True,
                   help='Only look at logs since given date. eg 20150818')
    p.add_argument('--until', type=int, required=True,
                   help='Only look at logs until given date. eg 20150818')
    p.set_defaults(func=_analyze)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main(get_args())
