# All the times here are in hours
# These are the times for non-pgo
import requests
import logging
from mozci.mozci import query_repo_url_from_buildername, query_repo_name_from_buildername, \
        trigger_all_talos_jobs, trigger_range, set_query_source
from mozci.query_jobs import TreeherderApi
from mozci.platforms import build_talos_buildernames_for_repo
from mozci.utils import transfer
from thclient import TreeherderClient
from store_alerts import getAlerts, updateAlert
from mozci.utils.misc import setup_logging
from managed_settings import TBPL_TESTS

LOG = setup_logging(logging.INFO)
# Use memory-saving mode
transfer.MEMORY_SAVING_MODE = True
TIME_TO_BUILD = 2
TIME_TO_TEST = 1
PENDING_TIME = 1
TIME_TO_WAIT = 2
CYCLE_TIME = 0.25
JSON_PUSHES = "%(repo_url)s/json-pushes"
WEEK = 604800
TWO_WEEKS = 1209600
SIXTY_DAYS = 5184000
SIGNATURE_URL = "https://treeherder.mozilla.org/api/project/%s/performance-data/get_performance_series_summary/?interval=%s"
PERFORMANCE_DATA = "https://treeherder.mozilla.org/api/project/%s/performance-data/get_performance_data/?interval_seconds=%s&signatures=%s"
OPTION_COLLECTION_HASH = "https://treeherder.mozilla.org/api/optioncollectionhash/"
SUCCESS = 0
DRY_RUN = False
REVERSE_TESTS = ['dromaeo_css', 'dromaeo_dom', 'v8_7', 'canvasmark']

# TODO: Ask about e10s
TREEHERDER_PLATFORM = {
    'linux32': 'Ubuntu HW 12.04',
    'linux64': 'Ubuntu HW 12.04 x64',
    'windowsxp': 'Windows XP 32-bit',
    'windows7-32': 'Windows 7 32-bit',
    'windows8-64': 'Windows 8 64-bit',
    'osx-10-10': 'Rev5 MacOSX Yosemite 10.10',
    'android-4-0-armv7-api11': 'Android 4.0 Tegra',
}

# Checked
def checkMerge(revision, buildername):
    "This function returns whether an alert is a merge or not."
    # Query Revision on pushlog, and check if all the authors of changesets are same.
    # We are not doing on the number of changesets, because a merge can have just 2 changesets
    # whereas a patch author can have 6-7 changeset.
    repo_url = query_repo_url_from_buildername(buildername)
    url = "%s?changeset=%s&version=2&full=1" % (JSON_PUSHES % {"repo_url": repo_url}, revision)
    req = requests.get(url).json()
    push_id = req["pushes"].keys()[0]
    changesets = req["pushes"][push_id]["changesets"]
    author = ""
    for changeset in changesets:
        if not author:
            author = changeset["author"]
        if changeset["author"] != author:
            return True

    return False

# Checked
def getRevisions(revision, buildername, start=0, end=0):
    "This function returns list of revisions for an alert."
    # Query Revision on pushlog, and get the revision. This should be easy.
    repo_url = query_repo_url_from_buildername(buildername)
    url = "%s?changeset=%s&version=2" % (JSON_PUSHES % {"repo_url": repo_url}, revision)
    req = requests.get(url).json()
    pushid = int(req["pushes"].keys()[0])
    startID = pushid + start - 1
    endID = pushid + end
    url = "%s?startID=%s&endID=%s&version=2&tipsonly=1" % (JSON_PUSHES % {"repo_url": repo_url}, startID, endID)
    req = requests.get(url).json()
    response = req["pushes"]
    revisionList = []
    for push in sorted(response.keys()):
        revisionList.append(response[push]["changesets"][0][0:12])

    return revisionList

# Checked
def getSuccessfulJobs(revision, buildername):
    "This function returns the number of data points for an alert."
    # Query TH client get_jobs method to get all jobs for a particular buildername
    # Then Query mozci function: https://github.com/armenzg/mozilla_ci_tools/blob/master/mozci/query_jobs.py#L187
    # to get the status of job for each job
    treeherder_api = TreeherderApi()
    repo_name = query_repo_name_from_buildername(buildername)
    matching_jobs = treeherder_api.get_matching_jobs(repo_name, revision, buildername)
    successful_jobs = 0
    for job in matching_jobs:
        status = treeherder_api.get_job_status(job)
        if status == SUCCESS:
            successful_jobs += 1
    return successful_jobs


def compare(test, buildername, revision, previous_revision):
    "This function will compare between 2 given revisions and return result as percentage"
    repo_name = query_repo_name_from_buildername(buildername)
    # Using TWO_WEEKS as interval, may change it afterwards
    signature_request_url = SIGNATURE_URL % (repo_name, TWO_WEEKS)
    signatures = requests.get(signature_request_url).json()
    options_collection_hash_list = requests.get(OPTION_COLLECTION_HASH).json()

    for signature, value in signatures.iteritems():
        # Skip processing subtests. They are identified by 'test' key in the dicitonary.
        if 'test' in value:
            continue

        # Ignoring e10s here.
        # TODO: Revisit this later
        if TBPL_TESTS[test]['testname'].lower() == value['suite'].lower() and TREEHERDER_PLATFORM[value["machine_platform"]] in buildername and 'test_options' not in value:
            test_signature = signature
        else:
            continue

        hash_signature = value['option_collection_hash']
        for key in options_collection_hash_list:
            if hash_signature == key["option_collection_hash"]:
                typeOfTest = key["options"][0]["name"]
                break

        if typeOfTest == 'pgo' and typeOfTest not in buildername:
            # if pgo, it should be present in buildername
            continue
        elif typeOfTest == 'opt':
            # if opt, nothing present in buildername
            break
        else:
            # We do not run talos on any branch other than pgo and opt.
            continue

    # Using TWO_WEEKS as interval, may change it afterwards
    req = requests.get(PERFORMANCE_DATA % (repo_name, TWO_WEEKS, test_signature)).json()
    performance_data = req[0]["blob"]
    treeherder_client = TreeherderClient()
    revision_resultset_id = treeherder_client.get_resultsets(repo_name, revision=revision)[0]["id"]
    previous_revision_resultset_id = treeherder_client.get_resultsets(repo_name, revision=previous_revision)[0]["id"]
    revision_perfdata = []
    previous_revision_perfdata = []

    for data in performance_data:
        if data["result_set_id"] == revision_resultset_id:
            revision_perfdata.append(data["geomean"])
        elif data["result_set_id"] == previous_revision_resultset_id:
            previous_revision_perfdata.append(data["geomean"])

    if revision_perfdata and previous_revision_perfdata:
        mean_revision_perfdata = sum(revision_perfdata) / float(len(revision_perfdata))
        mean_previous_revision_perfdata = sum(previous_revision_perfdata) / float(len(previous_revision_perfdata))


    if test in REVERSE_TESTS:
        # lower value results in regression
        return (mean_revision_perfdata - mean_previous_revision_perfdata) * 100.0 / mean_previous_revision_perfdata
    else:
        # higher value results in regression
        return (mean_previous_revision_perfdata - mean_revision_perfdata) * 100.0 / mean_previous_revision_perfdata


def main():
    alerts = getAlerts()
    for alert in alerts:
        # new alert
        LOG.info("Running alert for: [%s, %s, %s]" % (alert['test'], alert['buildername'], alert['revision']))
        if alert['stage'] == 0:
            LOG.info("We are in stage 0.")
            if checkMerge(alert['revision'], alert['buildername']) or 'pgo' in alert['buildername']:
                LOG.info("We are ignoring alert: %s since it is either a merge or a pgo job." % alert['test'])
                alert['stage'] = -1 # We need to have manual inspection in this case.
                alert['user'] = 'human'
                updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
            else:
                alert['stage'] = 1

        # trigger jobs for backfill
        if alert['stage'] == 1:
            LOG.info("We are in stage 1, and going to backfill jobs.")
            revisionList = getRevisions(alert['revision'], alert['buildername'], start=-2, end=2)
            # Setting Treeherder as the source for querying.
            set_query_source("treeherder")
            trigger_range(alert['buildername'], revisionList, times=6, dry_run=DRY_RUN)
            alert['stage'] = 2
            # We want some time interval between stage 1 and 2, so we exit.
            updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
            continue


        # verify jobs for backfill
        if alert['stage'] == 2:
            LOG.info("We are in stage 2, and going to verify if jobs are backfilled.")
            revisionList = getRevisions(alert['revision'], alert['buildername'], start=-2, end=2)
            for revision in revisionList:
                dataPoints = getSuccessfulJobs(revision, alert['buildername'])

                # If dataPoints are less than 6, it means that builds/jobs are still running.
                if dataPoints < 6:
                    # We wait for 6 hours for all triggered tests to complete,
                    # And if they don't then we mark them for manual intervention/
                    alert['loop'] += 1
                    if alert['loop'] > (TIME_TO_BUILD + TIME_TO_TEST + PENDING_TIME) / CYCLE_TIME:
                        LOG.info("The jobs did not complete backfilling in time, assigning for human inspection.")
                        alert['stage'] = -1
                        alert['user'] = 'human'
                    else:
                        alert['stage'] = 1

                    break

            if alert['stage'] != 2:
                updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
                continue

            badRevisions = []
            # Reset the loop for upcoming stages
            alert['loop'] = 0
            for i in range(1, len(revisionList)):
                results = compare(alert['test'], alert['buildername'], revisionList[i], revisionList[i-1])
                if results < -2.0:
                    badRevisions.append(revisionList[i])

            if len(badRevisions) != 1:
                LOG.info("There are too many bad revisions: %s for alert %s on buildername %s, "
                         "assigning for human inspection." % (badRevisions, alert['test'], alert['buildername']))
                alert['stage'] = -1 # too noisy, something bad happened
                alert['user'] = 'human'
                updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
                continue

            if checkMerge(badRevisions[0], alert['buildername']):
                LOG.info("The bad revision %s identified for alert %s on buildername %s is a merge, "
                         "assigning for human inspection" % (badRevisions[0], alert['test'], alert['buildername']))
                alert['stage'] = -1 # A merge revision is a bad revision, manually inspect
                alert['user'] = 'human'

            if alert['revision'] != badRevisions[0]:
                LOG.info("Alert_Manager misreported the bad revision. The actual bad revision is %s "
                         "for alert %s on %s buildername." % (badRevisions[0], alert['test'], alert['buildername']))
                alert['revision'] = badRevisions[0] # we misreported initially, change the actual regression revision

            alert['stage'] = 3

        # Trigger all talos stage
        if alert['stage'] == 3:
            LOG.info("We are in stage 3, and going to trigger all_talos jobs.")
            repo_name = query_repo_name_from_buildername(alert['buildername'])
            # Setting Treeherder as the source for querying.
            set_query_source("treeherder")
            trigger_all_talos_jobs(repo_name, alert['revision'], times=6, dry_run=DRY_RUN)
            previousRevision = getRevisions(alert['revision'], alert['buildername'], start=-1, end=-1)[0]
            trigger_all_talos_jobs(repo_name, previousRevision, times=6, dry_run=DRY_RUN)
            alert['stage'] = 4
            updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
            continue

        # Verify All talos stage is completed
        if alert['stage'] == 4:
            LOG.info("We are in stage 4, and going to verify if all_talos ran successfully.")
            previousRevision = getRevisions(alert['revision'], alert['buildername'], start=-1, end=-1)[0]
            repo_name = query_repo_name_from_buildername(alert['buildername'])
            all_buildernames = build_talos_buildernames_for_repo(repo_name)
            for revision in [alert['revision'], previousRevision]:
                for buildername in all_buildernames:
                    dataPoints = getSuccessfulJobs(revision, buildername)
                    if dataPoints < 6:
                        # We wait for 8 hours for all talos tests to complete,
                        # And if they don't then we mark them for manual intervention
                        alert['loop'] += 1
                        if alert['loop'] > (TIME_TO_BUILD + TIME_TO_TEST + PENDING_TIME + TIME_TO_WAIT) / CYCLE_TIME:
                            LOG.info("The all talos jobs for alert %s on %s revision did not complete in time, "
                                     " assigning for human inspection." % (alert['test'], alert['revision']))
                            alert['stage'] = -1
                            alert['user'] = 'human'
                        else:
                            alert['stage'] = 3
                        break

                if alert['stage'] != 4:
                    break

            if alert['stage'] != 4:
                updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'],
                            alert['stage'], alert['loop'], alert['user'])
                continue

            alert['stage'] = 5  # final stage, sheriff will check for this.
            alert['user'] = 'human'
            LOG.info("All automated parts are complete.")

        updateAlert(alert['id'], alert['revision'], alert['buildername'], alert['test'], alert['stage'], alert['loop'], alert['user'])

if __name__=="__main__": main()
