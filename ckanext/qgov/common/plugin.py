# encoding: utf-8
""" Queensland Government CKAN extension.
This contains a mixture of useful features, such as an anti-CSRF filter,
and site-specific customisations, such as a feedback channel.
"""
import datetime
import json
from logging import getLogger
import os
import random
import re
import socket
import urlparse

from ckan import authz, model
from ckan.common import _, c
from ckan.lib.base import h
from ckan.lib import formatters
import ckan.lib.navl.dictization_functions as df
import ckan.logic.auth as logic_auth
from ckan.logic import get_action
from ckan.plugins import implements, toolkit, SingletonPlugin, IConfigurer,\
    ITemplateHelpers, IActions, IAuthFunctions, IRoutes, IConfigurable,\
    IValidators
from routes.mapper import SubMapper
import requests
from paste.deploy.converters import asbool

import authenticator
import urlm
import intercepts
from ckanext.qgov.common.stats import Stats

LOG = getLogger(__name__)

IP_ADDRESS = re.compile(r'^({0}[.]){{3}}{0}$'.format(r'[0-9]{1,3}'))
PRIVATE_IP_ADDRESS = re.compile(r'^((1?0|127)([.]{0}){{3}}|(172[.](1[6-9]|2[0-9]|3[01])|169[.]254)([.]{0}){{2}}|192[.]168([.]{0}){{2}})$'.format(r'[0-9]{1,3}'))


def random_tags():
    """ Show the most-used tags in a random order.
    """
    tags = h.unselected_facet_items('tags', limit=15)
    random.shuffle(tags)
    return tags


def format_resource_filesize(size):
    """ Show a file size, formatted for humans.
    """
    return formatters.localised_filesize(int(size))


def group_id_for(group_name):
    """ Determine the ID for a provided group name, if any.
    """
    group = model.Group.get(group_name)

    if group and group.is_active():
        return group.id

    LOG.error("%s group was not found or not active", group_name)
    return None


def format_attribution_date(date_string=None):
    """ Format a date nicely.
    """
    if date_string:
        dateobj = datetime.datetime.strptime(date_string.split('T')[0],
                                             '%Y-%m-%d')
    else:
        dateobj = datetime.datetime.now()
    return dateobj.strftime('%d %B %Y')


def related_create(context, data_dict=None):
    '''
    Override default related_create so;
    - Users must be logged-in to create related items
    - Related item must be created for an associated dataset
    - User must be able to create datasets (proves privilege)

    Note: This function is used both to gain entry to the 'Create' form
    and to validate the 'Create' form
    '''
    context_model = context['model']
    user = context['user']
    userobj = context_model.User.get(user)

    check1 = all(authz.check_config_permission(p) for p in (
        'create_dataset_if_not_in_organization',
        'create_unowned_dataset',
    )) or authz.has_user_permission_for_some_org(
        user, 'create_dataset')

    if userobj and check1:
        if data_dict:
            dataset_id = data_dict.get('dataset_id', None)
            if dataset_id is None or dataset_id == '':
                return {'success': False,
                        'msg': _('''Related item must have
                                    an associated dataset''')}
            # check authentication against package
            pkg = context_model.Package.get(dataset_id)
            if not pkg:
                return {'success': False,
                        'msg': _('No package found, cannot check auth.')}

            pkg_dict = {'id': dataset_id}
            authorised = authz.is_authorized(
                'package_update',
                context,
                pkg_dict).get('success')
            if not authorised:
                return {'success': False,
                        'msg': _('''Not authorised to add a related item
                                    to this package.''')}

        return {'success': True}

    return {'success': False,
            'msg': _('You must be logged in to add a related item')}


def related_update(context, data_dict):
    '''
    Override default related_update so;
    - Users must be logged-in to create related items
    - User can update if they are able to create datasets for housed package
    '''
    user = context['user']

    check1 = all(authz.check_config_permission(p) for p in (
        'create_dataset_if_not_in_organization',
        'create_unowned_dataset',
    )) or authz.has_user_permission_for_some_org(
        user, 'create_dataset')

    if user and check1:
        related = logic_auth.get_related_object(context, data_dict)
        if related.datasets:
            for package in related.datasets:
                pkg_dict = {'id': package.id}
                authorised = authz.is_authorized(
                    'package_update',
                    context,
                    pkg_dict).get('success')
                if authorised:
                    return {'success': True}

            return {'success': False,
                    'msg': _('''You do not have permission
                                to update this related item''')}
    return {'success': False,
            'msg': _('''You must be logged in and have permission
                        to create datasets to update a related item''')}


def auth_user_list(context, data_dict=None):
    """Check whether access to the user list is authorised.
    Restricted to organisation admins as per QOL-5710.
    """
    return {'success': _requester_is_admin(context)}


def auth_user_show(context, data_dict):
    """Check whether access to individual user details is authorised.
    Restricted to organisation admins or self, as per QOL-5710.
    """
    if _requester_is_admin(context):
        return {'success': True}
    requester = context.get('user')
    id = data_dict.get('id', None)
    if id:
        user_obj = model.User.get(id)
    else:
        user_obj = data_dict.get('user_obj', None)
    if user_obj:
        return {'success': requester == user_obj.name}

    return {'success': False}


@toolkit.auth_allow_anonymous_access
def auth_group_show(context, data_dict):
    """Check whether access to a group is authorised.
    If it's just the group metadata, this requires no privileges,
    but if user details have been requested, it requires a group admin.
    """
    user = context.get('user')
    group = logic_auth.get_group_object(context, data_dict)
    if group.state == 'active' and \
        not asbool(data_dict.get('include_users', False)) and \
            data_dict.get('object_type', None) != 'user':
        return {'success': True}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if authorized:
        return {'success': True}
    else:
        return {'success': False,
                'msg': _('User %s not authorized to read group %s') % (user, group.id)}


def _requester_is_admin(context):
    """Check whether the current user has admin privileges in some group
    or organisation.
    This is based on the 'update' privilege; see eg
    ckan.logic.auth.update.group_edit_permissions.
    """
    requester = context.get('user')
    return _has_user_permission_for_some_group(requester, 'admin')


def _has_user_permission_for_some_group(user_name, permission):
    """Check if the user has the given permission for any group.
    """
    user_id = authz.get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    roles = authz.get_roles_with_permission(permission)

    if not roles:
        return False
    # get any groups the user has with the needed role
    q = model.Session.query(model.Member) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.capacity.in_(roles)) \
        .filter(model.Member.table_id == user_id)
    group_ids = []
    for row in q.all():
        group_ids.append(row.group_id)
    # if not in any groups has no permissions
    if not group_ids:
        return False

    # see if any of the groups are active
    q = model.Session.query(model.Group) \
        .filter(model.Group.state == 'active') \
        .filter(model.Group.id.in_(group_ids))

    return bool(q.count())


def get_validation_resources(data_dict):
    """ Return the validation schemas associated with a package.
    """
    context = {'ignore_auth': False, 'model': model,
               'user': c.user or c.author}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources', [])
        validation_schemas = []
        for resource in resources:
            if resource['format'].upper() == 'CSV VALIDATION SCHEMA':
                validation_schemas.append(resource['id'])
        return validation_schemas
    return package


def get_resource_name(data_dict):
    """ Retrieve the name of a resource given its ID.
    """
    context = {'ignore_auth': False, 'model': model,
               'user': c.user or c.author}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources', [])
        for resource in resources:
            if data_dict['resource_id'] == resource['id']:
                return resource['name']
        return None
    return None


def generate_download_url(package_id, resource_id):
    """ Construct a URL to download a resource given its ID.
    """
    context = {'ignore_auth': False, 'model': model,
               'user': c.user or c.author}
    try:
        resource = get_action('resource_show')(context, {"id": resource_id})
        if 'error' not in resource:
            return resource.get('url')
    except Exception:
        return ''


def generate_json_schema(package_id, validation_schema):
    """ Retrieve the validation schema for a package, if any.
    """
    validation_schema_url = generate_download_url(package_id,
                                                  validation_schema)
    req = requests.get(validation_schema_url, verify=False)
    if req.status_code == requests.codes.ok:
        try:
            return json.loads(req.text)
        except Exception:
            return {"error": "Failed to parse json schema"}
    else:
        return {"error": "Failed to retrieve json schema"}


def legacy_pager(self, *args, **kwargs):
    """ Construct a paging object suitable for Bootstrap 2.
    See https://github.com/ckan/ckan/issues/4895
    """
    kwargs.update(
        format=u"<div class='pagination-wrapper pagination'><ul>"
        "$link_previous ~2~ $link_next</ul></div>",
        symbol_previous=u'«', symbol_next=u'»',
        curpage_attr={'class': 'active'}, link_attr={}
    )
    from ckan.lib.helpers import Page
    return super(Page, self).pager(*args, **kwargs)


def valid_url(key, flattened_data, errors, context):
    """ Check whether the value is a valid URL.

    As well as checking syntax, this requires the URL to match one of the
    permitted protocols, unless it is an upload.
    """
    value = flattened_data[key]
    if not value or h.is_url(value) or _is_upload(key, flattened_data):
        return

    value = 'http://{}'.format(value)
    if not h.is_url(value):
        raise df.Invalid(_('Must be a valid URL'))
    flattened_data[key] = value


def _is_upload(key, flattened_data):
    url_type_key = list(key)
    url_type_key[2] = 'url_type'
    url_type_key = tuple(url_type_key)
    url_type = flattened_data.get(url_type_key, None)
    return url_type == 'upload'


def valid_resource_url(key, flattened_data, errors, context):
    """ Check whether the resource URL is permitted.

    This requires either an uploaded file, or passing any configured
    whitelist/blacklist checks.
    """

    valid_url(key, flattened_data, errors, context)
    value = flattened_data[key]
    if not value or _is_upload(key, flattened_data):
        LOG.debug("No resource URL found, or file is uploaded; skipping check")
        return

    if not RESOURCE_WHITELIST and not RESOURCE_BLACKLIST:
        LOG.debug("No whitelist or blacklist found; skipping URL check")
        return

    # parse our URL so we can extract the domain
    resource_url = urlparse.urlparse(value)
    if not resource_url:
        LOG.warn("Invalid resource URL")
        raise df.Invalid(_('Must be a valid URL'))

    LOG.debug("Requested resource domain is %s", resource_url.hostname)
    if not resource_url.hostname:
        raise df.Invalid(_('Must be a valid URL'))

    address_resolution = _resolve_address(resource_url.hostname)
    # reject the URL if it matches any blacklist entry
    if RESOURCE_BLACKLIST:
        for domain in RESOURCE_BLACKLIST:
            if _domain_match(resource_url.hostname, domain, address_resolution):
                raise df.Invalid(_('Domain is blocked'))

    # require the URL to match a whitelist entry, if applicable
    if RESOURCE_WHITELIST:
        for domain in RESOURCE_WHITELIST:
            if _domain_match(resource_url.hostname, domain, address_resolution):
                return
        raise df.Invalid(_('Must be from an allowed domain: {}').format(RESOURCE_WHITELIST))

    return


def _domain_match(hostname, pattern, address_resolution):
    """ Test whether 'hostname' matches the pattern.

    Note that this is not a regex match, but subdomains are allowed.
    Alternatively, 'pattern' can be an IP address, in which case,
    this tests whether 'hostname' can resolve to that IP address.

    If the pattern is 'private', then all private IP addresses are matched.
    This includes:
    0.x.x.x
    10.x.x.x
    127.x.x.x
    169.254.x.x
    172.16.0.0 to 172.31.255.255
    192.168.x.x
    """

    if pattern == 'private':
        if PRIVATE_IP_ADDRESS.match(hostname):
            return True

        if not address_resolution:
            # couldn't resolve hostname, nothing further to do
            return False

        ipaddrlist = address_resolution[2]
        for ipaddr in ipaddrlist:
            if PRIVATE_IP_ADDRESS.match(ipaddr):
                LOG.debug("%s can resolve to %s which is private",
                          hostname, ipaddrlist)
                return True

    elif IP_ADDRESS.match(pattern):
        if hostname == pattern:
            return True

        if not address_resolution:
            # couldn't resolve hostname, nothing further to do
            return False

        ipaddrlist = address_resolution[2]
        if pattern in ipaddrlist:
            LOG.debug("%s can resolve to %s which includes %s",
                      hostname, ipaddrlist, pattern)
            return True

    else:
        if _is_subdomain(hostname, pattern):
            return True

        if not address_resolution:
            # couldn't resolve hostname, nothing further to do
            return False

        resolved_hostname = address_resolution[0]
        if _is_subdomain(resolved_hostname, pattern):
            return True
        aliaslist = address_resolution[1]
        for alias in aliaslist:
            if _is_subdomain(alias, pattern):
                return True

    return False


def _resolve_address(hostname):
    """ Perform a DNS resolution on a hostname.
    If successful, return a tuple containing the resolved hostname,
    the list of aliases if any, and the list of IP addresses.
    If unsuccessful, return a tuple containing the value False.
    Note that if this tuple is evaluated as a boolean, the result is False.
    """
    try:
        return (socket.gethostbyname_ex(hostname))
    except (socket.gaierror, socket.herror):
        return (False)


def _is_subdomain(hostname, pattern):
    """ Checks whether 'hostname' is equal to 'pattern'
    or is a subdomain of 'pattern'.
    """
    return hostname == pattern or hostname.endswith('.' + pattern)


class QGOVPlugin(SingletonPlugin):
    """Apply custom functions for Queensland Government portals.

    ``IConfigurer`` allows us to add/modify configuration options.
    ``ITemplateHelpers`` lets us add helper functions
    for template rendering.
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    ``IActions`` allows us to add API actions.
    ``IAuthFunctions`` lets us override authorisation checks.
    """
    implements(IConfigurer, inherit=True)
    implements(IConfigurable, inherit=True)
    implements(ITemplateHelpers, inherit=True)
    implements(IActions, inherit=True)
    implements(IAuthFunctions, inherit=True)
    implements(IRoutes, inherit=True)
    implements(IValidators, inherit=True)

    # IConfigurer

    def update_config_schema(self, schema):
        """ Don't allow customisation of site CSS via the web interface.
        These fields represent a persistent XSS risk.
        """
        schema.pop('ckan.main_css', None)
        schema.pop('ckan.site_custom_css', None)

        return schema

    def update_config(self, ckan_config):
        """Use our custom list of licences, and disable some unwanted features
        """
        ckan_config['ckan.template_title_deliminater'] = '|'
        here = os.path.dirname(__file__)

        # If path to qgov-licences exists add to path
        possible_licences_path = os.path.join(here,
                                              'resources',
                                              'qgov-licences.json')
        if os.path.isfile(possible_licences_path):
            ckan_config['licenses_group_url'] = 'file://' \
                + possible_licences_path

        if 'scheming.presets' in ckan_config:
            # inject our presets before the others so we can override them
            ckan_config['scheming.presets'] = \
                'ckanext.qgov.common:resources/scheming_presets.json ' \
                + ckan_config['scheming.presets']

        # Theme Inclusions of public and templates
        possible_public_path = os.path.join(here, 'theme/public')
        if os.path.isdir(possible_public_path):
            ckan_config['extra_public_paths'] = possible_public_path \
                + ',' + ckan_config.get('extra_public_paths', '')
        possible_template_path = os.path.join(here, 'theme/templates')
        if os.path.isdir(possible_template_path):
            ckan_config['extra_template_paths'] = possible_template_path \
                + ',' + ckan_config.get('extra_template_paths', '')
        # block unwanted content
        ckan_config['openid_enabled'] = False

        # configure URL Management system through Config or JSON
        urlm_path = ckan_config.get('urlm.app_path', None)
        if urlm_path:
            urlm_proxy = ckan_config.get('urlm.proxy', None)
            urlm.configure_urlm(urlm_path, urlm_proxy)
        else:
            possible_urlm_path = os.path.join(here, 'resources', 'urlm.json')
            if os.path.isfile(possible_urlm_path):
                with open(possible_urlm_path) as urlm_file:
                    urlm_json = json.load(urlm_file)
                hostname = h.get_site_protocol_and_host()[1]
                if hostname not in urlm_json:
                    hostname = 'default'

                if hostname in urlm_json:
                    urlm_url = urlm_json[hostname].get('url', '')
                    urlm_proxy = urlm_json[hostname].get('proxy', None)
                    urlm.configure_urlm(urlm_url, urlm_proxy)

        if ckan_config.get('ckan.base_templates_folder',
                           None) == 'templates-bs2':
            from ckan.lib.helpers import Page
            Page.pager = legacy_pager
        return ckan_config

    # IConfigurable

    def configure(self, config):
        """ Monkey-patch functions that don't have standard extension
        points.
        """
        global RESOURCE_WHITELIST
        global RESOURCE_BLACKLIST
        RESOURCE_WHITELIST = config.get('ckanext.qgov.resource_domains.whitelist', '').split()
        RESOURCE_BLACKLIST = config.get('ckanext.qgov.resource_domains.blacklist', 'private').split()
        LOG.info("Resources must come from: %s and cannot come from %s", RESOURCE_WHITELIST, RESOURCE_BLACKLIST)

        intercepts.configure(config)

    # IRoutes
    def before_map(self, route_map):
        """ Add some custom routes for Queensland Government portals.
        """
        controller = 'ckanext.qgov.common.controller:QGOVController'
        with SubMapper(route_map, controller=controller) as mapper:
            mapper.connect('article',
                           '/article/{path:[-_a-zA-Z0-9/]+}',
                           action='static_content')
            mapper.connect('submit_feedback',
                           '/api/action/submit_feedback',
                           action='submit_feedback')
            return route_map

    def after_map(self, route_map):
        """ Add monkey-patches after routing is set up.
        """
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()
        return route_map

    # ITemplateHelpers

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
        helper_dict['get_validation_resources'] = get_validation_resources
        helper_dict['get_resource_name'] = get_resource_name
        helper_dict['generate_download_url'] = generate_download_url
        helper_dict['generate_json_schema'] = generate_json_schema

        return helper_dict

    # IActions

    def get_actions(self):
        """Extend actions API
        """
        return {
            'user_update': intercepts.user_update
        }

    # IAuthFunctions

    def get_auth_functions(self):
        """ Override the 'related' auth functions with our own.
        """
        return {
            'related_create': related_create,
            'related_update': related_update,
            'user_list': auth_user_list,
            'user_show': auth_user_show,
            'group_show': auth_group_show
        }

    # IValidators

    def get_validators(self):
        """ Add URL validators.
        """
        return {
            'valid_url': valid_url,
            'valid_resource_url': valid_resource_url
        }
