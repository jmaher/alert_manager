FROM ubuntu

MAINTAINER Jamon Camisso <jamon@jamon.ca>

#  Don't prompt for input
ENV DEBIAN_FRONTEND noninteractive

# Update the base image
RUN apt-get update
#RUN apt-get -y upgrade

# Install packages
RUN apt-get -q -y install libmysqlclient-dev python-pip git curl bzip2 python-dev mysql-client
RUN mkdir -p /srv/www/alert_manager

# Setup python packages
ADD requirements.txt /tmp/requirements.txt
RUN ["/usr/bin/pip", "install", "-r", "/tmp/requirements.txt"]
RUN ["/bin/rm", "/tmp/requirements.txt"]

# Unset DEBIAN_FRONTEND per http://docs.docker.com/reference/builder/#env
ENV DEBIAN_FRONTEND ''

# Run the development server, port 8159 is used, see fig file for port forward rules
CMD /usr/bin/python /srv/www/alert_manager/server.py
