# encoding: utf-8
""" Monkey-patch CKAN core functions with our own implementations.
"""

import json
from logging import getLogger
import magic
import mimetypes
import os
import re
import six

import requests

from ckan.common import _, response
from ckan.controllers.user import UserController
from ckan.controllers.package import PackageController
from ckan.controllers.storage import StorageController
from ckan.lib.navl.dictization_functions import Missing
from ckan.lib.uploader import ALLOWED_UPLOAD_TYPES
import ckan.logic
import ckan.logic.action.update
import ckan.logic.schema as schemas
import ckan.logic.validators as validators
from ckan.model import Session
from ckan.lib.base import c, request, abort, h
from ckan.lib.uploader import Upload
import ckan.plugins.toolkit as toolkit
from werkzeug.datastructures import FileStorage as FlaskFileStorage

import plugin
from authenticator import QGOVUser

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
STORAGE_DOWNLOAD = StorageController.file
RESOURCE_DOWNLOAD = PackageController.resource_download

ALLOWED_EXTENSIONS = [
    'accdb',
    'csv',
    'doc',
    'docx',
    'esri',
    'gdb',
    'geojson',
    'geotiff',
    'gpx',
    'html',
    'jp2',
    'jpeg',
    'jpg',
    'json',
    'kml',
    'kmz',
    'mtl',
    'obj',
    'pdf',
    'png',
    'ppt',
    'pptx',
    'rtf',
    'shp',
    'tab',
    'tif',
    'tiff',
    'topojson',
    'txt',
    'wfs',
    'wmts',
    'xls',
    'xlsx',
    'xml',
    'zip'
]
ALLOWED_EXTENSIONS_PATTERN = re.compile(r'.*\.(' + '|'.join(ALLOWED_EXTENSIONS) + ')$', re.I)
GENERIC_MIMETYPES = ['application/octet-stream', 'text/plain']
INVALID_UPLOAD_MESSAGE = '''This file type is not supported.
If possible, upload the file in another format.
If you continue to have problems, email
Smart Service Queensland - online.products@smartservice.qld.gov.au
'''
MISMATCHING_UPLOAD_MESSAGE = '''Unable to determine whether the file is
of type '{}' or '{}'.
If possible, upload the file in another format.
If you continue to have problems, email
Smart Service Queensland - online.products@smartservice.qld.gov.au
'''
IS_REMOTE_URL_PATTERN = re.compile(r'^[a-z]+:')

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def _get_underlying_file(wrapper):
    if isinstance(wrapper, FlaskFileStorage):
        return wrapper.stream
    return wrapper.file


def configure(config):
    global password_min_length
    global password_patterns
    global allowed_mime_types

    password_min_length = int(config.get('password_min_length', '10'))
    password_patterns = config.get(
        'password_patterns',
        r'.*[0-9].*,.*[a-z].*,.*[A-Z].*,.*[-`~!@#$%^&*()_+=|\\/ ].*'
    ).split(',')
    allowed_mime_types = config.get('ckan.mimetypes_allowed', '*').split(',')

    # Add allowed upload types that don't seem to be standard.
    # NB It's more important to match a sniffable type than an RFC type.
    mimetypes.add_type('application/msaccess', '.accdb')
    mimetypes.add_type('x-gis/x-shapefile', '.esri')
    mimetypes.add_type('application/x-filegdb', '.gdb')
    mimetypes.add_type('application/json', '.geojson')
    mimetypes.add_type('image/tiff', '.geotiff')
    mimetypes.add_type('application/xml', '.gpx')
    mimetypes.add_type('model/mtl', '.mtl')
    mimetypes.add_type('x-gis/x-shapefile', '.shp')
    mimetypes.add_type('text/plain', '.tab')
    mimetypes.add_type('application/json', '.topojson')
    mimetypes.add_type('application/xml', '.wfs')
    mimetypes.add_type('application/xml', '.wmts')


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

    Upload.upload = upload_after_validation
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
    return user_schema


def default_user_schema():
    """ Add our password validator function to the default list.
    """
    return _apply_schema_validator(DEFAULT_USER_SCHEMA, 'password')


def user_new_form_schema():
    """ Apply our password validator function when creating a new user.
    """
    user_schema = USER_NEW_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    return user_schema


def user_edit_form_schema():
    """ Apply our password validator function when editing an existing user.
    """
    user_schema = USER_EDIT_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    return user_schema


def default_update_user_schema():
    """ Apply our password validator function when updating a user.
    """
    return _apply_schema_validator(DEFAULT_UPDATE_USER_SCHEMA, 'password')


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


def _unlock_account(account_id):
    """ Unlock an account (erase the failed login attempts).
    """
    qgov_user = Session.query(QGOVUser).filter(QGOVUser.id == account_id).first()
    if qgov_user:
        LOG.debug("Clearing failed login attempts for %s", account_id)
        qgov_user.login_attempts = 0
        Session.commit()
    else:
        LOG.debug("Account %s not found", account_id)


def user_update(context, data_dict):
    '''
    Unlock an account when the password is reset.
    '''
    return_value = USER_UPDATE(context, data_dict)
    if u'reset_key' in data_dict:
        account_id = ckan.logic.get_or_bust(data_dict, 'id')
        _unlock_account(account_id)
    return return_value


def logged_in(self):
    """ Provide a custom error code when login fails due to account lockout.
    """
    if not c.user:
        # a number of failed login attempts greater than 10
        # indicates that the locked user is associated with the current request
        qgov_user = Session.query(QGOVUser).filter(QGOVUser.login_attempts > 10).first()
        if qgov_user:
            qgov_user.login_attempts = 10
            Session.commit()
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


def upload_after_validation(self, max_size=2):
    """ Validate file type against our whitelist before uploading.
    """
    if self.upload_field_storage and self.upload_field_storage.filename and not ALLOWED_EXTENSIONS_PATTERN.search(self.upload_field_storage.filename):
        raise ckan.logic.ValidationError(
            {self.file_field: [INVALID_UPLOAD_MESSAGE]}
        )
    UPLOAD(self, max_size)


def validate_resource_mimetype(resource):
    upload_field_storage = resource.get('upload', None)
    if isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
        filename = upload_field_storage.filename

        mime = magic.Magic(mime=True)
        upload_file = _get_underlying_file(upload_field_storage)
        sniffed_mimetype = mime.from_buffer(upload_file.read(512))
        # go back to the beginning of the file buffer
        upload_file.seek(0, os.SEEK_SET)
        LOG.debug("Upload sniffing indicates MIME type %s", sniffed_mimetype)
    elif IS_REMOTE_URL_PATTERN.search(resource.get('url', 'http://example.com')):
        LOG.debug("%s is not an uploaded resource; don't validate", resource['id'])
        return
    else:
        LOG.debug("No upload in progress for %s; just sanity-check metadata", resource['id'])
        filename = resource.get('url')
        sniffed_mimetype = None

    if not ALLOWED_EXTENSIONS_PATTERN.search(filename):
        raise ckan.logic.ValidationError(
            {'upload': [INVALID_UPLOAD_MESSAGE]}
        )

    filename_mimetype = mimetypes.guess_type(resource.get('url'), strict=False)[0]
    LOG.debug("Upload filename indicates MIME type %s", filename_mimetype)

    format_mimetype = mimetypes.guess_type('example.' + resource.get('format', ''), strict=False)[0]
    LOG.debug("Upload format indicates MIME type %s", format_mimetype)

    # If the file extension or format matches a generic type,
    # then sniffing should say the same.
    # This is to prevent attacks based on browser sniffing.
    allow_override = filename_mimetype not in GENERIC_MIMETYPES\
        and format_mimetype not in GENERIC_MIMETYPES

    claimed_mimetype = resource.get('mimetype')
    LOG.debug("Upload claims to have MIME type %s", claimed_mimetype)

    best_guess_mimetype = resource['mimetype'] = coalesce_mime_types(
        [filename_mimetype, format_mimetype, sniffed_mimetype, claimed_mimetype],
        allow_override=allow_override
    )
    LOG.debug("Best guess at MIME type is %s", best_guess_mimetype)
    if not is_mimetype_allowed(best_guess_mimetype):
        raise ckan.logic.ValidationError(
            {'upload': [INVALID_UPLOAD_MESSAGE]}
        )


def coalesce_mime_types(mime_types, allow_override=True):
    """ Compares a list of potential mime types and identifies
    the best candidate, ignoring any that are None.

    Throws ckan.logic.ValidationError if any candidates conflict.
    Returns 'application/octet-stream' if all candidates are None.

    'allow_override' controls the treatment of 'application/octet-stream'
    and 'text/plain' candidates. If True, then more specific types will
    be able to override these types (within limits, eg 'text/csv' and
    'application/xml' can override 'text/plain', but 'application/pdf'
    cannot). If False, then all types must exactly match, or
    ValidationError will be thrown.
    """
    best_candidate = None
    for mime_type in mime_types:
        if not mime_type or mime_type == best_candidate:
            continue
        if not best_candidate:
            best_candidate = mime_type
            continue
        if allow_override and is_valid_override(best_candidate, mime_type):
            if best_candidate in GENERIC_MIMETYPES:
                best_candidate = mime_type
                continue
            if mime_type in GENERIC_MIMETYPES:
                continue
        raise ckan.logic.ValidationError(
            {'upload': [MISMATCHING_UPLOAD_MESSAGE.format(best_candidate, mime_type)]}
        )

    return best_candidate or 'application/octet-stream'


def is_valid_override(mime_type1, mime_type2):
    """ Returns True if one of the two types can be considered a subtype
    of the other, eg 'text/csv' can override 'text/plain'.
    """
    if 'application/octet-stream' in [mime_type1, mime_type2]:
        return True
    if 'text/plain' in [mime_type1, mime_type2]:
        if mime_type1.split('/')[0] == mime_type2.split('/')[0]:
            return True
        if 'application/xml' in [mime_type1, mime_type2]:
            return True
    return False


def is_mimetype_allowed(mime_type):
    for allowed_mime_type in allowed_mime_types:
        if allowed_mime_type == '*' or allowed_mime_type == mime_type:
            return True
    return False


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
