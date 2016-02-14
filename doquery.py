import time
from datetime import datetime, timedelta
from db import app, getConfig
import os
import re
import settings
from lib.decorators import database_conn, memoize
from utils import build_tbpl_link


pmap = {}
pmap['Linux'] = 'Ubuntu HW 12.04'
pmap['Linux64'] = 'Ubuntu HW 12.04 x64'
pmap['Win7'] = 'WINnT 6.1 (ix)'
pmap['Win8'] = 'WINNT 6.2 x64'
pmap['WinXP'] = 'winnt 5.1 (ix)'
pmap['OSX64'] = 'MacOSX 10.6 (rev4)'
pmap['OSX10.8'] = 'MacOSX 10.8'
pmap['OSX10.10'] = 'MacOSX 10.10'
pmap['OSX10.105'] = 'MacOSX 10.10.5'
pmap['Android'] = 'Android 4.0.4'


@database_conn
def findDuplicates(db_cursor, branch, tests, platforms):
   for test in tests:
       for platform in platforms:
           query = "select id,platform,test,status,percent,keyrevision from alerts where branch='%s' and test='%s' and platform='%s' and percent<0" % (branch, test, pmap[platform])
           db_cursor.execute(query)
           rows = db_cursor.fetchall()
           data = {}
           for row in rows:
               if row[5] not in data:
                   data[row[5]] = row
               else:
                   old = data[row[5]]
                   if old[4] == row[4]:
                       if old[3] == 'Duplicate':
                           print "deleting:"
                           print old
                           db_cursor.execute("delete from alerts where id=%s" % old[0])
                           data[row[5]] = row
                       elif row[3] == 'Duplicate':
                           print "deleting:"
                           print row
                           db_cursor.execute("delete from alerts where id=%s" % row[0])



@database_conn
def getStats(db_cursor, branch, tests, platforms):
    for test in tests:
        summary = 0
        for platform in platforms:
            query = "SELECT count(id) FROM alerts WHERE test='%s' and platform='%s' and branch='%s' and percent<0" % (test, pmap[platform], branch)
            db_cursor.execute(query)

            row = db_cursor.fetchall()
            if row:                
                summary += row[0][0]
                testname = test
                if test == "Ts, Paint" or test == "SVG, Opacity Row Major":
                    testname = '"%s"' % test
                print "%s,%s,%s" % (testname, platform, row[0][0])
        print "%s,ZSummary,%s" % (test, summary)

if __name__ == "__main__":
    test_names = ["WEBGL Terrain", "TP5 Scroll", "TResize", "CanvasMark", "Tp5 Optimized",
                  "Dromaeo (DOM)", "Dromaeo (CSS)", "Kraken Benchmark", "V8 version 7",
                  "a11y Row Major MozAfterPaint", "Session Restore Test", "Paint", "Ts, Paint",
                  "Session Restore no Auto Restore Test", "SVG-ASAP", "Customization Animation Tests",
                  "Tab Animation Test", "tscroll-ASAP", "SVG, Opacity Row Major"]
    platforms = ['Linux', 'Linux64', 'OSX10.10', "OSX10.8", "OSX64", 'Win7', 'Win8', 'WinXP']

    getStats('Mozilla-Inbound', test_names, platforms)
#    findDuplicates('Mozilla-Inbound-Non-PGO', test_names, platforms)
