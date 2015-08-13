import requests
import logging
import subprocess
from argparse import ArgumentParser
from mozci.sources.buildapi import query_repo_url
JSON_PUSHES = "%(repo_url)s/json-pushes"
logging.basicConfig(format='%(levelname)s:\t %(message)s')
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
# requests is too noisy
logging.getLogger("requests").setLevel(logging.WARNING)


def parse_args(argv=None):
    parser = ArgumentParser()
    parser.add_argument("-s", "--start-rev",
                        dest="start_rev",
                        type=str,
                        help="Starting revision.")
    parser.add_argument("-e", "--end-rev",
                        dest="end_rev",
                        type=str,
                        help="Ending revision.")
    parser.add_argument("-c", "--changeset",
                        dest="changeset",
                        type=str,
                        help="Current changeset.")
    parser.add_argument("--cwd",
                        dest="cwd",
                        #required=True,
                        type=str,
                        help="Path for mozilla repo.")
    parser.add_argument("--repo",
                        dest="repo_name",
                        required=True,
                        type=str,
                        help="Repository Name.")
    parser.add_argument("-t", "--try-syntax",
                        dest="try_syntax",
                        required=True,
                        type=str,
                        help="Try syntax with which push.")
    options = parser.parse_args(argv)
    return options


def main():
    options = parse_args()
    repo_url = query_repo_url(options.repo_name)
    if options.start_rev and options.end_rev:
        url = "%s?fromchange=%s&tochange=%s&tipsonly=1" % (JSON_PUSHES % {"repo_url": repo_url},
                options.start_rev, options.end_rev)
    elif options.changeset:
        url = "%s?changeset=%s" % (JSON_PUSHES % {"repo_url": repo_url}, options.changeset)
    else:
        raise Exception("You need to enter either -start-rev and --end-rev or --changeset")

    response = requests.get(url).json()
    total_revisions = []
    for push, value in response.iteritems():
        for changeset in value["changesets"]:
            total_revisions.append(changeset)

    LOG.info("We are going to push the following revisions on try:\n %s" % total_revisions)

    for revision in total_revisions:
        LOG.info("Updating and pushing the revision %s to try" % revision)
        commands = [
            ['hg', 'qpop', '-a'],
            ['hg', 'update', '%s' % revision],
            ['hg', 'qnew', 'trypatch'],
            ['hg', 'qpush', 'trypatch'],
            ['hg', 'qref', '-m', 'hg update %s; %s' % (revision, options.try_syntax)],
            ['hg', 'push', '-f', 'try']
        ]

        print commands
        for command in commands:
            subprocess.call(command, cwd=options.cwd)

        LOG.info("Pushed revision %s to try" % revision)


if __name__ == "__main__": main()