#!/usr/bin/env bash
##
# Build site in CI.
#
set -e

# Process Docker Compose configuration. This is used to avoid multiple
# docker-compose.yml files.
# Remove lines containing '###'.
sed -i -e "/###/d" docker-compose.yml
# Uncomment lines containing '##'.
sed -i -e "s/##//" docker-compose.yml

# Pull the latest images.
ahoy pull

PYTHON=python
if [ "$CKAN_VERSION" = "2.8" ] || [ "$CKAN_VERSION" = "2.9-py2" ]; then
    PYTHON_VERSION=py2
else
    PYTHON_VERSION=py3
    PYTHON="${PYTHON}3"
fi

sed "s|{CKAN_VERSION}|$CKAN_VERSION|g" .docker/Dockerfile-template.ckan \
    | sed "s|{PYTHON}|$PYTHON|g" \
    | sed "s|{PYTHON_VERSION}|$PYTHON_VERSION|g" \
    > .docker/Dockerfile.ckan

ahoy build || (ahoy logs; exit 1)
