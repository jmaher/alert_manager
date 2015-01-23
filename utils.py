from lib.decorators import database_conn, memoize
from db import *
import settings
import requests

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
        tbpl_test = settings.TBPL_TESTS[record.test]
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

