#!/bin/bash
echo "Package installation ongoing"
apt-get install -y python3-pip
apt-get install -y libssl-dev libmysqlclient-dev
apt install -y python3-dev 
apt install -y build-essential
apt-get install -y libffi-dev
curl -sSL https://get.docker.com | sh
pip3 -v install docker-compose
pip3 install -r /root/concierge/install/requirements.txt
# tbc : install daemon and restart docker
apt-get install -y syslog-ng
echo "source s_net { tcp(ip(0.0.0.0) port(514) max-connections (5000)); udp(); };" >> /etc/syslog-ng/syslog-ng.conf
echo "log { source(s_net); destination(d_syslog); };" >> /etc/syslog-ng/syslog-ng.conf
systemctl restart syslog-ng
if [ -f .env ]
then
  set -o allexport; source .env; set +o allexport
fi
mkdir -p $ROOT_DIR
mkdir -p /nginx2/conf
cp nginx/app_nginx.conf /nginx2/conf/app_nginx.conf
cp nginx/uwsgi_params /nginx2/uwsgi_params
timedatectl set-timezone ${TIMEZONE}
echo "Package installation finished"

echo "Building now docker containers, this will take a lot time"
docker-compose build
docker-compose run backenddb python3 manage.py migrate
docker-compose run backenddb python3 manage.py collectstatic
docker-compose run backenddb python3 manage.py loaddata initial_data.json
# docker-compose run backenddb python3 manage.py dumpdata --natural-primary --natural-foreign --indent 4 -e sessions -e admin -e contenttypes -e auth.Permission > initial_data.json
echo "Installation finished, reboot now the system"
