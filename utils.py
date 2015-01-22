from db import *

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

