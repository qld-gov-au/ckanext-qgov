#!/bin/sh

USAGE="Usage: $(basename $0) (build|install|clean|all) [VERSION] [CLEAN_INSTANCE]
       examples-
       $(basename $0) build               # Builds egg version 0.0.1
       $(basename $0) build 0.0.2               # Builds target egg version 0.0.2
       $(basename $0) install               # Build and install egg with version 0.0.1
       $(basename $0) install 0.0.2              # Build and install egg with version 0.0.2
       $(basename $0) clean 0.0.1 epub   #Clean and build instance epub with version 0.0.1
       $(basename $0) all 0.0.1 data  #Clean, build and install instance epub with version 0.0.1"

if [ $# -lt 1 ]; then
  echo "${USAGE}" 1>&2
  exit 1
fi

if [ "$1" = "clean" -o "$1" = "all" ]; then
  if [ $# -lt 3 ]; then
      echo "${USAGE}" 1>&2
      exit 1
  fi
fi

. /usr/lib/ckan/default/bin/activate

clean () {
  echo "Restarting Apache2 to clear existing sessions..."
  sudo apache2ctl graceful
  echo "Stopping SOLR search server..."
  sudo service jetty stop
  echo "Purging SOLR cache..."
  sudo -u jetty rm -rf /var/lib/solr/data
  echo "Starting SOLR search server..."
  sudo service jetty start

  echo "Purging database ckan_$INSTANCE..."
  sudo -u postgres dropdb ckan_$INSTANCE
  sudo -u postgres dropdb ckan_${INSTANCE}_datastore
  sudo -u postgres createdb -O ckanuser ckan_$INSTANCE
  sudo -u postgres createdb -O ckanuser ckan_${INSTANCE}_datastore

  echo "Rebuilding $INSTANCE..."
  svn up ~/.babushka/deps
  babushka $INSTANCE

  echo "Creating test data..."
  paster --plugin=ckan create-test-data search -c /etc/ckan/$INSTANCE/$INSTANCE.ini

  echo "Rebuilding SOLR search index..."
  paster --plugin=ckan search-index rebuild -c /etc/ckan/$INSTANCE/$INSTANCE.ini
}

unit_test () {
  echo "Running tests..."
  (cd ckanext/qgov/common && python -m unittest test_anti_csrf) || exit 1
}

install () {
    echo "Deploying $1 to local Apache instance..."
    easy_install "$1"
    sudo apachectl graceful
}

if [ "$1" = "check" ]; then
    pip install pyflakes pylint
    python -m pyflakes ckanext
    python -m pylint ckanext
    exit
fi

if [ "$1" = "test" ]; then
    unit_test
    exit $?
fi

if [ "$1" = "build" -o "$1" = "install" ]; then
    VERSION=$2
fi
if [ "$1" = "clean" -o "$1" = "all" ]; then
    VERSION=$2
    INSTANCE=$3
    if [ "$INSTANCE" = "" ]; then
        echo "${USAGE}" 1>&2
        exit 1
    fi
    clean
fi
if [ "$VERSION" = "" ]; then
    VERSION=0.0.1
fi

unit_test || exit 1

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
