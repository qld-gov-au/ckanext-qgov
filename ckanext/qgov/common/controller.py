import re
import ckan.lib.base
from ckan.lib.base import BaseController, c, render, request
from ckan.controllers.storage import StorageController
from ckan.controllers.user import UserController
from ckan.model import Session
from ckanext.qgov.common.authenticator import QGOVUser

from logging import getLogger
LOG = getLogger(__name__)

ALLOWED_EXTENSIONS = re.compile(r'.*((\.csv)|(\.xls)|(\.txt)|(\.kmz)|(\.xlsx)|(\.pdf)|(\.shp)|(\.tab)|(\.jp2)|(\.esri)|(\.gdb)|(\.jpg)|(\.tif)|(\.tiff)|(\.jpeg)|(\.xml)|(\.kml)|(\.doc)|(\.docx)|(\.rtf))$', re.I)

class QGOVController(BaseController):

    def static_content(self, path):
        LOG.info("Seeking static content for " + path)
        from ckan.lib.render import TemplateNotFound
        try:
            return render('static-content/{path}/index.html'.format(path=path))
        except TemplateNotFound:
            LOG.warn(path + " not found")
            base.abort(404)

    def upload_handle(self):
        params = dict(request.params.items())
        originalFilename = params.get('file').filename
        if ALLOWED_EXTENSIONS.search(originalFilename):
            return StorageController.upload_handle(StorageController())
        base.abort(403, 'This file type is not supported. If possible, upload the file in another format. If you continue to have problems, email Smart Service - onlineservices@smartservice.qld.gov.au')

    def logged_in(self):
        controller = UserController()
        if not c.user:
            # a number of failed login attempts greater than 10
            # indicates that the locked user is associated with the current request
            qgovUser = Session.query(QGOVUser).filter(QGOVUser.login_attempts > 10).first()
            if qgovUser:
                qgovUser.login_attempts = 10
                Session.commit()
                return controller.login('account-locked')
        return controller.logged_in()
