# encoding: utf-8

from flask import Blueprint

from ckan import model
from ckan.plugins.toolkit import g, get_action, redirect_to, url_for,\
    ObjectNotFound, NotAuthorized


_dataset = Blueprint(
    u'qgov_dataset',
    __name__,
    url_prefix=u'/dataset/<id>',
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
    import ckan.views.dataset as dataset_view
    if not g.user and not _is_dataset_public(id):
        redirect_to(
            url_for('user.login', came_from='/dataset/{id}'.format(id=id))
        )

    return dataset_view.read(package_type, id)


def resource_read(package_type, id, resource_id):
    """
    Override the default CKAN behaviour for private Dataset Resource visibility.
    Instead of displaying "404 Dataset not found" message,
    give unauthenticated users a chance to log in.
    :param id: Package id/name
    :param resource_id: Resource id
    :return:
    """
    import ckan.views.resource as resource_view
    if not g.user and not _is_dataset_public(id):
        redirect_to(
            url_for('user.login',
                    came_from='/dataset/{id}/resource/{resource_id}'.format(id=id, resource_id=resource_id))
        )

    return resource_view.read(package_type, id, resource_id)


_dataset.add_url_rule(u'', view_func=dataset_read)
_dataset.add_url_rule(u'/resource/<resource_id>', view_func=resource_read)


def get_blueprints():
    return [_dataset]
