Version 1.1
#ckanext-qgov - Queensland Government CKAN Extensions


#About
Queensland Government has developed this plugin to be used with data.qld.gov.au and publications.qld.gov.au. The plugin has had Queensland Government site specific functionality removed from it.

#Features
* Static Routing on all index.html found in static-content directory
* CSRF Protection
* File upload known type verification
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

#QGOVONLY
extra_public_paths = /srv/data/public
extra_template_paths = /srv/data/templates
```
