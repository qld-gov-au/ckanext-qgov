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
