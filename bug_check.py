from server import create_db_connnection
import MySQLdb
import requests

#------------------------------------------------------------------------------
#
# This python module polls the bugs marked as 'investigating' in the
# database. It then polls bugzilla for the status of each bug, and builds
# a list of 'conflicts' where the bug is resolved on bugzilla, but not in the
# database
#
#------------------------------------------------------------------------------
def getStatus(bugid):
    status = None
    try:
        url = "https://bugzilla.mozilla.org/rest/bug/" + str(bugid)+ "?include_fields=id,status,resolution";
        bzjson = requests.get(url).json()
        bugs = bzjson['bugs'];
        details = [];
        # bugs is an array of bugs, for this query it is a single item in the array
        if (int(bugs[0]['id']) == int(bugid)):
            status = bugs[0]['status'];  
            details.append(status);
            details.append(bugs[0]['resolution'])         
            return details;
    except:
        return "None";
def get_investigating_bugs():
    """
    Builds a list of bugs for which the status is marked as 'investigating' 
    in the local database

    INPUTS: None
    OUTPUT: List of bugids which are marked as 'investigating'
    """

    #Get database connection
    db = create_db_connnection()
    cursor = db.cursor()

    #Query for the 'investigating' bugs
    query = "select bug from alerts where status = 'Investigating'"
    cursor.execute(query)
    ids = cursor.fetchall()
    #Append the bug id's to the list object to be returned
    buglist = []
    for bugid in ids:
        buglist.append(bugid[0])
    
    cursor.close()
    db.close()
    return buglist


def get_conflicting_bugs():
    """
    Get a list of bugs for which their status is 'investigating' in the local
    database, but 'RESOLVED' at bugzilla

    INPUTS: None
    OUTPUT: List of bugids which are 'conflicting' as per the above definition
    """
    conflicting = []

    #Get the local db bugs marked as 'investigating'
    investigating = get_investigating_bugs()
    #Check to see if any 'investigating' bugs are resolved on bugzilla
    for bugid in investigating:
        param = [];
        param= getStatus(bugid);
        if (param[0] == 'RESOLVED'):
            conflicting.append(bugid)
            conflicting.append(param[1])
    return conflicting
