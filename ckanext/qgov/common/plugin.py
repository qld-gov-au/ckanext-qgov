# encoding: utf-8
""" Queensland Government CKAN extension.
This contains a mixture of useful features, such as an anti-CSRF filter,
and site-specific customisations, such as a feedback channel.
"""
import datetime
import json
import os
import random
from logging import getLogger

import ckan.authz as authz
from ckan.common import _, c
from ckan.lib.base import h
import ckan.lib.formatters as formatters
import ckan.logic.auth as logic_auth
from ckan.logic import get_action
from ckan.plugins import implements, SingletonPlugin, IConfigurer, ITemplateHelpers, IActions, IAuthFunctions, IRoutes
import ckan.model as model
from routes.mapper import SubMapper
import requests

import ckanext.qgov.common.anti_csrf as anti_csrf
import ckanext.qgov.common.authenticator as authenticator
import ckanext.qgov.common.urlm as urlm
import ckanext.qgov.common.intercepts as intercepts
from ckanext.qgov.common.stats import Stats

LOG = getLogger(__name__)

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
        dateobj = datetime.datetime.strptime(date_string.split('T')[0], '%Y-%m-%d')
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
                        'msg': _('Related item must have an associated dataset')}
            # check authentication against package
            pkg = context_model.Package.get(dataset_id)
            if not pkg:
                return {'success': False,
                        'msg': _('No package found, cannot check auth.')}

            pkg_dict = {'id': dataset_id}
            authorised = authz.is_authorized('package_update', context, pkg_dict).get('success')
            if not authorised:
                return {'success': False,
                        'msg': _('Not authorised to add a related item to this package.')}

        return {'success': True}

    return {'success': False, 'msg': _('You must be logged in to add a related item')}

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
                authorised = authz.is_authorized('package_update', context, pkg_dict).get('success')
                if authorised:
                    return {'success': True}

            return {'success': False,
                    'msg': _('You do not have permission to update this related item')}
    return {'success': False,
            'msg': _('You must be logged in and have permission to create datasets to update a related item')}

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
        resource = get_action('resource_show')(context, {
            "id":resource_id
        })
        if 'error' not in resource:
            return resource.get('url')
    except:
        return ''

def generate_json_schema(package_id, validation_schema):
    """ Retrieve the validation schema for a package, if any.
    """
    validation_schema_url = generate_download_url(package_id, validation_schema)
    req = requests.get(validation_schema_url, verify=False)
    if req.status_code == requests.codes.ok:
        try:
            return json.loads(req.text)
        except:
            return {"error": "Failed to parse json schema"}
    else:
        return {"error" : "Failed to retrieve json schema"}

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
    implements(ITemplateHelpers, inherit=True)
    implements(IActions, inherit=True)
    implements(IAuthFunctions, inherit=True)
    implements(IRoutes, inherit=True)

    def __init__(self, **kwargs):
        """ Monkey-patch functions that don't have standard extension
        points.
        """
        anti_csrf.intercept_csrf()
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()

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

        #configure URL Management system through Config or JSON
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

        if ckan_config.get('ckan.base_templates_folder', None) == 'templates-bs2':
            from ckan.lib.helpers import Page
            Page.pager = legacy_pager
        return ckan_config

    def before_map(self, route_map):
        """ Add some custom routes for Queensland Government portals.
        """
        with SubMapper(route_map, controller='ckanext.qgov.common.controller:QGOVController') as mapper:
            mapper.connect('article', '/article/{path:[-_a-zA-Z0-9/]+}', action='static_content')
            mapper.connect('submit_feedback', '/api/action/submit_feedback', action='submit_feedback')
            return route_map

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

    def get_actions(self):
        """Extend actions API
        """
        return {
            'user_update': intercepts.user_update
        }

    def get_auth_functions(self):
        """ Override the 'related' auth functions with our own.
        """
        return {
            'related_create': related_create,
            'related_update' : related_update
        }
