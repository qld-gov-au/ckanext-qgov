# encoding: utf-8
""" Queensland Government CKAN extension.
This contains a mixture of useful features, such as an anti-CSRF filter,
and site-specific customisations, such as a feedback channel.
"""

import json
from logging import getLogger
import os
import re

from ckan import plugins
from ckan.lib.base import h
import ckan.lib.navl.dictization_functions as df
from ckan.lib.navl.validators import unicode_safe
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins.toolkit import _, add_template_directory, get_action, \
    get_validator, render

from . import authenticator, auth_functions as auth, helpers, intercepts, urlm
from .stats import Stats
from .user_creation import validators as user_creation_validators
from .user_creation.logic.actions import create as user_creation_create_actions

LOG = getLogger(__name__)

IP_ADDRESS = re.compile(r'^({0}[.]){{3}}{0}$'.format(r'[0-9]{1,3}'))
PRIVATE_IP_ADDRESS = re.compile(r'^((1?0|127)([.]{0}){{3}}|(172[.](1[6-9]|2[0-9]|3[01])|169[.]254)([.]{0}){{2}}|192[.]168([.]{0}){{2}})$'.format(r'[0-9]{1,3}'))


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


class QGOVPlugin(SingletonPlugin):
    """Apply custom functions for Queensland Government portals.

    ``IConfigurer`` allows us to add/modify configuration options.
    ``ITemplateHelpers`` lets us add helper functions
    for template rendering.
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    ``IActions`` allows us to add API actions.
    ``IAuthFunctions`` lets us override authorisation checks.
    """
    implements(plugins.IConfigurer, inherit=True)
    implements(plugins.IConfigurable, inherit=True)
    implements(plugins.ITemplateHelpers, inherit=True)
    implements(plugins.IActions, inherit=True)
    implements(plugins.IAuthFunctions, inherit=True)
    implements(plugins.IValidators, inherit=True)
    implements(plugins.IResourceController, inherit=True)
    implements(plugins.IMiddleware, inherit=True)
    implements(plugins.IBlueprint)
    implements(plugins.ITranslation, inherit=True)

    # IConfigurer

    def update_config_schema(self, schema):
        """ Don't allow customisation of site CSS via the web interface.
        These fields represent a persistent XSS risk.
        """
        schema.pop('ckan.main_css', None)
        schema.pop('ckan.site_custom_css', None)

        ignore_missing = get_validator('ignore_missing')
        schema.update({
            'ckanext.data_qld.excluded_display_name_words': [ignore_missing, unicode_safe]
        })

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

        # include templates
        add_template_directory(ckan_config, 'templates')

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

        return ckan_config

    # IConfigurable

    def configure(self, config):
        """ Monkey-patch functions that don't have standard extension
        points.
        """
        authenticator.intercept_authenticator()
        intercepts.configure(config)
        intercepts.set_intercepts()

    # IMiddleware

    def make_middleware(self, app, config):
        if hasattr(app, 'errorhandler'):
            @app.errorhandler(404)
            def handle_not_found(e):
                from flask import redirect, request, get_flashed_messages
                redirect_url = urlm.get_purl_response(request.base_url)
                if redirect_url:
                    # eat the 'page not found' message as it's obsolete
                    get_flashed_messages()
                    return redirect(redirect_url, 301)
                else:
                    # copy default error handling
                    extra_vars = {
                        u'code': e.code,
                        u'content': e.description,
                        u'name': e.name
                    }

                    return render(u'error_document_template.html', extra_vars), e.code
        return app

    # IBlueprint
    def get_blueprint(self):
        """
        CKAN uses Flask Blueprints in the /ckan/views dir for user and dashboard
        Here we override some routes to redirect unauthenticated users to the login page, and only redirect the
        user to the `came_from` URL if they are logged in.
        :return:
        """
        from .views import user, assets
        blueprints = user.get_blueprints()
        blueprints.extend(assets.get_blueprints())
        return blueprints

    # ITemplateHelpers

    def get_helpers(self):
        """ A dictionary of extra helpers that will be available
        to provide QGOV-specific helpers to the templates.
        """
        return {
            'top_organisations': Stats.top_organisations,
            'top_categories': Stats.top_categories,
            'resource_count': Stats.resource_count,
            'resource_report': Stats.resource_report,
            'resource_org_count': Stats.resource_org_count,
            'random_tags': helpers.random_tags,
            'format_resource_filesize': helpers.format_resource_filesize,
            'group_id_for': helpers.group_id_for,
            'format_attribution_date': helpers.format_attribution_date,
            'get_validation_resources': helpers.get_validation_resources,
            'get_resource_name': helpers.get_resource_name,
            'generate_download_url': helpers.generate_download_url,
            'generate_json_schema': helpers.generate_json_schema,
            'data_qld_organisation_list': helpers.organisation_list,
            'data_qld_user_has_admin_access': helpers.user_has_admin_access,
            'data_qld_format_activity_data': helpers.format_activity_data,
            'activity_type_nice': helpers.activity_type_nice,
        }

    # IActions

    def get_actions(self):
        """Extend actions API
        """
        return {
            'user_show': intercepts.user_show,
            'user_update': intercepts.user_update,
            'user_create': user_creation_create_actions.user_create,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        """ Override the 'related' auth functions with our own.
        """
        auth_functions = {
            'related_create': auth.related_create,
            'related_update': auth.related_update,
            'user_list': auth.user_list,
            'user_show': auth.user_show,
            'group_show': auth.group_show
        }
        try:
            from ckanext.data_qld.auth_functions import member_create  # noqa: F401
            LOG.info("member_create is already defined in ckanext-data-qld")
        except ImportError:
            auth_functions['member_create'] = auth.member_create
        return auth_functions

    # IValidators

    def get_validators(self):
        """ Add URL validators.
        """
        return {
            'valid_url': valid_url,
            'data_qld_user_name_validator': user_creation_validators.data_qld_user_name_validator,
            'data_qld_displayed_name_validator': user_creation_validators.data_qld_displayed_name_validator,
        }

    # IResourceController

    def after_create(self, context, data_dict):
        # Set the resource position order for this (latest) resource to first
        resource_id = data_dict.get('id', None)
        package_id = data_dict.get('package_id', None)
        if resource_id and package_id:
            try:
                get_action('package_resource_reorder')(context, {'id': package_id, 'order': [resource_id]})
            except Exception as e:
                LOG.error("Failed to move new resource to first position: %s", e)

    # ITranslation

    def i18n_directory(self):
        return os.path.join(os.path.dirname(__file__), 'i18n')
