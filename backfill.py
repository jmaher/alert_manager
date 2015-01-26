from db import *
import settings



def create_buildername(platform, branch, test):
    tbpl_platform = settings.TBPL_PLATFORMS[platform]
    tbpl_test = settings.TBPL_TESTS[test]['jobname']
    tbpl_tree = settings.TBPL_TREES[branch]

    if 'OSX' in tbpl_platform:
        tbpl_tree = tbpl_tree.split(' pgo')[0]

    return '%s %s talos %s' % (tbpl_platform, tbpl_tree, tbpl_test)

def get_active_alerts():
    # return array of [revision, branch, buildername]
    retVal = []

    db = create_db_connection()
    cursor = db.cursor()

    query = "select platform, branch, test, keyrevision from alerts where (status='' or status='NEW' or status='Back Filling')"
    cursor.execute(query)
    alerts = cursor.fetchall()

    for alert in alerts:
        retVal.append([keyrevision, branch, create_buildername(platform, branch, test)])

    cursor.close()
    db.close()
    return retVal

def update_alerts():
    conflicting = []
    
    alerts = get_active_alerts()
    for alert in alerts:
        print alert


if __name__ == "__main__":
    write_bug_report()
