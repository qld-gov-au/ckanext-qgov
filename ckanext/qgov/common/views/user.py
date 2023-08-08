# encoding: utf-8

from six import text_type as str

from flask import Blueprint

import ckan.lib.helpers as h
from ckan.plugins.toolkit import _, g, request, redirect_to, url_for
from ckan.views.user import login, me, EditView

blueprint = Blueprint(u'user_overrides', __name__)


def logged_in_override():
    """
    Override default CKAN behaviour to only redirect user to `came_from` URL if they are logged in.
    Ref.: ckan/views/user.py > def logged_in()
    :return:
    """
    if g.user:
        came_from = request.params.get(u'came_from', None)
        return redirect_to(str(came_from)) if came_from and h.url_is_local(came_from) else me()
    else:
        h.flash_error(_(u'Login failed. Bad username or password or reCAPTCHA.'))
        return login()


def user_edit_override():
    """
    Override default CKAN behaviour of displaying "No user specified" message for /user/edit page and instead
    redirect the user to the login page.
    Ref.: ckan/views/user.py > class EditView(...)
    :return:
    """
    if not g.user:
        return redirect_to(url_for(
            u'user.login',
            came_from=url_for(u'user.edit')))
    return EditView().dispatch_request()


blueprint.add_url_rule(u'/user/logged_in', u'logged_in', logged_in_override)
blueprint.add_url_rule(u'/user/edit', u'edit', user_edit_override)


def get_blueprints():
    return [blueprint]
