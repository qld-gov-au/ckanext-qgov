# H1 ckanext-qgov - Queensland Government CKAN Extensions

# H2 About
Queensland Government has developed this plugin to be used with data.qld.gov.au and publications.qld.gov.au. The plugin has had Queensland Government site specific functionality removed from it.

# H2 Features
* Static Routing on all index.html found in static-content directory
* CSRF Protection
* File upload known type verification
* Statistics helpers
* Custom feedback route
* Password Strength validator
* Account locking on incorrect password

# H2 Requirements
* None

# H2 Configuration
```
ckan.plugins = qgov
contact_form_url = https://my_feedback_service.com

```


