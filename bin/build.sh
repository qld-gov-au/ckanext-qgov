#!/usr/bin/env bash
##
# Build site in CI.
#
set -ex

# Process Docker Compose configuration. This is used to avoid multiple
# docker-compose.yml files.
# Remove lines containing '###'.
sed -i -e "/###/d" docker-compose.yml
# Uncomment lines containing '##'.
sed -i -e "s/##//" docker-compose.yml

# Pull the latest images.
ahoy pull

PYTHON=python

CKAN_GIT_VERSION=$CKAN_VERSION
CKAN_GIT_ORG=ckan

if [ "$CKAN_VERSION" = "2.10" ]; then
    if [ "$CKAN_TYPE" = "custom" ]; then
      CKAN_GIT_VERSION=ckan-2.10.0-qgov.1
      CKAN_GIT_ORG=qld-gov-au
    fi

    PYTHON_VERSION=py3
    PYTHON="${PYTHON}3"
else
    if [ "$CKAN_TYPE" = "custom" ]; then
      CKAN_GIT_VERSION=ckan-2.9.5-qgov.9
      CKAN_GIT_ORG=qld-gov-au
    fi

    if [ "$CKAN_VERSION" = "2.9-py2" ]; then
        PYTHON_VERSION=py2
        CKAN_GIT_VERSION=2.9
    else
        PYTHON_VERSION=py3
        PYTHON="${PYTHON}3"
    fi
fi

sed "s|{CKAN_VERSION}|$CKAN_VERSION|g" .docker/Dockerfile-template.ckan \
    | sed "s|{CKAN_GIT_VERSION}|$CKAN_GIT_VERSION|g" \
    | sed "s|{CKAN_GIT_ORG}|$CKAN_GIT_ORG|g" \
    | sed "s|{PYTHON_VERSION}|$PYTHON_VERSION|g" \
    | sed "s|{PYTHON}|$PYTHON|g" \
    > .docker/Dockerfile.ckan

ahoy build
