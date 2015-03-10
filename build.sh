#!/bin/sh

install () {
    echo "Deploying $1 to local Apache instance..."
    . /usr/lib/ckan/bin/activate
    easy_install "$1"
    sudo apachectl graceful
}

if [ "$1" = "check" ]; then
    . /usr/lib/ckan/bin/activate
    pip install pyflakes pylint
    python -m pyflakes ckanext-qgov
    python -m pylint ckanext
    exit
fi

VERSION=$1
if [ "$1" = "install" ]; then
    VERSION=$2
fi
if [ "$VERSION" = "" ]; then
    VERSION=0.0.1
fi
ARTIFACT=ckanext_qgov-$VERSION-py2.7.egg

echo "Building CKAN extension..."
python setup.py build -f

echo "Packaging CKAN extension..."
cp setup.py setup.py.bak
sed -i -e "s/@BUILD-LABEL@/$VERSION/" setup.py
python setup.py bdist_egg --skip-build --dist-dir=target

echo "Cleaning up..."
mv setup.py.bak setup.py
rm -rf build

if [ "$1" = "install" -o "$2" = "all" ]; then
    install target/$ARTIFACT
fi

