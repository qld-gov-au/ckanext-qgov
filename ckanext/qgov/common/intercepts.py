from ckan.controllers.user import UserController
from ckan.controllers.package import PackageController
from ckan.controllers.storage import StorageController
import ckan.logic
import ckan.logic.schema as schemas
from ckan.model import Session
from ckan.lib.base import BaseController, c, render, request, abort, h
from pylons.i18n import _
from ckanext.qgov.common.authenticator import QGOVUser
from ckan.lib.uploader import *
import plugin
import re
import requests
import json

PERFORM_RESET = UserController.perform_reset
LOGGED_IN = UserController.logged_in
PACKAGE_EDIT = PackageController._save_edit
RESOURCE_EDIT = PackageController.resource_edit

DEFAULT_USER_SCHEMA = schemas.default_user_schema()
USER_NEW_FORM_SCHEMA = schemas.user_new_form_schema()
USER_EDIT_FORM_SCHEMA = schemas.user_edit_form_schema()
DEFAULT_UPDATE_USER_SCHEMA = schemas.default_update_user_schema()

UPLOAD = Upload.upload
RESOURCE_UPLOAD = ResourceUpload.upload
STORAGE_DOWNLOAD = StorageController.file
RESOURCE_DOWNLOAD = PackageController.resource_download

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

ALLOWED_EXTENSIONS = re.compile(r'.*((\.csv)|(\.xls)|(\.txt)|(\.kmz)|(\.xlsx)|(\.pdf)|(\.shp)|(\.tab)|(\.jp2)|(\.esri)|(\.gdb)|(\.jpg)|(\.tif)|(\.tiff)|(\.jpeg)|(\.xml)|(\.kml)|(\.doc)|(\.docx)|(\.rtf)|(\.json)|(\.accdb)|(\.geojson)|(\.geotiff)|(\.topojson)|(\.gpx)|(\.html)|(\.mtl)|(\.obj)|(\.ppt)|(\.pptx)|(\.wfs)|(\.wmts)|(\.zip))$', re.I)

def set_intercepts():
    UserController.perform_reset = perform_reset
    UserController.logged_in = logged_in
    PackageController._save_edit = save_edit
    PackageController.resource_edit = validate_resource_edit

    schemas.default_user_schema = default_user_schema
    schemas.user_new_form_schema = user_new_form_schema
    schemas.user_edit_form_schema = user_edit_form_schema
    schemas.default_update_user_schema = default_update_user_schema

    Upload.upload = upload_after_validation
    ResourceUpload.upload = resource_upload_after_validation
    StorageController.file = storage_download_with_headers
    PackageController.resource_download = resource_download_with_headers

def default_user_schema():
    user_schema = DEFAULT_USER_SCHEMA
    if 'password' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password'][idx] = plugin.user_password_validator
    return user_schema

def user_new_form_schema():
    user_schema = USER_NEW_FORM_SCHEMA
    if 'password' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password'][idx] = plugin.user_password_validator

    if 'password1' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password1']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password1'][idx] = plugin.user_password_validator

    return user_schema

def user_edit_form_schema():
    user_schema = USER_EDIT_FORM_SCHEMA
    if 'password' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password'][idx] = plugin.user_password_validator
    if 'password1' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password1']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password1'][idx] = plugin.user_password_validator
    return user_schema

def default_update_user_schema():
    user_schema = DEFAULT_UPDATE_USER_SCHEMA
    if 'password' in user_schema:
        for idx, user_schema_func in enumerate(user_schema['password']):
            if user_schema_func.__name__ == 'user_password_validator':
                user_schema['password'][idx] = plugin.user_password_validator
    return user_schema

def perform_reset(self, id):
    '''
    Extending Reset to include login_attempts
    Success loading original perform_reset indicates legitimate user
    Set login_attempts to 0
    '''
    to_render = PERFORM_RESET(self, id)
    qgovUser = Session.query(QGOVUser).filter(QGOVUser.id == id).first()
    if qgovUser:
        qgovUser.login_attempts = 0
        Session.commit()
    return to_render

def logged_in(self):
    if not c.user:
        # a number of failed login attempts greater than 10
        # indicates that the locked user is associated with the current request
        qgovUser = Session.query(QGOVUser).filter(QGOVUser.login_attempts > 10).first()
        if qgovUser:
            qgovUser.login_attempts = 10
            Session.commit()
            return self.login('account-locked')
    return LOGGED_IN(self)

def save_edit(self, name_or_id, context, package_type=None):
    '''
    Intercept save_edit
    Replace author,maintainer,maintainer_email
    '''
    try:
        author_email = request.POST.getone('author_email')
        if not EMAIL_REGEX.match(author_email):
            abort(400, _('Invalid email.'))
    except:
        abort(400, _('No author email or multiple author emails provided'))

    if request.POST.has_key('author'):
        request.POST.__delitem__('author')
    if request.POST.has_key('maintainer'):
        request.POST.__delitem__('maintainer')
    if request.POST.has_key('maintainer_email'):
        request.POST.__delitem__('maintainer_email')

    request.POST.add('author',author_email)
    request.POST.add('maintainer',author_email)
    request.POST.add('maintainer_email',author_email)

    return PACKAGE_EDIT(self, name_or_id, context, package_type=None)

def validate_resource_edit(self, id, resource_id, data=None, errors=None, error_summary=None):
    '''
    Intercept save_edit
    Replace author,maintainer,maintainer_email
    '''
    if request.POST.has_key('validation_schema') and request.POST.has_key('format'):
        resource_format = request.POST.getone('format')
        validation_schema = request.POST.getone('validation_schema')
        if resource_format == 'CSV' and validation_schema and validation_schema != '':
            schema_url = plugin.generate_download_url(id,validation_schema)
            data_url = plugin.generate_download_url(id,resource_id)
            validation_url = "http://goodtables.okfnlabs.org/api/run?format=csv&schema={0}&data={1}&row_limit=100000&report_limit=1000&report_type=grouped".format(schema_url,data_url)
            r = requests.get(validation_url,verify=False)
            if r.status_code == requests.codes.ok:
                response_text = json.loads(r.text)
                if response_text['success'] == True:
                    h.flash_success("CSV was validated successfully against the selected schema")
                else:
                    h.flash_error("CSV was NOT validated against the selected schema")

    return RESOURCE_EDIT(self, id, resource_id, data, errors, error_summary)

def upload_after_validation(self, max_size = 2):
    if self.upload_field_storage and self.upload_field_storage.filename and not ALLOWED_EXTENSIONS.search(self.upload_field_storage.filename):
        raise ckan.logic.ValidationError(
            {self.file_field: ['This file type is not supported. If possible, upload the file in another format. If you continue to have problems, email One Stop Shop - oss.online@dsiti.qld.gov.au']}
        )
    UPLOAD(self, max_size)

def resource_upload_after_validation(self, id, max_size = 2):
    if self.filename and not ALLOWED_EXTENSIONS.search(self.filename):
        raise ckan.logic.ValidationError(
            {'upload': ['This file type is not supported. If possible, upload the file in another format. If you continue to have problems, email One Stop Shop - oss.online@dsiti.qld.gov.au']}
        )
    RESOURCE_UPLOAD(self, id, max_size)

def set_download_headers():
    from ckan.common import response
    response.headers['Content-Disposition'] = 'attachment'
    response.headers['X-Content-Type-Options'] = 'nosniff'

def storage_download_with_headers(self, label):
    file_download = STORAGE_DOWNLOAD(self, label)
    set_download_headers()
    return file_download

def resource_download_with_headers(self, id, resource_id, filename = None):
    file_download = RESOURCE_DOWNLOAD(self, id, resource_id, filename)
    set_download_headers()
    return file_download
