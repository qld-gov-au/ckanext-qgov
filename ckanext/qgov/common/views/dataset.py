# encoding: utf-8

import logging

from flask import Blueprint

from ckan import model
from ckan.plugins.toolkit import check_ckan_version, g, get_action,\
    redirect_to, url_for, ObjectNotFound, NotAuthorized
from ckan.views import dataset, resource

from ckanext.qgov.common.helpers import make_uncached_response

LOG = logging.getLogger(__name__)

_dataset = Blueprint(
    u'qgov_dataset',
    __name__,
    url_prefix=u'/dataset/',
    url_defaults={u'package_type': u'dataset'}
)


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
        LOG.debug("Package %s does not exist", id)
        return True
    except NotAuthorized:
        LOG.debug("Package %s is not visible", id)
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
        return make_uncached_response(redirect_to(
            url_for('user.login', came_from=url_for('dataset.read', id=id))
        ))

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
        return make_uncached_response(redirect_to(
            url_for('user.login',
                    came_from=url_for('resource.read', id=id, resource_id=resource_id))
        ))

    return resource.read(package_type, id, resource_id)


# Any core routes that would match an <id> pattern, such as 'new',
# must be repeated here, or else they will be overridden.
_dataset.add_url_rule(u'new', view_func=dataset.CreateView.as_view('new'))
if not check_ckan_version('2.10'):
    _dataset.add_url_rule(u'changes_multiple', 'changes_multiple', view_func=dataset.changes_multiple)
_dataset.add_url_rule(u'<id>', view_func=dataset_read)
_dataset.add_url_rule(u'<id>/resource/new', view_func=resource.CreateView.as_view('new_resource'))
_dataset.add_url_rule(u'<id>/resource/<resource_id>', view_func=resource_read)


def get_blueprints():
    return [_dataset]
