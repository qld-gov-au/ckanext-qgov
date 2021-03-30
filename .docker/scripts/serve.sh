#!/usr/bin/env sh
set -e

dockerize -wait tcp://postgres:5432 -timeout 1m
dockerize -wait tcp://solr:8983 -timeout 1m

sed -i "s@SITE_URL@${SITE_URL}@g" /app/ckan/default/production.ini

python -m smtpd -n -c DebuggingServer localhost:25 &

CKAN_INI_FILE=/app/ckan/default/production.ini

. /app/ckan/default/bin/activate
if (which ckan > /dev/null); then
    ckan -c ${CKAN_INI_FILE} run
else
    paster serve ${CKAN_INI_FILE}
fi
