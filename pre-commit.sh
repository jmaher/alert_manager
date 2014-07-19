#!/usr/bin/env bash
 
PY_CHANGED_FILES=`git diff --cached --name-only --diff-filter=ACMR | grep '.*.py$'` || exit 0
 
flake8 --ignore=E501,F403 $PY_CHANGED_FILES
 
if [ $? -ne 0 ]
then
    echo ""
    echo "Bother! Commit is rejected. Please, fix found errors."
    echo "If you want to commit anyway, run following command: 'git commit --no-verify'"
    exit 1
fi
 
exit 0
