# encoding: utf-8

from ckan import authz, model
from ckan.logic import auth as logic_auth
from ckan.plugins.toolkit import _, asbool, auth_allow_anonymous_access

from helpers import user_has_admin_access


def member_create(context, data_dict):
    """
    This code is largely borrowed from /src/ckan/ckan/logic/auth/create.py
    With a modification to allow users to add datasets to any group
    :param context:
    :param data_dict:
    :return:
    """
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']

    if not group.is_organization and data_dict.get('object_type') == 'package':
        authorized = user_has_admin_access(True)
    else:
        authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit group %s') %
                        (user, group.id)}
    else:
        return {'success': True}


def related_create(context, data_dict=None):
    '''
    Override default related_create so;
    - Users must be logged-in to create related items
    - Related item must be created for an associated dataset
    - User must be able to create datasets (proves privilege)

    Note: This function is used both to gain entry to the 'Create' form
    and to validate the 'Create' form
    '''
    context_model = context['model']
    user = context['user']
    userobj = context_model.User.get(user)

    check1 = all(authz.check_config_permission(p) for p in (
        'create_dataset_if_not_in_organization',
        'create_unowned_dataset',
    )) or authz.has_user_permission_for_some_org(
        user, 'create_dataset')

    if userobj and check1:
        if data_dict:
            dataset_id = data_dict.get('dataset_id', None)
            if dataset_id is None or dataset_id == '':
                return {'success': False,
                        'msg': _('''Related item must have
                                    an associated dataset''')}
            # check authentication against package
            pkg = context_model.Package.get(dataset_id)
            if not pkg:
                return {'success': False,
                        'msg': _('No package found, cannot check auth.')}

            pkg_dict = {'id': dataset_id}
            authorised = authz.is_authorized(
                'package_update',
                context,
                pkg_dict).get('success')
            if not authorised:
                return {'success': False,
                        'msg': _('''Not authorised to add a related item
                                    to this package.''')}

        return {'success': True}

    return {'success': False,
            'msg': _('You must be logged in to add a related item')}


def related_update(context, data_dict):
    '''
    Override default related_update so;
    - Users must be logged-in to create related items
    - User can update if they are able to create datasets for housed package
    '''
    user = context['user']

    check1 = all(authz.check_config_permission(p) for p in (
        'create_dataset_if_not_in_organization',
        'create_unowned_dataset',
    )) or authz.has_user_permission_for_some_org(
        user, 'create_dataset')

    if user and check1:
        related = logic_auth.get_related_object(context, data_dict)
        if related.datasets:
            for package in related.datasets:
                pkg_dict = {'id': package.id}
                authorised = authz.is_authorized(
                    'package_update',
                    context,
                    pkg_dict).get('success')
                if authorised:
                    return {'success': True}

            return {'success': False,
                    'msg': _('''You do not have permission
                                to update this related item''')}
    return {'success': False,
            'msg': _('''You must be logged in and have permission
                        to create datasets to update a related item''')}


def user_list(context, data_dict=None):
    """Check whether access to the user list is authorised.
    Restricted to organisation admins as per QOL-5710.
    """
    return {'success': _requester_is_admin(context)}


def user_show(context, data_dict):
    """Check whether access to individual user details is authorised.
    Restricted to organisation admins or self, as per QOL-5710.
    """
    if _requester_is_admin(context):
        return {'success': True}
    requester = context.get('user')
    id = data_dict.get('id', None)
    if id:
        user_obj = model.User.get(id)
    else:
        user_obj = data_dict.get('user_obj', None)
    if user_obj:
        return {'success': requester == user_obj.name}

    return {'success': False}


@auth_allow_anonymous_access
def group_show(context, data_dict):
    """Check whether access to a group is authorised.
    If it's just the group metadata, this requires no privileges,
    but if user details have been requested, it requires a group admin.
    """
    user = context.get('user')
    group = logic_auth.get_group_object(context, data_dict)
    if group.state == 'active' and \
        not asbool(data_dict.get('include_users', False)) and \
            data_dict.get('object_type', None) != 'user':
        return {'success': True}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if authorized:
        return {'success': True}
    else:
        return {'success': False,
                'msg': _('User %s not authorized to read group %s') % (user, group.id)}


def _requester_is_admin(context):
    """Check whether the current user has admin privileges in some group
    or organisation.
    This is based on the 'update' privilege; see eg
    ckan.logic.auth.update.group_edit_permissions.
    """
    requester = context.get('user')
    return _has_user_permission_for_some_group(requester, 'admin')


def _has_user_permission_for_some_group(user_name, permission):
    """Check if the user has the given permission for any group.
    """
    user_id = authz.get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    roles = authz.get_roles_with_permission(permission)

    if not roles:
        return False
    # get any groups the user has with the needed role
    q = model.Session.query(model.Member) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.capacity.in_(roles)) \
        .filter(model.Member.table_id == user_id)
    group_ids = []
    for row in q.all():
        group_ids.append(row.group_id)
    # if not in any groups has no permissions
    if not group_ids:
        return False

    # see if any of the groups are active
    q = model.Session.query(model.Group) \
        .filter(model.Group.state == 'active') \
        .filter(model.Group.id.in_(group_ids))

    return bool(q.count())
