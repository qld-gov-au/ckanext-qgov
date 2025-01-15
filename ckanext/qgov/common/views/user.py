# encoding: utf-8

from flask import Blueprint
from typing import Any

from ckan.plugins.toolkit import g, redirect_to, url_for
from ckan.views import user as user_view

blueprint = Blueprint(u'user_overrides', __name__)


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
    return user_view.EditView().dispatch_request()


def _gettext_wrapper(*args: Any, **kwargs: Any):
    translation = original_gettext(*args, **kwargs)
    if 'Bad username or password.' in translation:
        translation = translation.replace('or password.', 'or password or CAPTCHA.')
    return translation


blueprint.add_url_rule(u'/user/edit', u'edit', user_edit_override)
original_gettext = user_view._
user_view._ = _gettext_wrapper


def get_blueprints():
    return [blueprint]
