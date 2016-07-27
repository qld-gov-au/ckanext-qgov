from ckan.controllers.user import UserController
from ckan.controllers.package import PackageController
from ckan.model import Session
from ckan.lib.base import BaseController, c, render, request
from ckanext.qgov.common.authenticator import QGOVUser

PERFORM_RESET = UserController.perform_reset
LOGGED_IN = UserController.logged_in
PACKAGE_EDIT = PackageController._save_edit

def set_intercepts():
    UserController.perform_reset = perform_reset
    UserController.logged_in = logged_in
    PackageController._save_edit = save_edit

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
    author_email = request.POST.getone('author_email')

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