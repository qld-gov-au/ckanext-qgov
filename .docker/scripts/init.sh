#!/usr/bin/env sh
##
# Initialise CKAN instance.
#
set -e

CKAN_USER_NAME="${CKAN_USER_NAME:-admin}"
CKAN_DISPLAY_NAME="${CKAN_DISPLAY_NAME:-Administrator}"
CKAN_USER_PASSWORD="${CKAN_USER_PASSWORD:-Password123!}"
CKAN_USER_EMAIL="${CKAN_USER_EMAIL:-admin@localhost}"

. /app/ckan/default/bin/activate
which ckan || (function ckan { paster --plugin=ckan $* -c /app/ckan/default/production.ini || exit 1 })
cd /app/ckan/default/src/ckan
ckan db clean || exit 1
ckan db init || exit 1
ckan user add "${CKAN_USER_NAME}"\
 fullname="${CKAN_DISPLAY_NAME}"\
 email="${CKAN_USER_EMAIL}"\
 password="${CKAN_USER_PASSWORD}" || exit 1
ckan sysadmin add "${CKAN_USER_NAME}" || exit 1

# Create some base test data
. /app/scripts/create-test-data.sh
