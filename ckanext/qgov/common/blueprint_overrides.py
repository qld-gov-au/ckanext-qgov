# encoding: utf-8

import six

from flask import Blueprint

from ckan import model
import ckan.lib.helpers as h
from ckan.plugins.toolkit import _, g, get_action, request, redirect_to,\
    url_for, ObjectNotFound, NotAuthorized
from ckan.views import dashboard, dataset, resource, user

blueprint = Blueprint(u'user_overrides', __name__)
_dataset = Blueprint(
    u'qgov_dataset',
    __name__,
    url_prefix=u'/dataset/<id>',
    url_defaults={u'package_type': u'dataset'}
)


def dashboard_override(offset=0):
    """
    Override default CKAN behaviour of throwing 403 Unauthorised exception for /dashboard[/] page and instead
    redirect the user to the login page.
    Ref.: ckan/views/dashboard.py > def index(...)
    :param offset:
    :return:
    """
    return dashboard.index(offset) if g.user else redirect_to(url_for(u'user.login'))


def logged_in_override():
    """
    Override default CKAN behaviour to only redirect user to `came_from` URL if they are logged in.
    Ref.: ckan/views/user.py > def logged_in()
    :return:
    """
    if g.user:
        came_from = request.params.get(u'came_from', None)
        return redirect_to(six.text_type(came_from)) if came_from and h.url_is_local(came_from) else user.me()
    else:
        h.flash_error(_(u'Login failed. Bad username or password.'))
        return user.login()


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
    return user.EditView().dispatch_request()


def _get_context():
    return {'model': model, 'session': model.Session,
            'user': g.user, 'for_view': True,
            'auth_user_obj': g.userobj}


def _get_errors_summary(errors):
    return ', '.join([error for key, error in errors.items()])


def _is_dataset_public(id):
    try:
        get_action('package_show')(_get_context(), {'id': id})
        return True
    except ObjectNotFound:
        return True
    except NotAuthorized:
        return False


def dataset_read(package_type, id):
    """
    Override the default CKAN behaviour for private Dataset visibility.
    Instead of displaying "404 Dataset not found" message,
    give unauthenticated users a chance to log in.
    :param id: Package id/name
    :return:
    """
    if not g.user and not _is_dataset_public(id):
        redirect_to(
            url_for('user.login', came_from='/dataset/{id}'.format(id=id))
        )

    return dataset.read(package_type, id)


def resource_read(package_type, id, resource_id):
    """
    Override the default CKAN behaviour for private Dataset Resource visibility.
    Instead of displaying "404 Dataset not found" message,
    give unauthenticated users a chance to log in.
    :param id: Package id/name
    :param resource_id: Resource id
    :return:
    """
    if not g.user and not _is_dataset_public(id):
        redirect_to(
            url_for('user.login',
                    came_from='/dataset/{id}/resource/{resource_id}'.format(id=id, resource_id=resource_id))
        )

    return resource.read(package_type, id, resource_id)


blueprint.add_url_rule(u'/user/logged_in', u'logged_in', logged_in_override)
blueprint.add_url_rule(u'/user/edit', u'edit', user_edit_override)
blueprint.add_url_rule(
    u'/dashboard/', u'dashboard', dashboard_override,
    strict_slashes=False, defaults={u'offset': 0})

_dataset.add_url_rule(u'', view_func=dataset_read)
_dataset.add_url_rule(u'/resource/<resource_id>', view_func=resource_read)


def get_blueprints():
    return [blueprint, _dataset]
