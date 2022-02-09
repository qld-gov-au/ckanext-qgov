# encoding: utf-8

import six

from flask import Blueprint

import ckan.lib.helpers as h
from ckan.plugins.toolkit import _, g, request, redirect_to, url_for
from ckan.views.user import login, me, EditView
from ckan.views.dashboard import index

blueprint = Blueprint(u'user_overrides', __name__)


def dashboard_override(offset=0):
    """
    Override default CKAN behaviour of throwing 403 Unauthorised exception for /dashboard[/] page and instead
    redirect the user to the login page.
    Ref.: ckan/views/dashboard.py > def index(...)
    :param offset:
    :return:
    """
    return index(offset) if g.user else redirect_to(url_for(u'user.login'))


def logged_in_override():
    """
    Override default CKAN behaviour to only redirect user to `came_from` URL if they are logged in.
    Ref.: ckan/views/user.py > def logged_in()
    :return:
    """
    if g.user:
        came_from = request.params.get(u'came_from', None)
        return redirect_to(six.text_type(came_from)) if came_from and h.url_is_local(came_from) else me()
    else:
        h.flash_error(_(u'Login failed. Bad username or password.'))
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
blueprint.add_url_rule(
    u'/dashboard/', u'dashboard', dashboard_override,
    strict_slashes=False, defaults={u'offset': 0})


def get_blueprints():
    return [blueprint]
