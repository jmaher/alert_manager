import MySQLdb
import datetime
import settings

def create_db_connnection(dbname):
    return MySQLdb.connect(host="localhost",
                           user="root",
                           passwd="root",
                           db=dbname)


def build_buildername(branch, test, platform):
    # This was leading to an error as there was no mapping, we don't run these anymore
    if platform in ["Android 2.2 (Native)", 'MacOSX 10.8', 'MacOSX 10.6 (rev4)']:
        return ''

    # We have branch as Firefox not mozilla-central.
    if branch == "mozilla-central":
        branch = 'Firefox'

    th_platform = settings.TBPL_PLATFORMS[platform]
    th_test = settings.TBPL_TESTS[test]['jobname']
    th_tree = settings.TBPL_TREES[branch]
    if 'OSX' in th_platform:
        th_tree = th_tree.split(' pgo')[0]

    if th_test == "other":
        if th_platform == 'Ubuntu HW 12.04 x64':
            th_test = "other_l64"
        else:
            th_test = "other_nol64"

    buildername = '%s %s talos %s' % (th_platform, th_tree, th_test)
    return buildername


def saveAlerts():
    db_alerts = create_db_connnection("alerts")
    cursor_alerts = db_alerts.cursor()
    # Right now setting it to get alerts for previous two weeks
    date = str(datetime.date.today() - datetime.timedelta(days=14))
    # We need to get only NEW alerts
    # WHERE if want alerts after >=some_date
    query = "SELECT branch, test, platform, keyrevision FROM alerts where push_date>='%s'" % date
    cursor_alerts.execute(query)
    db_alertbot = create_db_connnection("alertbot")
    cursor_alertbot = db_alertbot.cursor()
    for row in cursor_alerts.fetchall():
        branch = row[0]
        test = row[1]
        platform = row[2]
        revision = row[3]
        buildername = build_buildername(branch, test, platform)
        if buildername == '':
            continue
        stage = 0
        loop = 0
        user = 'bot'

        query = 'INSERT into alertbot (`revision`, `buildername`, `test`, `stage`, `loop`, `user`) values ("%s", "%s", "%s", %d, %d, "%s")' %       (revision, buildername, test, stage, loop, user)
        cursor_alertbot.execute(query)


def getAlerts():
    db_alertbot = create_db_connnection("alertbot")
    cursor_alertbot = db_alertbot.cursor()
    query = "SELECT `id`, `revision`, `buildername`, `test`, `stage`, `loop`, `user` FROM alertbot WHERE stage>=0 AND user='bot' ORDER BY `id` DESC LIMIT 1"
    cursor_alertbot.execute(query)
    alerts = []
    for row in cursor_alertbot.fetchall():
        alerts.append({
            'id':row[0],
            'revision': row[1],
            'buildername': row[2],
            'test': row[3],
            'stage': row[4],
            'loop': row[5],
            'user': row[6]
            })

    return alerts


def updateAlert(id, revision, buildername, test, stage, loop, user):
    db_alertbot = create_db_connnection("alertbot")
    cursor_alertbot = db_alertbot.cursor()
    query = 'UPDATE alertbot SET \
                `revision` = "%s",\
                `buildername` = "%s",\
                `test` = "%s",\
                `stage` = %d,\
                `loop` = %d,\
                `user` = "%s" WHERE\
                `id` = %d' % (revision, buildername, test, stage, loop, user, id)

    cursor_alertbot.execute(query)


if __name__ == "__main__":
    saveAlerts()
