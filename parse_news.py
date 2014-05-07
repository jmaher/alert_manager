import re
import sys
import string
import mailbox
import MySQLdb
import datetime
import rfc822
import urllib
import base64
import os
import ConfigParser
from optparse import OptionParser
import httplib
import json
import time

trees = ['Mozilla-Inbound', 
         'Mozilla-Inbound-Non-PGO', 
         'Fx-Team',
         'Fx-Team-Non-PGO',
         'Firefox',
         'Firefox-Non-PGO', 
         'Mozilla-Aurora',
         'Mozilla-Aurora-Non-PGO',
         'Mozilla-Beta',
         'Mozilla-Beta-Non-PGO',
         'B2g-Inbound',
         'B2g-Inbound-Non-PGO',
         'mobile']

platforms = ['XP', 'Win7', 'Ubuntu HW 12.04 x64', 'Ubuntu HW 12.04', 'Linux',
             'WINNT 5.2', 'WINNT 6.1 (ix)', 'WINNT 6.2 x64', 'WINNT 5.1 (ix)',
# jmaher: I don't care too much about centOS- that is builders
#             'CentOS release 5 (Final)', 'CentOS (x86_64) release 5 (Final)',
             'MacOSX 10.7', 'MacOSX 10.8', 'MacOSX 10.6 (rev4)', 
             'Android 2.2 (Native)', 'Android 4.0.4']

tbpl_platforms = {'WINNT 5.1 (ix)': 'Windows XP 32-bit',
                  'WINNT 5.2': '',
                  'WINNT 6.1 (ix)': 'Windows 7 32-bit',
                  'WINNT 6.2 x64': 'WINNT 6.2',
                  'Ubuntu HW 12.04': 'Ubuntu HW 12.04',
                  'Ubuntu HW 12.04 x64': 'Ubuntu HW 12.04 x64',
                  'MacOSX 10.6 (rev4)': 'Rev4 MacOSX Snow Leopard 10.6',
                  'MacOSX 10.8': 'Rev5 MacOSX Mountain Lion 10.8',
                  'Android 2.2 (Native)': 'Android 2.2 Tegra',
                  'Android 4.0.4': 'Android 4.0 Tegra'
                  }

# oh the hacks continue, osx runs on the pgo branch without the pgo tag
tbpl_trees = {'Mozilla-Inbound': 'mozilla-inbound pgo',
              'Mozilla-Inbound-Non-PGO': 'mozilla-inbound',
              'Fx-Team': 'fx-team pgo',
              'Fx-Team-Non-PGO': 'fx-team',
              'Firefox': 'mozilla-central pgo',
              'Firefox-Non-PGO': 'mozilla-central',
              'Mozilla-Aurora': 'mozilla-aurora pgo',
              'Mozilla-Aurora-Non-PGO': 'mozilla-aurora',
              'Mozilla-Beta': 'mozilla-beta pgo',
              'Mozilla-Beta-Non-PGO': 'mozilla-beta',
              'B2g-Inbound': 'b2g-inbound pgo',
              'B2g-Inbound-Non-PGO': 'b2g-inbound',
              'mobile': 'mozilla-central'
             }

tbpl_tests = {'SVG No Chrome': 'svgr',
        'SVG Row Major': 'svgr',
        'SVG, Opacity Row Major': 'svgr',
        'Dromaeo (DOM)': 'dromaeojs',
        'Dromaeo (CSS)': 'dromaeojs',
        'Kraken Benchmark': 'dromaeojs',
        'V8': 'dromaeojs',
        'V8 Version 7': 'dromaeojs',
        'V8 version 7': 'dromaeojs',
        'Paint': 'other',
        'tscroll Row Major': 'svgr',
        'TResize': 'chromez',
        'Tp5 Optimized': 'tp5o',
        'Tp5 Optimized (Private Bytes)': 'tp5o',
        'Tp5 Optimized (Main RSS)': 'tp5o',
        'Tp5 Optimized (Content RSS)': 'tp5o',
        'Tp5 Optimized (%CPU)': 'tp5o',
        'Tp5 No Network Row major MozAfterPaint (Main Startup File I/O Bytes)': 'tp5o',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Startup File IO Bytes)': 'tp5o',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Normal Network IO Bytes)': 'tp5o',
        'Tp5 No Network Row Major MozAfterPaint (Main Normal File IO Bytes)': 'tp5o',
        'Tp5 No Network Row Major MozAfterPaint (Main Startup File IO Bytes)': 'tp5o',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Normal File IO Bytes)': 'tp5o',
        'Tp5 Optimized (Modified Page List Bytes)': 'tp5o',
        'Tp5 Optimized Responsiveness': 'tp5o',
        'Tp5 Optimized MozAfterPaint': 'tp5o',
        'a11y Row Major MozAfterPaint': 'other',
        'Tp4 Mobile': 'remote-tp4m_nochrome',
        'LibXUL Memory during link': '',
        'Ts, Paint': 'other',
        'Robocop Pan Benchmark': 'remote-trobopan',
        'Robocop Database Benchmark': 'remote-troboprovider',
        'Robocop Checkerboarding No Snapshot Benchmark': 'remote-trobocheck2',
        'Robocop Checkerboarding Real User Benchmark': 'remote-trobocheck2',
        'Customization Animation Tests': 'svgr',
        'Latency Performance Tests': '',
        'WebRTC Media Performance Tests': '',
        'Tab Animation Test, NoChrome': 'svgr',
        'Tab Animation Test': 'svgr',
        'Canvasmark, NoChrome': 'chromez',
        'Canvasmark': 'chromez',
        'CanvasMark, NoChrome': 'chromez',
        'CanvasMark': 'chromez',
        'Tab Animation Test, NoChrome': 'svgr',
        'tscroll-ASAP': 'svgr',
        'SVG-ASAP, NoChrome': 'svgr',
        'SVG-ASAP': 'svgr',
        'tscroll-ASAP MozAfterPaint': 'svgr',
        'Session Restore no Auto Restore Test': 'other',
        'Session Restore Test': 'other'
             }

tests = ['SVG No Chrome',
        'SVG Row Major',
        'SVG, Opacity Row Major',
        'Dromaeo (DOM)',
        'Dromaeo (CSS)',
        'Kraken Benchmark',
        'V8',
        'V8 Version 7',
        'V8 version 7',
        'Paint',
        'tscroll Row Major',
        'TResize',
        'Tp5 Optimized',
        'Tp5 Optimized (Private Bytes)',
        'Tp5 Optimized (Main RSS)',
        'Tp5 Optimized (Content RSS)',
        'Tp5 Optimized (%CPU)',
        'Tp5 No Network Row major MozAfterPaint (Main Startup File I/O Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Startup File IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Normal Network IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Main Normal File IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Main Startup File IO Bytes)',
        'Tp5 Optimized (Modified Page List Bytes)',
        'Tp5 Optimized Responsiveness',
        'Tp5 Optimized MozAfterPaint',
        'a11y Row Major MozAfterPaint',
        'Tp4 Mobile',
        'LibXUL Memory during link',
        'Ts, Paint',
        'Robocop Pan Benchmark',
        'Robocop Database Benchmark',
        'Robocop Checkerboarding No Snapshot Benchmark',
        'Robocop Checkerboarding Real User Benchmark',
        'Customization Animation Tests',
        'Latency Performance Tests',
        'WebRTC Media Performance Tests',
        'Tab Animation Test, NoChrome',
        'Tab Animation Test',
        'Canvasmark, NoChrome',
        'Canvasmark',
        'CanvasMark, NoChrome',
        'CanvasMark',
        'Tab Animation Test, NoChrome',
        'tscroll-ASAP',
        'SVG-ASAP, NoChrome',
        'SVG-ASAP',
        'tscroll-ASAP MozAfterPaint' ]


def getDatazillaData(branchid):
    fname = "%s-%s.revs" % (branchid, int(time.time() / 1000))
    if os.path.exists(fname):
        data = '{}'
        with open(fname, 'r') as fhandle:
            data = fhandle.read()
    else:
    # https://datazilla.mozilla.org/refdata/pushlog/list/?days_ago=7&branches=Mozilla-Inbound
        conn = httplib.HTTPSConnection('datazilla.mozilla.org')
        cset = "/refdata/pushlog/list/?days_ago=30&branches=%s" % branchid
        conn.request("GET", cset)
        response = conn.getresponse()
        data = response.read()
        with open(fname, 'w+') as fhandle:
            fhandle.write(data)
    
    return json.loads(data)

def getRevisionRange(dzdata, revision):
    revid = None
    for item in dzdata:
        if revision in dzdata['%s' % item]['revisions']:
            revid = item
            break

    if not revid:
#        print "unable to find revision: %s" % revision
        return None
    low = '%s' % (int(revid) - 6)
    high = '%s' % (int(revid) + 6)
    if low not in dzdata:
        print "unable to get range, missing id: %s" % low
        return None
    if high not in dzdata:
        print "unable to get range, missing id: %s" % high
        return None

    return dzdata[low]['revisions'][-1], dzdata[high]['revisions'][-1]

#subject = "(Improvement) Firefox-Non-PGO - Customization Animation Tests - WINNT 6.2 x64 - 5.84%"
subre = re.compile("^(<Regression>|\(Improvement\))(.*)")


subject_trans_table = string.maketrans("\t", " ")

def getRevisions(changeseturl):
    cpart = changeseturl.split('?')[-1].replace('&', '_')

    if not os.path.exists(os.path.abspath('tmpcset')):
        os.mkdir('tmpcset')

    cacheFile = os.path.join(os.path.abspath('tmpcset'), cpart)
    if not os.path.exists(cacheFile):
        opener = urllib.FancyURLopener({})
        f = opener.open(changeseturl)
        data = f.read()
        f.close()
        with open(cacheFile, 'w+') as fHandle:
            fHandle.write(data)

    with open(cacheFile, 'r') as fHandle:
        data = fHandle.read()

    revisions = []
    #TODO: do we need to support other branches
    re_rev = re.compile(".*href=\"(\/integration)?\/(b2g-inbound|mozilla-central|mozilla-inbound|fx-team)\/rev\/([0-9a-f]+)\".*")
    for line in data.split('\n'):
        matches = re_rev.match(line)
        if matches:
            revisions.append(matches.group(3))

    return revisions

def getCSets(config):
    db = MySQLdb.connect(host=config['host'],
                         user=config['username'],
                         passwd=config['password'],
                         db=config['database'])

    #TODO: optimize to last 2 weeks of data
    sql = "select id, keyrevision, changesets from alerts";
    cur = db.cursor()
    cur.execute(sql)

    results = []
    for row in cur.fetchall():
        results.append([int(row[0]), row[1], row[2].split(',')])
    cur.close()

    return results

def addTbplURL(id, tbplurl):
    if tbplurl == '':
        return

    db = MySQLdb.connect(host=config['host'],
                         user=config['username'],
                         passwd=config['password'],
                         db=config['database'])

    sql = "select tbplurl from alerts where id=%s" % id
    cur = db.cursor()
    cur.execute(sql)

    results = []
    exists = False
    for row in cur.fetchall():
        if row[0]:
            if row[0] != '' and row[0] != 'NULL':
                exists = True
                break
    cur.close()

    if not exists:
        sql = "update alerts set tbplurl='%s' where id=%s" % (tbplurl, id)
        cur = db.cursor()
        cur.execute(sql)
        cur.close()


def markMerged(config, id, originalKeyRevision):
    db = MySQLdb.connect(host=config['host'],
                         user=config['username'],
                         passwd=config['password'],
                         db=config['database'])

    sql = "select mergedfrom from alerts where id=%s" % id
    cur = db.cursor()
    cur.execute(sql)

    results = []
    setAsMerged = False
    for row in cur.fetchall():
        if row[0]:
            if row[0] != '':
                setAsMerged = True
                break
    cur.close()

    if not setAsMerged:
        sql = "update alerts set mergedfrom='%s' where id=%s" % (originalKeyRevision, id)
        cur = db.cursor()
        cur.execute(sql)
        cur.close()

def subject_of(msg):
    global subject_trans_table
    subject = msg.get('Subject')
    if subject is None:
        return subject
    return subject.translate(subject_trans_table, "\n")

def validSubject(subject):
    global trees, platforms, tests, subre
    match = subre.match(subject)
    if not match:
        return [None, None, None, None]

    if match.group(1) == "(Improvement)":
        sign = "+"
    else:
        sign = "-"

    parts = match.group(2).strip().split(' - ')
    if parts[0] not in trees:
        print "INVALID TREE: %s" % parts[0]
        return [None, None, None, None]

    if parts[2] not in platforms:
#        print "INVALID PLATFORM: '%s'" % parts[2]
        return [None, None, None, None]

    if parts[1] not in tests:
        print "INVALID TEST NAME: %s" % parts[1]
        return [None, None, None, None]

    parts[3] = "%s%s" % (sign, parts[3])
    return parts


def parseMailbox(config):
    mbox = mailbox.MHMailbox(config['maildir'])
    while 1:
        msg = mbox.next()
        if not msg:
            break

        parseMessage(config, msg)

def parseMessage(config, msg):
    parts = validSubject(subject_of(msg))

    if not parts[0]:
        return

    branch = parts[0]
    test = parts[1]
    platform = parts[2]
    percent = parts[3]
    body = msg.fp.read()

    if not body:
        return

    graphurl = None
    changeset = None
    keyrevision = None
    bugCount = 0
    bugsection = False

# get these out of the body
#    Graph   : http://mzl.la/1iU7sbe
#Changeset range: http://hg.mozilla.org/integration/mozilla-inbound/pushloghtml?fromchange=1bb4238bdde3&tochange=89f9304ff4ba
    newbody = ""
    logbody = False

    for line in body.split('\n'):
        if line.strip().startswith('-----------------------------'):
            logbody = True

        try:
            line.strip().index('http://mzl.la/')
            graphurl = ':'.join(line.strip().split(':')[1:])
        except:
            pass

        try:
            line.strip().index('Changeset range')
            changeset = ':'.join(line.strip().split(':')[1:])
            parts = changeset.split('=')
            rawparts = []
            for p in parts:
                raw = p.split('&')
                for r in raw:
                   rawparts.append(r)
            rawparts[-1] = rawparts[-1].zfill(12)
            rawparts[-3] = rawparts[-3].zfill(12)
            changeset = "%s=%s&%s=%s" % (rawparts[0], rawparts[1], rawparts[2], rawparts[3])
        except:
            pass

        try:
            line.strip().index('since revision')
            keyrevision = line.strip().split(' ')[-1].strip()
            keyrevision = keyrevision.zfill(12)
        except:
            pass

        if bugsection:
            if line.strip().startswith('* http://bugzilla.mozilla.org/show_bug.cgi?id='):
                bugCount += 1
            if line.strip() == '':
                bugsection = None

        if line.strip().startswith('Bugs:'):
            bugsection = True

        if logbody:
            newbody += "%s\n" % line

    if not graphurl or not changeset:
        print "INVALID BODY: no graphurl or changeset"
        return

    csets = getRevisions(changeset)

    date = msg.get('Date')
    parsed = rfc822.parsedate(date)

    merged = ''
    if bugCount > 5:
        # search for csets in existing 
        db_csets = getCSets(config)
        merged = ''
        for i, k, c in db_csets:
            if k in csets:
                merged = k
                # found the key revision in the merged changeset, see if others are there
                for originalrev in c:
                    if originalrev not in csets:
#                        print "OH NO: found keyrevision %s, but not other cset: %s from original in current set: %s" % (k, originalrev, c)
#                        print "       platform: %s, branch: %s, test %s, keyrevision %s, csets: %s\n" % (platform, branch, test, keyrevision, csets)
                        merged = ''
                        break

            if merged:
                break

    datestring = "%s-%s-%s %s:%s:%s" % (str(parsed[0]).zfill(4), str(parsed[1]).zfill(2), str(parsed[2]).zfill(2), str(parsed[3]).zfill(2), str(parsed[4]).zfill(2), str(parsed[5]).zfill(2))

    db = MySQLdb.connect(host=config['host'],
                         user=config['username'],
                         passwd=config['password'],
                         db=config['database'])

    # TODO: figure out if we should set these fields to a specific value
    comment = ''
    bug = ''
    status = ''
    body = MySQLdb.escape_string(newbody)

    #TODO: is branch valid?
    tbpl_branch = branch.split('-Non-PGO')[0]
    dzdata = getDatazillaData(tbpl_branch)
    vals = getRevisionRange(dzdata, keyrevision)
    link = ''
    if vals:
        tree = '?tree=%s&' % tbpl_branch
        if 'OSX' in tbpl_platforms[platform]:
             tbpl_trees[branch] = tbpl_trees[branch].split(' pgo')[0]
        if tbpl_branch == 'Firefox':
            tree = '?'
        link = 'https://tbpl.mozilla.org/%sfromchange=%s&tochange=%s&jobname=%s %s talos %s' % (tree, vals[0], vals[1], tbpl_platforms[platform], tbpl_trees[branch], tbpl_tests[test])
        link = link.replace(' ', '%20')

    foundDuplicate = False
    cur = db.cursor()
    # TODO: is this valid? we are checking if the branch is equal, same with percent- in this case it already exists?!?
    sql = "select id from alerts where branch='%s' and test='%s' and platform='%s' and percent='%s'" % (branch, test, platform, percent)
    cur.execute(sql)
    for row in cur.fetchall():
        if row[0]:
          foundDuplicate = row[0]

    cur.close()

    if foundDuplicate:
        if merged:
            markMerged(config, foundDuplicate, merged)
        addTbplURL(foundDuplicate, link)
        return

    if 1 == 0:
        print "branch: %s" % branch
        print "test: %s" % test
        print "platform: %s" % platform
        print "percent: %s" % percent
        print "graphurl: %s" % graphurl
        print "changeset: %s" % changeset
        print "keyrevision: %s" % keyrevision
        print "bugcount: %s" % bugCount
        print "changesets: %s" % csets

    cur = db.cursor()
    sql = 'insert into alerts (branch, test, platform, percent, graphurl, changeset, keyrevision, bugcount, comment, bug, status, body, date, changesets, mergedfrom, tbplurl) values ('
    sql += "'%s'" % branch
    sql += ", '%s'" % test
    sql += ", '%s'" % platform
    sql += ", '%s'" % percent
    sql += ", '%s'" % graphurl
    sql += ", '%s'" % changeset
    sql += ", '%s'" % keyrevision
    sql += ", %s" % bugCount
    sql += ", '%s'" % comment
    sql += ", '%s'" % bug
    sql += ", '%s'" % status
    sql += ", '%s'" % body
    sql += ", '%s'" % datestring
    sql += ", '%s'" % ','.join(csets)
    sql += ", '%s'" % merged
    sql += ", '%s'" % link
    sql += ')'

    cur.execute(sql)
    cur.close()


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("--config",
                    action = "store", type = "string", dest = "config",
                    default = 'config.ini',
                    help = "path to the config file [config.ini]")

    options, args = op.parse_args()

    if not os.path.exists(options.config):
        print "ERROR: %s doesn't exist" % (options.config)
        sys.exit(1)

    parser = ConfigParser.RawConfigParser()
    parser.read(options.config)

    config = {'username': parser.get('alerts', 'username'), 
              'password': parser.get('alerts', 'password'), 
              'host': parser.get('alerts', 'host'), 
              'database': parser.get('alerts', 'database'), 
              'maildir': parser.get('alerts', 'maildir')}
    parseMailbox(config)

