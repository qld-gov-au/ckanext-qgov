# encoding: utf-8
""" Monkey-patch CKAN core functions with our own implementations.
"""

import json
from logging import getLogger
import re
import six

import requests

from ckan.common import _, g, response
from ckan.controllers.user import UserController
from ckan.controllers.package import PackageController
try:
    from ckan.controllers.storage import StorageController
    storage_enabled = True
except ImportError:
    storage_enabled = False
from ckan.lib.navl.dictization_functions import Missing
from ckan.lib.navl.validators import ignore_missing, not_empty
from ckan.lib.redis import connect_to_redis
import ckan.logic
import ckan.logic.action.update
import ckan.logic.schema as schemas
from ckan.logic import validators
from ckan.lib.base import c, request, abort, h
from ckan.lib.uploader import Upload
from ckan.plugins import toolkit

import plugin
from authenticator import unlock_account, LOGIN_THROTTLE_EXPIRY

LOG = getLogger(__name__)

USER_UPDATE = ckan.logic.action.update.user_update
LOGGED_IN = UserController.logged_in
PACKAGE_EDIT = PackageController._save_edit
RESOURCE_EDIT = PackageController.resource_edit

DEFAULT_USER_SCHEMA = schemas.default_user_schema()
USER_NEW_FORM_SCHEMA = schemas.user_new_form_schema()
USER_EDIT_FORM_SCHEMA = schemas.user_edit_form_schema()
DEFAULT_UPDATE_USER_SCHEMA = schemas.default_update_user_schema()
RESOURCE_SCHEMA = schemas.default_resource_schema()

UPLOAD = Upload.upload
if storage_enabled:
    STORAGE_DOWNLOAD = StorageController.file
RESOURCE_DOWNLOAD = PackageController.resource_download

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
    UserController.logged_in = logged_in
    PackageController._save_edit = save_edit
    PackageController.resource_edit = validate_resource_edit

    schemas.default_user_schema = default_user_schema
    schemas.user_new_form_schema = user_new_form_schema
    schemas.user_edit_form_schema = user_edit_form_schema
    schemas.default_update_user_schema = default_update_user_schema

    schemas.default_resource_schema = default_resource_schema

    if storage_enabled:
        StorageController.file = storage_download_with_headers
    PackageController.resource_download = resource_download_with_headers


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
    resource_schema['url'].append(toolkit.get_validator('valid_url'))
    resource_schema['url'].append(toolkit.get_validator('valid_resource_url'))
    return resource_schema


def user_update(context, data_dict):
    '''
    Unlock an account when the password is reset.
    '''
    return_value = USER_UPDATE(context, data_dict)
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
    try:
        author_email = request.POST.getone('author_email')
        if not EMAIL_REGEX.match(author_email):
            abort(400, _('Invalid email.'))
    except Exception:
        abort(400, _('No author email or multiple author emails provided'))

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
            schema_url = plugin.generate_download_url(id, validation_schema)
            data_url = plugin.generate_download_url(id, resource_id)
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
    _set_download_headers(response)
    return file_download


def resource_download_with_headers(self, id, resource_id, filename=None):
    """ Add security headers to protect against download-based exploits.
    """
    file_download = RESOURCE_DOWNLOAD(self, id, resource_id, filename)
    _set_download_headers(response)
    return file_download
