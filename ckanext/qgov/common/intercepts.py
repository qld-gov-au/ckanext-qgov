# encoding: utf-8
""" Monkey-patch CKAN core functions with our own implementations.
"""

import json
from logging import getLogger
import re
import six

import requests

from ckan.lib.navl.dictization_functions import Missing
from ckan.lib.navl.validators import ignore_missing, not_empty
from ckan.lib.redis import connect_to_redis
import ckan.logic
import ckan.logic.action.update
import ckan.logic.schema as schemas
from ckan.logic import validators
from ckan.plugins import toolkit
from ckan.plugins.toolkit import _, abort, c, g, h, get_validator, \
    chained_action, redirect_to, request

from . import helpers
from .authenticator import unlock_account, LOGIN_THROTTLE_EXPIRY
from .urlm import get_purl_response
from .user_creation import helpers as user_creation_helpers

LOG = getLogger(__name__)

DEFAULT_USER_SCHEMA = schemas.default_user_schema()
USER_NEW_FORM_SCHEMA = schemas.user_new_form_schema()
USER_EDIT_FORM_SCHEMA = schemas.user_edit_form_schema()
DEFAULT_UPDATE_USER_SCHEMA = schemas.default_update_user_schema()
RESOURCE_SCHEMA = schemas.default_resource_schema()

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def configure(config):
    global password_min_length
    global password_patterns

    password_min_length = int(config.get('password_min_length', '10'))
    password_patterns = config.get(
        'password_patterns',
        r'.*[0-9].*,.*[a-z].*,.*[A-Z].*,.*[-`~!@#$%^&*()_+=|\\/ ].*'
    ).split(',')


def set_intercepts():
    """ Monkey-patch to wrap/override core functions with our own.
    """
    validators.user_password_validator = user_password_validator

    schemas.default_user_schema = default_user_schema
    schemas.user_new_form_schema = user_new_form_schema
    schemas.user_edit_form_schema = user_edit_form_schema
    schemas.default_update_user_schema = default_update_user_schema

    schemas.default_resource_schema = default_resource_schema


def set_pylons_intercepts():
    from ckan.controllers.user import UserController
    from ckan.controllers.package import PackageController
    try:
        from ckan.controllers.storage import StorageController
        storage_enabled = True
    except ImportError:
        storage_enabled = False
    from ckan.lib import base
    from ckan.controllers import group, package, user

    global LOGGED_IN, PACKAGE_EDIT, RESOURCE_EDIT, RESOURCE_DOWNLOAD, STORAGE_DOWNLOAD, ABORT
    LOGGED_IN = UserController.logged_in
    PACKAGE_EDIT = PackageController._save_edit
    RESOURCE_EDIT = PackageController.resource_edit
    RESOURCE_DOWNLOAD = PackageController.resource_download
    ABORT = base.abort

    UserController.logged_in = logged_in
    PackageController._save_edit = save_edit
    PackageController.resource_edit = validate_resource_edit

    if storage_enabled:
        STORAGE_DOWNLOAD = StorageController.file
        StorageController.file = storage_download_with_headers
    PackageController.resource_download = resource_download_with_headers

    # Monkey-patch ourselves into the 404 handler
    base.abort = abort_with_purl
    group.abort = abort_with_purl
    package.abort = abort_with_purl
    user.abort = abort_with_purl


def user_password_validator(key, data, errors, context):
    """ Strengthen the built-in password validation to require more length and complexity.
    """
    value = data[key]

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, six.string_types):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif not len(value) >= password_min_length:
        errors[('password',)].append(
            _('Your password must be {min} characters or longer'.format(min=password_min_length))
        )
    else:
        for policy in password_patterns:
            if not re.search(policy, value):
                errors[('password',)].append(
                    _('Must contain at least one number, lowercase letter, capital letter, and symbol')
                )


def _apply_schema_validator(user_schema, field_name, validator_name='user_password_validator',
                            validator=user_password_validator):
    if field_name in user_schema:
        for idx, user_schema_func in enumerate(user_schema[field_name]):
            if user_schema_func.__name__ == validator_name:
                user_schema[field_name][idx] = validator
                break
        else:
            user_schema[field_name].append(validator)
    return user_schema


def _remove_schema_validator(user_schema, field_name, validator):
    if field_name in user_schema\
            and validator in user_schema[field_name]:
        user_schema[field_name].remove(validator)
    return user_schema


def default_user_schema():
    """ Add our password validator function to the default list.
    """
    user_schema = DEFAULT_USER_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def user_new_form_schema():
    """ Apply our password validator function when creating a new user.
    """
    user_schema = USER_NEW_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def user_edit_form_schema():
    """ Apply our password validator function when editing an existing user.
    """
    user_schema = USER_EDIT_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def default_update_user_schema():
    """ Apply our password validator function when updating a user.
    """
    user_schema = DEFAULT_UPDATE_USER_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def default_resource_schema():
    """ Add URL validators to the default resource schema.
    """
    resource_schema = RESOURCE_SCHEMA.copy()
    # We can't make an entirely shallow copy, or else it will be permanently
    # modified by eg schema.default_show_package_schema, but we don't want
    # infinite depth either.
    for key in resource_schema:
        resource_schema[key] = resource_schema[key][:]
    resource_schema['url'].append(get_validator('valid_url'))
    return resource_schema


@chained_action
def user_update(original_action, context, data_dict):
    '''
    Unlock an account when the password is reset.
    '''
    modified_schema = context.get('schema') or default_user_schema()
    context['schema'] = user_creation_helpers.add_custom_validator_to_user_schema(modified_schema)
    return_value = original_action(context, data_dict)
    if u'reset_key' in data_dict:
        account_id = ckan.logic.get_or_bust(data_dict, 'id')
        unlock_account(account_id)
    return return_value


def logged_in(self):
    """ Provide a custom error code when login fails due to account lockout.
    """
    if not c.user:
        # a number of failed login attempts greater than 10 indicates
        # that the locked user is associated with the current request
        redis_conn = connect_to_redis()

        for key in redis_conn.keys('{}.ckanext.qgov.login_attempts.*'.format(g.site_id)):
            login_attempts = redis_conn.get(key)
            if login_attempts > 10:
                redis_conn.set(key, 10, ex=LOGIN_THROTTLE_EXPIRY)
                return self.login('account-locked')
    return LOGGED_IN(self)


def save_edit(self, name_or_id, context, package_type=None):
    '''
    Intercept save_edit
    Replace author, maintainer, maintainer_email
    '''
    # Harvest package types do not have 'author_email' in their schema.
    if package_type == 'harvest':
        return PACKAGE_EDIT(self, name_or_id, context, package_type)

    try:
        author_email = request.POST.getone('author_email')
    except Exception:
        return abort(400, _('No author email or multiple author emails provided'))
    if not EMAIL_REGEX.match(author_email):
        return abort(400, _('Invalid email.'))

    if 'author' in request.POST:
        request.POST.__delitem__('author')
    if 'maintainer' in request.POST:
        request.POST.__delitem__('maintainer')
    if 'maintainer_email' in request.POST:
        request.POST.__delitem__('maintainer_email')

    request.POST.add('author', author_email)
    request.POST.add('maintainer', author_email)
    request.POST.add('maintainer_email', author_email)

    return PACKAGE_EDIT(self, name_or_id, context, package_type=None)


def validate_resource_edit(self, id, resource_id,
                           data=None, errors=None, error_summary=None):
    '''
    Intercept save_edit
    Replace author, maintainer, maintainer_email
    '''
    if 'validation_schema' in request.POST and 'format' in request.POST:
        resource_format = request.POST.getone('format')
        validation_schema = request.POST.getone('validation_schema')
        if resource_format == 'CSV' and validation_schema and validation_schema != '':
            schema_url = helpers.generate_download_url(id, validation_schema)
            data_url = helpers.generate_download_url(id, resource_id)
            validation_url = "http://goodtables.okfnlabs.org/api/run?format=csv&schema={0}&data={1}&row_limit=100000&report_limit=1000&report_type=grouped".format(schema_url, data_url)
            req = requests.get(validation_url, verify=False)
            if req.status_code == requests.codes.ok:
                response_text = json.loads(req.text)
                if response_text['success']:
                    h.flash_success("CSV was validated successfully against the selected schema")
                else:
                    h.flash_error("CSV was NOT validated against the selected schema")

    return RESOURCE_EDIT(self, id, resource_id, data, errors, error_summary)


def _set_download_headers(response):
    response.headers['Content-Disposition'] = 'attachment'
    response.headers['X-Content-Type-Options'] = 'nosniff'


def storage_download_with_headers(self, label):
    """ Add security headers to protect against download-based exploits.
    """
    file_download = STORAGE_DOWNLOAD(self, label)
    _set_download_headers(toolkit.response)
    return file_download


def resource_download_with_headers(self, id, resource_id, filename=None):
    """ Add security headers to protect against download-based exploits.
    """
    file_download = RESOURCE_DOWNLOAD(self, id, resource_id, filename)
    _set_download_headers(toolkit.response)
    return file_download


def abort_with_purl(status_code=None, detail='', headers=None, comment=None):
    """ Consult PURL about a 404, redirecting if it reports a new URL.
    """
    if status_code == 404:
        redirect_url = get_purl_response(request.url)
        if redirect_url:
            return redirect_to(redirect_url, 301)

    return ABORT(status_code, detail, headers, comment)
