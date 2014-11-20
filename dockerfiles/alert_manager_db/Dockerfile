FROM ubuntu

MAINTAINER Jamon Camisso <jamon@jamon.ca>

VOLUME /var/lib/mysql

# Don't prompt for input
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -q -y update
RUN apt-get -q -y dist-upgrade
RUN apt-get -q -y install mysql-server supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY provision_mysql.sh /usr/local/bin/provision_mysql.sh
RUN chmod 775 /usr/local/bin/provision_mysql.sh
EXPOSE 3306

# Unset DEBIAN_FRONTEND per http://docs.docker.com/reference/builder/#env
ENV DEBIAN_FRONTEND ''

CMD ["/usr/bin/supervisord"]
