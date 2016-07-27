import os, random, re
from logging import getLogger

from ckan.lib.base import h
import ckan.lib.formatters as formatters
import ckan.logic.validators as validators
from ckan.plugins import implements, SingletonPlugin, IConfigurer, IRoutes, ITemplateHelpers
import datetime

from ckanext.qgov.common.stats import Stats
import anti_csrf, authenticator, urlm, intercepts

LOG = getLogger(__name__)

def random_tags():
    tags = h.unselected_facet_items('tags', limit=15)
    random.shuffle(tags)
    return tags

def format_resource_filesize(size):
    return formatters.localised_filesize(int(size))

def group_id_for(group_name):
    import ckan.model as model
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
    from ckan.lib.navl.dictization_functions import Missing
    from pylons import config
    from pylons.i18n import _

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

class QGOVPlugin(SingletonPlugin):
    """Apply custom functions for Queensland Government portals.

    ``IConfigurer`` allows us to add/modify configuration options.
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    """
    implements(IConfigurer, inherit=True)
    implements(IRoutes, inherit=True)
    implements(ITemplateHelpers, inherit=True)

    def __init__(self, **kwargs):
        validators.user_password_validator = user_password_validator
        anti_csrf.intercept_csrf()
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()

    def update_config(self, config):
        """Use our custom list of licences, and disable some unwanted features
        """

        here = os.path.dirname(__file__)
        config['licenses_group_url'] = 'file://'+os.path.join(here, 'resources', 'qgov-licences.json')
        config['ckan.template_title_deliminater'] = '|'

        # block unwanted content
        config['openid_enabled'] = False

        # configure URL Management system
        urlm_path = config.get('urlm.app_path', None)
        if urlm_path:
            urlm_proxy = config.get('urlm.proxy', None)
            urlm.configure_urlm(urlm_path, urlm_proxy)
        else:
            urlm.configure_for_environment(config.get('ckan.site_url', ''))
        return config

    def before_map(self, routeMap):
        """ Use our custom controller, and disable some unwanted URLs
        """
        controller = 'ckanext.qgov.common.controller:QGOVController'
        routeMap.connect('/storage/upload_handle', controller=controller, action='upload_handle')
        routeMap.connect('/static-content/{path:[-_a-zA-Z0-9/]+}', controller=controller, action='static_content')

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
