# encoding: utf-8
import os, random, re
from logging import getLogger
import ckan.lib.base as base
from ckan.lib.base import h
import ckan.authz as authz
from routes.mapper import SubMapper
import ckan.lib.formatters as formatters
import ckan.logic.validators as validators
import ckan.logic.auth as logic_auth
from ckan.logic import get_action
from ckan.plugins import implements, SingletonPlugin, IConfigurer, IBlueprint, ITemplateHelpers,IActions,IAuthFunctions,IRoutes
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.dictization_functions import Missing
from ckan.common import config, _
import ckan.model as model
from ckan import __version__
from ckan.common import _ as __, g, c
from flask import Blueprint
import datetime
from ckanext.qgov.common.stats import Stats
import anti_csrf, authenticator, urlm, intercepts
import requests
from flask import abort
import json

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

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, basestring):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif not len(value) >= password_min_length:
        errors[('password',)].append(__('Your password must be {min} characters or longer'.format(min=password_min_length)))
    else:
        for policy in password_patterns:
            if not re.search(policy, value):
                errors[('password',)].append(__('Must contain at least one number, lowercase letter, capital letter, and symbol'))

def related_create(context, data_dict=None):
    '''
    Override default related_create so;
    - Users must be logged-in to create related items
    - Related item must be created for an associated dataset
    - User must be able to create datasets (proves privilege)

    Note: This function is used to both gain entry to the 'Create' form and validate the 'Create' form
    '''
    model = context['model']
    user = context['user']
    userobj = model.User.get( user )

    check1 = all(authz.check_config_permission(p) for p in (
        'create_dataset_if_not_in_organization',
        'create_unowned_dataset',
    )) or authz.has_user_permission_for_some_org(
        user, 'create_dataset')

    if userobj and check1:
        if data_dict is not None and len(data_dict) != 0:
            dataset_id = data_dict.get('dataset_id',None)
            if dataset_id is None or dataset_id == '':
                return {'success': False,
                    'msg': _('Related item must have an associated dataset')}
            # check authentication against package
            pkg = model.Package.get(dataset_id)
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
    model = context['model']
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
            'msg': _('You must be logged in and permission to create datasets to update a related item')}

def get_validation_resources(data_dict):
    context = {'ignore_auth': False, 'model': model,
               'user': c.user or c.author}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources',[])
        validation_schemas = []
        for resource in resources:
            if resource['format'].upper() == 'CSV VALIDATION SCHEMA':
                validation_schemas.append(resource['id'])
        return validation_schemas
    return package

def get_resource_name(data_dict):
    context = {'ignore_auth': False, 'model': model,
               'user': c.user or c.author}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources',[])
        for resource in resources:
            if data_dict['resource_id'] == resource['id']:
                return resource['name']
        return None
    return None

def generate_download_url(package_id,resource_id):
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

def generate_json_schema(package_id,validation_schema):
    validation_schema_url = generate_download_url(package_id,validation_schema)
    r = requests.get(validation_schema_url,verify=False)
    if r.status_code == requests.codes.ok:
        try:
            return json.loads(r.text)
        except:
            return { "error": "Failed to parse json schema"}
    else:
        return { "error" : "Failed to retrieve json schema"}

def legacy_pager(self, *args, **kwargs):
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
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    """
    implements(IConfigurer, inherit=True)
    implements(ITemplateHelpers, inherit=True)
    implements(IActions, inherit=True)
    implements(IAuthFunctions, inherit=True)
    implements(IRoutes, inherit=True)

    def __init__(self, **kwargs):
        validators.user_password_validator = user_password_validator
        anti_csrf.intercept_csrf()
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()

    def update_config_schema(self, schema):
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
                    urlm_url = urlm_json[hostname].get('url','')
                    urlm_proxy = urlm_json[hostname].get('proxy',None)
                    urlm.configure_urlm(urlm_url,urlm_proxy)

        if 'ckan.base_templates_folder' in ckan_config and ckan_config['ckan.base_templates_folder'] == 'templates-bs2':
            from ckan.lib.helpers import Page
            Page.pager = legacy_pager
        return ckan_config

    def static_content(self, path):
        try:
            return render('static-content/{path}/index.html'.format(path=path))
        except TemplateNotFound:
            LOG.warn(path + " not found")
            base.abort(404)

    def before_map(self, map):
        # These named routes are used for custom dataset forms which will use
        # the names below based on the dataset.type ('dataset' is the default
        # type)
        with SubMapper(map, controller='ckanext.qgov.common.controller:QGOVController') as m:
            m.connect('article', '/article/{path:[-_a-zA-Z0-9/]+}', action='static_content')
            m.connect('submit_feedback', '/api/action/submit_feedback', action='submit_feedback')
            return map

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
        return {
            'related_create': related_create,
            'related_update' : related_update
        }
