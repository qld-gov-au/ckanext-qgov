import os, random, re
from logging import getLogger
from ckan.lib.base import h
import ckan.lib.formatters as formatters
import ckan.logic.validators as validators
from ckan.plugins import implements, SingletonPlugin, IConfigurer, IRoutes, ITemplateHelpers,IActions 
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.dictization_functions import Missing
from pylons import config
from pylons.i18n import _
import datetime
from ckanext.qgov.common.stats import Stats
import anti_csrf, authenticator, urlm, intercepts
import ckan.model as model
import requests
from ckan.logic.action.get import package_show
from pylons.controllers.util import abort

LOG = getLogger(__name__)

def random_tags():
    tags = h.unselected_facet_items('tags', limit=15)
    random.shuffle(tags)
    return tags

def format_resource_filesize(size):
    return formatters.localised_filesize(int(size))

def group_id_for(group_name):

    group = model.Group.get(group_name)

    if group and group.is_active():
        return group.id
    else:
        LOG.error("%s group was not found or not active", group_name)
        return None

def format_attribution_date(date_string=None):
    if date_string:
        return datetime.datetime.strptime(date_string.split('T')[0],'%Y-%m-%d').strftime('%d %B %Y')
    else:
        return datetime.datetime.now().strftime('%d %B %Y')

def user_password_validator(key, data, errors, context):
    password_min_length = int(config.get('password_min_length', '10'))
    password_patterns = config.get('password_patterns', r'.*[0-9].*,.*[a-z].*,.*[A-Z].*,.*[-`~!@#$%^&*()_+=|\\/ ].*').split(',')

    value = data[key]

    if value is None or value == '' or isinstance(value, Missing):
        raise ValueError(_('You must provide a password'))
    if not len(value) >= password_min_length:
        errors[('password',)].append(_('Your password must be {min} characters or longer'.format(min=password_min_length)))
    for policy in password_patterns:
        if not re.search(policy, value):
            errors[('password',)].append(_('Must contain at least one number, lowercase letter, capital letter, and symbol'))

@toolkit.side_effect_free
def submit_feedback(context,data_dict=None):
    controller = 'ckanext.qgov.data.controller:QGOVDataController'
    protocol, host = h.get_site_protocol_and_host()
    full_current_url = h.full_current_url()

    if protocol is not None and host is not None and host in full_current_url:
        url = config.get('contact_form_url', '')
        if url.strip() != '':
            package = package_show(context,data_dict)
            if 'error' not in package:
                if 'name' not in data_dict:
                    data_dict['name'] = 'Not provided'
                if 'email' not in data_dict:
                    data_dict['email'] = 'Not provided'
                if 'comments' not in data_dict:
                    data_dict['comments'] = 'Not provided'

                form_data = {
                    'feedback_email' : package['maintainer_email'],
                    'feedback_organisation' : package['organization']['title'],
                    'feedback_dataset' : package['title'],
                    'feedback_origins' : full_current_url,
                    'name' : data_dict['name'],
                    'email' : data_dict['email'],
                    'comments' : data_dict['comments']
                }

                if '/resource/' in full_current_url:
                    form_data['feedback_resource'] = full_current_url.split('/resource/')[1]

                r = requests.post(url, data=form_data)
                if r.status_code == requests.codes.ok:
                    try:
                        h.url_for(controller=controller,action='thanks')
                        h.redirect_to(controller=controller, action='thanks')
                    except:
                        h.redirect_to('/')
                else:
                    abort(404, 'This form submission is invalid.')
            return package
        else:
            abort(404,'No URL provided')
    else:
        abort(404, 'Invalid request source')

class QGOVPlugin(SingletonPlugin):
    """Apply custom functions for Queensland Government portals.

    ``IConfigurer`` allows us to add/modify configuration options.
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    """
    implements(IConfigurer, inherit=True)
    implements(IRoutes, inherit=True)
    implements(ITemplateHelpers, inherit=True)
    implements(IActions, inherit=True)

    def __init__(self, **kwargs):
        validators.user_password_validator = user_password_validator
        anti_csrf.intercept_csrf()
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()

    def update_config(self, ckan_config):
        """Use our custom list of licences, and disable some unwanted features
        """
        ckan_config['ckan.template_title_deliminater'] = '|'
        here = os.path.dirname(__file__)

        #If path to qgov-licences exists add to path
        possible_licences_path = os.path.join(here, 'resources', 'qgov-licences.json')
        if os.path.isfile(possible_licences_path):
            ckan_config['licenses_group_url'] = 'file://'+ possible_licences_path

        #Theme Inclusions of public and templates
        possible_public_path = os.path.join(here, 'theme/public')
        if os.path.isdir(possible_public_path):
            ckan_config['extra_public_paths'] = possible_public_path + ',' + ckan_config.get('extra_public_paths', '')
        possible_template_path = os.path.join(here, 'theme/templates')
        if os.path.isdir(possible_template_path):
            ckan_config['extra_template_paths'] = possible_template_path + ',' + ckan_config.get('extra_template_paths', '')
        # block unwanted content
        ckan_config['openid_enabled'] = False

        # configure URL Management system
        urlm_path = ckan_config.get('urlm.app_path', None)
        if urlm_path:
            urlm_proxy = ckan_config.get('urlm.proxy', None)
            urlm.configure_urlm(urlm_path, urlm_proxy)
        else:
            urlm.configure_for_environment(ckan_config.get('ckan.site_url', ''))
        return ckan_config

    def before_map(self, routeMap):
        """ Use our custom controller, and disable some unwanted URLs
        """
        controller = 'ckanext.qgov.common.controller:QGOVController'
        routeMap.connect('/storage/upload_handle', controller=controller, action='upload_handle')
        routeMap.connect('/article/{path:[-_a-zA-Z0-9/]+}', controller=controller, action='static_content')

        return routeMap

    def get_helpers(self):
        """ A dictionary of extra helpers that will be available
        to provide QGOV-specific helpers to the templates.
        """
        helper_dict = {}
        helper_dict['top_organisations'] = Stats.top_organisations
        helper_dict['top_categories'] = Stats.top_categories
        helper_dict['resource_count'] = Stats.resource_count
        helper_dict['resource_report'] = Stats.resource_report
        helper_dict['resource_org_count'] = Stats.resource_org_count
        helper_dict['random_tags'] = random_tags
        helper_dict['format_resource_filesize'] = format_resource_filesize
        helper_dict['group_id_for'] = group_id_for
        helper_dict['format_attribution_date'] = format_attribution_date

        return helper_dict

    def get_actions(self):
        """Extend actions API
        """
        return {
            'submit_feedback' : submit_feedback
        }
