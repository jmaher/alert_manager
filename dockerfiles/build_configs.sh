#!/bin/bash

cp fig.yml.template fig.yml
ALERT_MANAGER_DIR=$(echo $PWD|sed 's/\/dockerfiles//g')
printf "  volumes:\n" >> fig.yml
printf "    - $ALERT_MANAGER_DIR:/srv/www/alert_manager\n" >> fig.yml 

# Use a docker config.ini.dev leaving the config.py system in place for staging/prod scripting
cp alert_manager_web/config.ini.dev $ALERT_MANAGER_DIR/config.ini

# Check to see if boot2docker is used
BOOT2DOCKER=$(which boot2docker)
if [ $? -eq 0 ]
then
    BOOT2DOCKERIP=$(boot2docker ip 2>&1|awk '{print $NF}'|grep -v "^$")
    SITE="$BOOT2DOCKERIP"
    printf "\n\033[1mFor reference, it looks like you're running boot2docker\033[m\n"
    printf "\n\033[1mPlease make a note of this if this setup fails and you need some help\033[m\n"
else
    # Not using boot2docker, so assume localhost is where alert manager will show up
    SITE="127.0.0.1"
fi

printf "\033[1mCheck '\033[31mfig.yml\033[m\033[1m' in this directory.\033[m\n"
printf "\033[1mEnsure that the volumes: directive to points to your shared folder\033[m\n"
printf "\033[1mIt should be something like $ALERT_MANAGER_DIR:/srv/www/alert_manager\033[m\n"
printf "\033[1mAfter you check/edit, you should be all set!\033[m\n"
printf "\n\033[1mWhen you're ready, run '\033[31mfig up\033[m\033[1m' and browse to:\nhttp://$SITE:8080/alerts.html\033[m\n"

