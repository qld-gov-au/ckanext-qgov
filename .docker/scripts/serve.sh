#!/usr/bin/env sh
set -e

dockerize -wait tcp://postgres:5432 -timeout 1m
dockerize -wait tcp://solr:8983 -timeout 1m
dockerize -wait tcp://redis:6379 -timeout 1m

. ${APP_DIR}/scripts/activate
if (which ckan > /dev/null); then
    ckan -c ${CKAN_INI} run -r
else
    paster serve ${CKAN_INI}
fi
