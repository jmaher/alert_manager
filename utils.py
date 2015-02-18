from lib.decorators import database_conn, memoize
from db import *
import settings
import requests, re
import logging
from managed_settings import TBPL_TESTS, HOST_ALERT_MANAGER
import datetime

WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',  'Friday', 'Saturday', 'Sunday']
logger = None

def get_revision_range(dzdata, revision):
    # TODO: switch this to hg instead of datazilla (jmaher)
    for item in dzdata:
        if revision in dzdata[item]['revisions']:
            revid = int(item)
            break
    else:
        if logger:
            logger.info('Unable to find revision: %s' % revision)
        return

    lower = str(revid - 6)
    upper = str(revid + 6)

    if lower not in dzdata:
        if logger:
            logger.info('Unable to get range, missing id: %s' % lower)
        return
    if upper not in dzdata:
        if logger:
            logger.info('Unable to get range, missing id: %s' % upper)
        return

    return dzdata[lower]['revisions'][-1], dzdata[upper]['revisions'][-1]

@memoize
def get_datazilla_data(branch_id):
    """Returns data retrieved from datazilla.

    Data is cached in memory to avoid redundant
    requests to datazilla or producing temp files on disk.
    """
    url = settings.DATAZILLA_URL_TEMPLATE % {'branch': branch_id, 'days': 21}
    return requests.get(url).json()


def build_tbpl_link(record):
    # TODO: is branch valid?
    tbpl_branch = record.branch.split('-Non-PGO')[0]
    if tbpl_branch == 'Firefox':
        treeherder_repo = 'mozilla-central'
    else:
        treeherder_repo = tbpl_branch.lower()

    dzdata = get_datazilla_data(tbpl_branch)
    vals = get_revision_range(dzdata, record.keyrevision)

    link = ''
    if vals:
        params = []

        tbpl_platform = settings.TBPL_PLATFORMS[record.platform]
        tbpl_test = settings.TBPL_TESTS[record.test]['jobname']
        tbpl_tree = settings.TBPL_TREES[record.branch]

        if 'OSX' in tbpl_platform:
            tbpl_tree = tbpl_tree.split(' pgo')[0]

        params.append(('repo', treeherder_repo))
        params.append(('fromchange', vals[0]))
        params.append(('tochange', vals[1]))
        params.append(('filter-searchStr', '%s %s talos %s' % (tbpl_platform, tbpl_tree, tbpl_test)))
        link = settings.TREEHERDER_URL
        delim = '?'
        for key, value in params:
            link = "%s%s%s=%s" % (link, delim, key, value)
            if delim == '?':
                delim = '&'
        link = link.replace(' ', '%20')

    return link

def get_details_from_id(alert_id):
    '''
    Returns a dictionary with keys test, branch, platform, keyrevision
    '''
    db = create_db_connnection()
    cursor = db.cursor()
    retVal = {}
    sql = "select test, branch, platform, keyrevision, tbplurl from alerts where id=%s;" %(alert_id,)
    cursor.execute(sql)
    search_results = cursor.fetchall()
    search_results = search_results[0]
    
    retVal['test'] = search_results[0]
    retVal['branch'] = search_results[1]
    retVal['platform'] = search_results[2]
    retVal['keyrevision'] = search_results[3]
    retVal['tbplurl'] = search_results[4]    
    cursor.close()
    db.close()

    return retVal

def parse_details_to_file_bug(details, oldest_alert, bugnum='BUGNUM'):
    branch = details['branch']
    test = details['test']
    platform = details['platform']
    percent = details['percent']
    push_date = details['push_date']
    summary = ''

    #add regression values
    min_percent = min(percent)
    max_percent = max(percent)
    min_percent = re.findall('(?P<number>\d+)', min_percent)[0]
    max_percent = re.findall('(?P<number>\d+)', max_percent)[0]
    if int(max_percent) - int(min_percent) <= 1:
        summary = summary + '%s' %(max_percent) + '% '
    else:
        summary = summary + '%s-%s' %(min_percent, max_percent) + '% '

    #add platform
    flags = {
        'linux64': 0,
        'linux32': 0,
        'Win8 x64': 0,
        'WinXP x32': 0,
        'Win7 x32': 0,
        'Android': 0,
        'MacOS': 0
    }
    for p in platform:
        if 'Ubuntu HW 12.04 x64' in p:
            flags['linux64'] = 1
        elif 'Ubuntu HW 12.04' in p:
            flags['linux32'] = 1
        elif 'WINNT 6.2 x64' in p:
            flags['Win8 x64'] = 1
        elif 'WINNT 5.1 (ix)' in p:
            flags['WinXP x32'] = 1
        elif 'WINNT 6.1 (ix)' in p:
            flags['Win7 x32'] = 1
        elif 'Mac' in p:
            flags['MacOS'] = 1
        elif 'Android' in p:
            flags['Android'] = 1
    add = ''
    try_platform = ''
    if flags['linux64'] and flags['linux32']:
        add = add + 'Linux*/'
        try_platform = 'linux,'
    elif flags['linux64']:
        add = add + 'Linux 64/'
        try_platform = try_platform + 'linux64,'
    elif flags['linux32']:
        try_platform = try_platform + 'linux,'
        add = add + 'Linux 32/'
    if  (flags['Win8 x64'] and flags['WinXP x32']) or (flags['Win8 x64'] and flags['Win7 x32']):
        try_platform = try_platform + 'win64,win32,'
        add = add + 'Win*/'
    elif flags['Win8 x64']:
        try_platform = try_platform + 'win64,'
        add = add + 'Win8/'
    elif flags['WinXP x32']:
        try_platform = try_platform + 'win32,'
        add = add + 'WinXP/'
    elif flags['Win7 x32']:
        try_platform = try_platform + 'win32,'
        add = add + 'Win7/'
    if flags['MacOS']:
        try_platform = try_platform + 'macosx64,'
        add = add + 'MacOS*/'
    if flags['Android']:
        try_platform = try_platform + 'android-api-11,'
        add = add + 'Android/'

    try_platform = try_platform.strip(',')
    add = add.strip('/') + ' '
    summary = summary + add

    #add Test
    add = ''
    for t in sorted(set(test)):
        add = add + TBPL_TESTS[t]['testname'] + '/'
    add = add.strip('/') + ' '
    summary = summary + add
    summary = summary + 'regression on '
    #add branch
    add = oldest_alert[0] + ' '
    summary = summary + add + ' on '
    #add date
    summary = summary + oldest_alert[4].strftime("%B %d, %Y") + ' from push %s' % details['keyrev']

    day = datetime.datetime.now()
    n_days = 3
    due_date = (day + datetime.timedelta(days=n_days)).weekday()
    if day.weekday()>=2:
        due_date = 0

    duedate = WEEK[due_date]

    #Creating Description
    desc = """
Talos has detected a Firefox performance regression from your commit %s in bug %s.  We need you to address this regression.

This is a list of all known regressions and improvements related to your bug:
%s/alerts.html?rev=%s&showAll=1

On the page above you can see Talos alert for each affected platform as well as a link to a graph showing the history of scores for this test. There is also a link to a treeherder page showing the Talos jobs in a pushlog format.

To learn more about the regressing test, please see: https://wiki.mozilla.org/Buildbot/Talos/Tests#%s

Reproducing and debugging the regression:
If you would like to re-run this Talos test on a potential fix, use try with the following syntax:
try: -b o -p %s -u none -t %s  # add "mozharness: --spsProfile" to generate profile data

To run the test locally and do a more in-depth investigation, first set up a local Talos environment:
https://wiki.mozilla.org/Buildbot/Talos/Running#Running_locally_-_Source_Code

Then run the following command from the directory where you set up Talos:
talos --develop -e <path>/firefox -a %s

Making a decision:
As the patch author we need your feedback to help us handle this regression.
*** Please let us know your plans by %s, or the offending patch will be backed out! ***

Our wiki page oulines the common responses and expectations:
https://wiki.mozilla.org/Buildbot/Talos/RegressionBugsHandling
            """ %(details['keyrev'], bugnum,
                  HOST_ALERT_MANAGER, details['keyrev'],
                  TBPL_TESTS[oldest_alert[1]]['wikiname'],
                  try_platform, TBPL_TESTS[oldest_alert[1]]['jobname'],
                  TBPL_TESTS[oldest_alert[1]]['testname'], duedate)

    return ({'summary':summary,'desc':desc})

def find_bugnum_from_body(keyrev):
    db = create_db_connnection()
    cursor = db.cursor()
    query = "select id,body from alerts  where keyrevision = '%s'" % keyrev
    cursor.execute(query)
    search_results = cursor.fetchall()
    bugs=set(re.findall(r'- [Bb]ug ([0-9]+)', str(search_results)))
    logging.debug(sorted(bugs))
    cursor.close()
    db.close()

    return list(bugs)

