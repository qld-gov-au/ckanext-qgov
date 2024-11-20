#!/usr/bin/env sh
##
# Install current extension.
#
set -ex

install_requirements () {
    PROJECT_DIR=$1
    shift
    # Identify the best match requirements file, ignore the others.
    # If there is one specific to our CKAN or Python version, use that.
    for filename_pattern in "$@"; do
        filename="$PROJECT_DIR/${filename_pattern}-$CKAN_VERSION.txt"
        if [ -f "$filename" ]; then
            pip install -r "$filename"
            return 0
        fi
    done
    for filename_pattern in "$@"; do
        filename="$PROJECT_DIR/${filename_pattern}-$PYTHON_VERSION.txt"
        if [ -f "$filename" ]; then
            pip install -r "$filename"
            return 0
        fi
    done
    for filename_pattern in "$@"; do
        filename="$PROJECT_DIR/$filename_pattern.txt"
        if [ -f "$filename" ]; then
            pip install -r "$filename"
            return 0
        fi
    done
}

. "${APP_DIR}"/bin/activate
if [ "$CKAN_VERSION" = "2.9" ]; then
    pip install "setuptools>=44.1.0,<71"
fi
install_requirements . dev-requirements requirements-dev
for extension in . `ls -d $SRC_DIR/ckanext-*`; do
    install_requirements $extension requirements pip-requirements
done
pip install -e .
installed_name=$(grep '^\s*name=' setup.py |sed "s|[^']*'\([-a-zA-Z0-9]*\)'.*|\1|")

# Validate that the extension was installed correctly.
if ! pip list | grep "$installed_name" > /dev/null; then echo "Unable to find the extension in the list"; exit 1; fi

. "${APP_DIR}"/bin/process-config.sh
. "${APP_DIR}"/bin/deactivate
