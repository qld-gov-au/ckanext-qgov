#!/usr/bin/env sh
##
# Initialise CKAN instance.
#
set -e


if [ "$VENV_DIR" != "" ]; then
  . ${VENV_DIR}/bin/activate
fi
ckan_cli db clean --yes
ckan_cli db init

# Create some base test data
. $APP_DIR/scripts/create-test-data.sh
