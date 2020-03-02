# encoding: utf-8
""" Monkey-patch CKAN core functions with our own implementations.
"""

import re
import json
from logging import getLogger
import socket
import urlparse

import requests

from ckan.common import _, response
from ckan.controllers.user import UserController
from ckan.controllers.package import PackageController
from ckan.controllers.storage import StorageController
from ckan.lib.navl.dictization_functions import Missing
import ckan.logic
import ckan.logic.action.update
import ckan.logic.schema as schemas
import ckan.logic.validators as validators
from ckan.model import Session
from ckan.lib.base import c, request, abort, h
from ckan.lib.uploader import Upload, ResourceUpload
import ckan.lib.navl.dictization_functions as df

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
RESOURCE_UPLOAD = ResourceUpload.upload
STORAGE_DOWNLOAD = StorageController.file
RESOURCE_DOWNLOAD = PackageController.resource_download

IP_ADDRESS = re.compile(r'^({0}[.]){{3}}{0}$'.format(r'[0-9]{1,3}'))
PRIVATE_IP_ADDRESS = re.compile(r'^((10|127)([.]{0}){{3}}|(172[.](1[6-9]|2[0-9]|3[01])|169[.]254)([.]{0}){{2}}|192[.]168([.]{0}){{2}})$'.format(r'[0-9]{1,3}'))

ALLOWED_EXTENSIONS = [
    'csv',
    'xls',
    'txt',
    'kmz',
    'xlsx',
    'pdf',
    'shp',
    'tab',
    'jp2',
    'esri',
    'gdb',
    'jpg',
    'png',
    'tif',
    'tiff',
    'jpeg',
    'xml',
    'kml',
    'doc',
    'docx',
    'rtf',
    'json',
    'accdb',
    'geojson',
    'geotiff',
    'topojson',
    'gpx',
    'html',
    'mtl',
    'obj',
    'ppt',
    'pptx',
    'wfs',
    'wmts',
    'zip'
]
ALLOWED_EXTENSIONS_PATTERN = re.compile(r'.*\.(' + '|'.join(ALLOWED_EXTENSIONS) + ')$', re.I)
INVALID_UPLOAD_MESSAGE = '''This file type is not supported.
If possible, upload the file in another format.
If you continue to have problems, email
One Stop Shop - oss.online@dsiti.qld.gov.au
'''

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def configure(config):
    global RESOURCE_WHITELIST
    global RESOURCE_BLACKLIST
    global password_min_length
    global password_patterns
    RESOURCE_WHITELIST = config.get('ckanext.qgov.resource_domains.whitelist', '').split()
    RESOURCE_BLACKLIST = config.get('ckanext.qgov.resource_domains.blacklist', '').split()

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

    LOG.info("Resources must come from: %s and cannot come from %s", RESOURCE_WHITELIST, RESOURCE_BLACKLIST)

    RESOURCE_SCHEMA['url'].append(valid_url)
    RESOURCE_SCHEMA['url'].append(valid_resource_url)

    schemas.default_resource_schema = default_resource_schema

    Upload.upload = upload_after_validation
    ResourceUpload.upload = resource_upload_after_validation
    StorageController.file = storage_download_with_headers
    PackageController.resource_download = resource_download_with_headers


def user_password_validator(key, data, errors, context):
    """ Strengthen the built-in password validation to require more length and complexity.
    """
    value = data[key]

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, basestring):
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
    """ Return a copy of the altered resource schema.

    This cannot be an entirely shallow copy, or else it will be permanently
    modified by eg schema.default_show_package_schema; however, it does not
    need to be infinitely deep.
    """
    resource_schema = RESOURCE_SCHEMA.copy()
    for key in resource_schema:
        resource_schema[key] = resource_schema[key][:]
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

    # reject the URL if it matches any blacklist entry
    if RESOURCE_BLACKLIST:
        for domain in RESOURCE_BLACKLIST:
            if _domain_match(resource_url.hostname, domain):
                raise df.Invalid(_('{} is blocked').format(domain))

    # require the URL to match a whitelist entry, if applicable
    if RESOURCE_WHITELIST:
        for domain in RESOURCE_WHITELIST:
            if _domain_match(resource_url.hostname, domain):
                return
        raise df.Invalid(_('Must be from an allowed domain: {}').format(RESOURCE_WHITELIST))

    return


def _domain_match(hostname, pattern):
    """ Test whether 'hostname' matches the pattern.

    Note that this is not a regex match, but subdomains are allowed.
    Alternatively, 'pattern' can be an IP address, in which case,
    this tests whether 'hostname' can resolve to that IP address.

    If the pattern is 'private', then all private IP addresses are matched.
    This includes:
    10.x.x.x
    127.x.x.x
    169.254.x.x
    172.16.0.0 to 172.31.255.255
    192.168.x.x
    """
    if pattern == 'private':
        if PRIVATE_IP_ADDRESS.match(hostname):
            return True
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyname_ex(hostname)
            for ipaddr in ipaddrlist:
                if PRIVATE_IP_ADDRESS.match(ipaddr):
                    LOG.debug("%s can resolve to %s which is private",
                              hostname, ipaddrlist)
                    return True
        except socket.gaierror:
            # this is normal since the user could enter any arbitrary hostname
            pass
    elif IP_ADDRESS.match(pattern):
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyname_ex(hostname)
            if pattern in ipaddrlist:
                LOG.debug("%s can resolve to %s which includes %s",
                          hostname, ipaddrlist, pattern)
                return True
        except socket.gaierror:
            # this is normal since the user could enter any arbitrary hostname
            pass
    if hostname == pattern or hostname.endswith('.' + pattern):
        return True
    return False


def upload_after_validation(self, max_size=2):
    """ Validate file type against our whitelist before uploading.
    """
    if self.upload_field_storage and self.upload_field_storage.filename and not ALLOWED_EXTENSIONS_PATTERN.search(self.upload_field_storage.filename):
        raise ckan.logic.ValidationError(
            {self.file_field: [INVALID_UPLOAD_MESSAGE]}
        )
    UPLOAD(self, max_size)


def resource_upload_after_validation(self, id, max_size=10):
    """ Validate file type against our whitelist before uploading.
    """
    if self.filename and not ALLOWED_EXTENSIONS_PATTERN.search(self.filename):
        raise ckan.logic.ValidationError(
            {'upload': [INVALID_UPLOAD_MESSAGE]}
        )
    RESOURCE_UPLOAD(self, id, max_size)


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
