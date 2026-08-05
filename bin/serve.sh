#!/usr/bin/env sh
set -e

. "${APP_DIR}"/bin/activate
ckan -c ${CKAN_INI} run --disable-reloader --threaded
