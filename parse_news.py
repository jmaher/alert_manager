import logging
import mailbox
import string
import time
from collections import namedtuple
from datetime import datetime, timedelta
from email.utils import parsedate
from itertools import chain
from urllib import urlencode
from urlparse import parse_qsl, urlsplit, urlunsplit

import requests

from db import app
import os
import re
import settings
from lib.decorators import database_conn, memoize


logger = logging.getLogger('news parser')
logger.setLevel(settings.LOG_LEVEL)
file_handler = logging.FileHandler('news_parser.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


subject_trans_table = string.maketrans("\t", " ")
two_weeks = datetime.today() - timedelta(days=14)


SUBJECT_RE = re.compile('^(<Regression>|\(Improvement\))(.*)')
GRAPHURL_RE = re.compile('(http://mzl.la/.+)')
CSET_RE = re.compile('Changeset range: (http://.+)')

# TODO: do we need to support other branches
REV_RE = re.compile(
    'href=\"(\/integration)?\/'
    '(b2g-inbound|mozilla-central|mozilla-inbound|fx-team)'
    '\/rev\/([0-9a-f]+)\"')


fields = ('branch', 'test', 'platform', 'percent',
          'graphurl', 'changeset', 'keyrevision', 'bugcount', 'body', 'push_date',
          'comment', 'bug', 'status')
record = namedtuple('record', fields)


def parse_mailbox():
    """Main routine"""
    mbox = mailbox.MH(settings.MAILDIR)

    read = set(mbox.get_sequences().get('read', ''))
    unread = set(mbox.keys()) - read

    logger.info('Parsing mailbox. Got %d unread messages' % len(unread))

    for msg_id in unread:
        record = parse_message(mbox[msg_id])

        if not record:
            logger.info('Message can not be parsed')
            continue

        if record.date >= two_weeks:
            csets = get_revisions(record.changeset)
        else:
            csets = set()

        check_for_backout(record)
        merged = is_merged(record, csets)
        duplicate = check_for_duplicate(record)
        link = build_tbpl_link(record)

        if duplicate:
            if merged:
                mark_merged(duplicate, merged)
            add_tbpl_url(duplicate, link)

        update_database(record, merged, link, csets)

    all_read = unread | read
    mbox.set_sequences({'read': all_read})

    logger.info('DONE')


def parse_message(msg):
    """Handles parsing of message content.

    Returns result packed in named tuple "record"
    or None if message can not be parsed.

    Record fields:
        'branch', 'test', 'platform', 'percent',
        'graphurl', 'changeset', 'keyrevision', 'bugcount','body', 'date',
        'comment', 'bug', 'status'
    To get 'platform' from "record":
    * record.platform
    * record[2]
    """
    subject = parse_subject(get_subject(msg))
    if not subject:
        return

    body = parse_body(msg)
    if not body:
        return

    logger.info('Message parsed successfully')

    return record._make(chain(subject, body))


def get_subject(msg):
    """Retrieves subject of mail message.

    Returns empty string if message doesn't have subject.
    """
    subject = msg.get('subject', '')
    return subject.translate(subject_trans_table, '\n')


def parse_subject(subject, subject_re=SUBJECT_RE):
    """Parses message subject.

    Returns None if subject can not be parsed.
    """
    match = subject_re.match(subject)
    if not match:
        return

    if match.group(1) == '(Improvement)':
        sign = '+'
    else:
        sign = '-'

    parts = match.group(2).strip().split(' - ')
    if parts[0] not in settings.TREES:
        logger.info('INVALID TREE: %s' % parts[0])
        return

    if parts[1] not in settings.TESTS:
        logger.info('INVALID TEST NAME: %s' % parts[1])
        return

    if parts[2] not in settings.PLATFORMS:
        logger.info('INVALID PLATFORM: %s' % parts[2])
        return

    parts[3] = "%s%s" % (sign, parts[3])
    return parts


def parse_body(msg, graphurl_re=GRAPHURL_RE, cset_re=CSET_RE):
    body = msg.get_payload()
    if not body:
        return

    graph_url = None
    change_set = None
    key_revision = None
    bug_count = 0
    new_body_parts = []

    # TODO: figure out if we should set these fields to a specific value
    comment = bug = status = ''

    bug_section = False
    log_body = False

    match = graphurl_re.search(body)
    if match:
        graph_url = match.group(1)

    match = cset_re.search(body)
    if match:
        parsed_url = urlsplit(match.group(1))
        query_parts = parse_qsl(parsed_url.query)

        new_parts = []
        for param, value in query_parts:
            new_value = value.zfill(12)
            if param == 'tochange':
                key_revision = new_value

            new_parts.append((param, new_value))
        new_query_part = tuple([urlencode(new_parts)])
        change_set = urlunsplit(parsed_url[:3] + new_query_part + parsed_url[4:])

    if not graph_url or not change_set:
        logger.error('INVALID BODY: no graphurl or changeset')
        return

    for line in body.splitlines():
        line = line.strip()

        if line.startswith('-' * 29):
            log_body = True
            continue

        if log_body:
            new_body_parts.append(line)

        if line.startswith('Bugs:'):
            bug_section = True
            continue

        if bug_section:
            if line.startswith('* http://bugzilla.mozilla.org/show_bug.cgi?id='):
                bug_count += 1
            if not line:
                bug_section = False

    new_body = u'\n'.join(new_body_parts)
    parsed_date = parsedate(msg['date'])
    date_ = datetime.fromtimestamp(time.mktime(parsed_date))

    return (graph_url, change_set, key_revision,
            bug_count, new_body, date_,
            comment, bug, status)


def is_merged(record, csets):
    # TODO: find a better way to determine merged.
    # possibly search top commit for merge & bugcount > 5 ?

    merged = ''
    if csets and record.bugcount > 10:
        for keyrev, stored_csets in get_csets():  # search for csets in existing
            if keyrev in csets:
                # found the key revision in the merged changeset,
                # see if others are there
                if all(originalrev in csets for originalrev in stored_csets):
                    merged = keyrev
                    break

    return merged


def build_tbpl_link(record):
    # TODO: is branch valid?
    tbpl_branch = record.branch.split('-Non-PGO')[0]

    dzdata = get_datazilla_data(tbpl_branch)
    vals = get_revision_range(dzdata, record.keyrevision)

    link = ''
    if vals:
        params = []

        tbpl_platform = settings.TBPL_PLATFORMS[record.platform]
        tbpl_test = settings.TBPL_TESTS[record.test]
        tbpl_tree = settings.TBPL_TREES[record.branch]

        if 'OSX' in tbpl_platform:
            tbpl_tree = tbpl_tree.split(' pgo')[0]

        if tbpl_branch != 'Firefox':
            params.append(('tree', tbpl_branch))

        params.append(('fromchange', vals[0]))
        params.append(('tochange', vals[1]))
        params.append(('jobname', '%s %s talos %s' % (tbpl_platform, tbpl_tree, tbpl_test)))
        link = '%s/' % settings.TBPL_URL
        delim = '?'
        for key, value in params:
            link = "%s%s%s=%s" % (link, delim, key, value)
            if delim == '?':
                delim = '&'
        link = link.replace(' ', '%20')

    return link


@database_conn
def get_csets(db_cursor):

    now = app.config["now"]

    query = """SELECT keyrevision, changesets FROM alerts
               WHERE DATE_SUB(%s, INTERVAL 14 DAY) < PUSH_DATE;"""
    db_cursor.execute(query, (now,))

    results = []
    for keyrev, csets in db_cursor.fetchall():
        results.append([keyrev, csets.split(',')])
    return results


@database_conn
def check_for_duplicate(db_cursor, record):
    # TODO: is this valid? we are checking if the branch is equal,
    # same with percent- in this case it already exists?!?s
    query = """SELECT id FROM alerts WHERE
               branch=%s AND test=%s AND platform=%s AND percent=%s"""
    db_cursor.execute(
        query,
        (record.branch, record.test, record.platform, record.percent))

    duplicate = None
    for row in db_cursor.fetchall():
        if row[0]:
            duplicate = row[0]
    return duplicate


@database_conn
def add_tbpl_url(db_cursor, id_, tbpl_url):
    if tbpl_url:
        query = "SELECT tbplurl FROM alerts WHERE id=%s"
        db_cursor.execute(query, (id_,))

        row = db_cursor.fetchone()
        if not (row and row[0] != 'NULL'):
            query = "UPDATE alerts SET tbplurl=%s WHERE id=%s"
            db_cursor.execute(query, (tbpl_url, id_))


@database_conn
def mark_merged(db_cursor, id_, original_key_revision):
    query = "SELECT mergedfrom FROM alerts WHERE id=%s"
    db_cursor.execute(query, (id_,))

    row = db_cursor.fetchone()
    if not row:
        query = "UPDATE alerts SET mergedfrom=%s WHERE id=%s"
        db_cursor.execute(query, (original_key_revision, id_))


@memoize
def get_datazilla_data(branch_id):
    """Returns data retrieved from datazilla.

    Data is cached in memory to avoid redundant
    requests to datazilla or producing temp files on disk.
    """
    url = settings.DATAZILLA_URL_TEMPLATE % {'branch': branch_id, 'days': 21}
    return requests.get(url).json()


def get_revision_range(dzdata, revision):
    # TODO: switch this to hg instead of datazilla (jmaher)
    for item in dzdata:
        if revision in dzdata[item]['revisions']:
            revid = int(item)
            break
    else:
        logger.info('Unable to find revision: %s' % revision)
        return

    lower = str(revid - 6)
    upper = str(revid + 6)

    if lower not in dzdata:
        logger.info('Unable to get range, missing id: %s' % lower)
        return
    if upper not in dzdata:
        logger.info('Unable to get range, missing id: %s' % upper)
        return

    return dzdata[lower]['revisions'][-1], dzdata[upper]['revisions'][-1]


@memoize
def get_revisions(changeset_url, rev_re=REV_RE):
    cpart = changeset_url.split('?')[-1].replace('&', '_')
    cache_file = os.path.join(settings.TEMP_CSET_DIR, cpart)

    if not os.path.exists(cache_file):
        data = requests.get(changeset_url).content
        with open(cache_file, 'w+') as fhandle:
            fhandle.write(data)
    else:
        with open(cache_file, 'r') as fhandle:
            data = fhandle.read()

    matches = rev_re.finditer(data)
    return {m.group(3) for m in matches}


@database_conn
def check_for_backout(db_cursor, record):
    query = """SELECT id FROM alerts
               WHERE platform=%s AND test=%s AND branch=%s
               AND ABS(SUBSTRING_INDEX(percent, "%%", 1)) between %s and %s
               AND backout IS NULL
               AND DATE_SUB(%s, INTERVAL 7 DAY) < push_date;"""

    percent = float(record.percent[1:-1])
    query_params = (
        record.platform,
        record.test,
        record.branch,
        percent * 0.9,
        percent * 1.1,
        app.config["now"]
    )

    db_cursor.execute(query, query_params)

    results = db_cursor.fetchall()
    if results:
        query = "UPDATE alerts SET backout=%s WHERE id=%s"
        db_cursor.execute(query, (record.keyrevision, results[0]))


@database_conn
def update_database(db_cursor, record, merged, link, csets):
    query = """INSERT into alerts
               (branch, test, platform, percent,
               graphurl, changeset, keyrevision, bugcount,
               body, push_date, comment, bug,
               status, mergedfrom, tbplurl, changesets)
               VALUES
               (%(branch)s, %(test)s, %(platform)s, %(percent)s,
               %(graphurl)s, %(changeset)s, %(keyrevision)s, %(bugcount)s,
               %(body)s, %(push_date)s, %(comment)s, %(bug)s, %(status)s,
               %(merged)s, %(tbpl_url)s, %(csets)s)"""

    data = record._asdict()
    data['merged'] = merged
    data['tbpl_url'] = link
    data['csets'] = ', '.join(csets)
    db_cursor.execute(query, data)


def create_tmp_directories():
    """Creates necessary temp directories"""
    if not os.path.exists(settings.TEMP_CSET_DIR):
        os.mkdir(settings.TEMP_CSET_DIR)


def clean_up():
    """Removes outdated tmpcset files"""
    ls = os.listdir(settings.TEMP_CSET_DIR)
    delta = timedelta(days=1)
    now = datetime.now()

    for fname in ls:
        file_path = os.path.join(settings.TEMP_CSET_DIR, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - mtime > delta:
            logger.info('File %s is obsolete. Removing.' % file_path)
            os.remove(file_path)


if __name__ == "__main__":
    create_tmp_directories()
    parse_mailbox()
    clean_up()
