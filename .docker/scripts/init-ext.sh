#!/usr/bin/env sh
##
# Install current extension.
#
set -e

install_requirements () {
    PROJECT_DIR="$1"
    for filename in requirements-$PYTHON_VERSION.txt requirements.txt pip-requirements.txt; do
        if [ -f "$PROJECT_DIR/$filename" ]; then
            pip install -r "$PROJECT_DIR/$filename"
            return 0
        fi
    done
}

install_dev_requirements () {
    PROJECT_DIR="$1"
    for filename in dev-requirements-$PYTHON_VERSION.txt requirements-dev-$PYTHON_VERSION.txt requirements-dev.txt dev-requirements.txt; do
        if [ -f "$PROJECT_DIR/$filename" ]; then
            pip install -r "$PROJECT_DIR/$filename"
            return 0
        fi
    done
}

if [ "$VENV_DIR" != "" ]; then
  . ${VENV_DIR}/bin/activate
fi
install_dev_requirements .
for extension in . `ls $VENV_DIR/src/ckanext-*`; do
    install_requirements $extension
done
python setup.py develop
installed_name=$(grep '^\s*name=' setup.py |sed "s|[^']*'\([-a-zA-Z0-9]*\)'.*|\1|")

# Validate that the extension was installed correctly.
if ! pip list | grep "$installed_name" > /dev/null; then echo "Unable to find the extension in the list"; exit 1; fi

if [ "$VENV_DIR" != "" ]; then
  deactivate
fi
