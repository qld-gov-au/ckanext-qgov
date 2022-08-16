[![Tests](https://github.com/qld-gov-au/ckan-ex-qgov/actions/workflows/test.yml/badge.svg)](https://github.com/qld-gov-au/ckan-ex-qgov/actions/workflows/test.yml)
============
ckanext-qgov - Queensland Government CKAN Extensions
============


#About
Queensland Government has developed this plugin to be used with data.qld.gov.au and publications.qld.gov.au. The plugin has had Queensland Government site specific functionality removed from it.

#Features
* Static Routing on all index.html found in static-content directory
* CSRF Protection
* Restrict access to user APIs; only admins should be able to view profiles other than their own
* Resource URL filtering (domain whitelist/blacklist)
* Statistics helpers
* Custom feedback route
* Password Strength validator
* Account locking on incorrect password
* Custom 404 Handler

#Requirements
* None

#Configuration
```
ckan.plugins = qgovext

urlm.app_path = https://www.404redirect.qld.gov.au/services/url
urlm.proxy = proxy:3128
feedback_form_recipients = myemail@gmail.com,otheremail@gov.au
feedback_redirection = /article/thanks
ckan.mimetypes_allowed = *

```

# Development

The 'develop' branch is automatically pushed to dev.data.qld.gov.au and dev.publications.qld.gov.au.

The 'master' branch is automatically pushed to test-dev.data.qld.gov.au.

For deploying to higher environments, releases should be tagged and updated in the CloudFormation templates.

## Installation

* Activate your virtual environment
```
. /usr/lib/ckan/default/bin/activate
```
* Install the extension
```
pip install 'git+https://github.com/qld-gov-au/ckanext-qgov.git#egg=ckanext-qgov'
```
> **Note**: If you prefer, you can download the source code as well and install in 'develop' mode for easy editing. To do so, use the '-e' fla
g:
> ```
> pip install -e 'git+https://github.com/qld-gov-au/ckanext-qgov.git#egg=ckanext-qgov'
> ```

* Modify your configuration file (generally in `/etc/ckan/default/production.ini`) and add `qgovext` in the `ckan.plugins` property.
```
ckan.plugins = qgovext <OTHER_PLUGINS>
```

## Tests

- Make sure that you have latest versions of all required software installed:
  - [Docker](https://www.docker.com/)
  - [Pygmy](https://pygmy.readthedocs.io/)
  - [Ahoy](https://github.com/ahoy-cli/ahoy)

- Build the test container for your preferred CKAN version: '2.8', '2.9-py2', or '2.9'.
```
CKAN_VERSION=2.9 .circleci/build.sh
```

- Run tests: `.circleci/test.sh`
