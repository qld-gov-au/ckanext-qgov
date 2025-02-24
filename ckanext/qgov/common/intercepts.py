# encoding: utf-8
""" Monkey-patch CKAN core functions with our own implementations.
"""

from logging import getLogger
import re

from ckan import authz
from ckan.lib.navl.dictization_functions import Missing
from ckan.lib.navl.validators import ignore_missing, not_empty
from ckan.logic import schema as schemas, validators
from ckan.plugins.toolkit import _, get_or_bust, get_validator, \
    chained_action, side_effect_free

from .authenticator import unlock_account
from .user_creation import helpers as user_creation_helpers

LOG = getLogger(__name__)

DEFAULT_USER_SCHEMA = schemas.default_user_schema()
USER_NEW_FORM_SCHEMA = schemas.user_new_form_schema()
if hasattr(schemas, 'user_perform_reset_form_schema'):
    USER_PERFORM_RESET_FORM_SCHEMA = schemas.user_perform_reset_form_schema()
USER_EDIT_FORM_SCHEMA = schemas.user_edit_form_schema()
DEFAULT_UPDATE_USER_SCHEMA = schemas.default_update_user_schema()
RESOURCE_SCHEMA = schemas.default_resource_schema()


def configure(config):
    global password_min_length
    global password_patterns

    password_min_length = int(config.get('password_min_length', '10'))
    password_patterns = config.get(
        'password_patterns',
        r'.*[0-9].*,.*[a-z].*,.*[A-Z].*,.*[-`~!@#$%^&*()_+=|\\/ ].*'
    ).split(',')


def set_intercepts():
    """ Monkey-patch to wrap/override core functions with our own.
    Theoretically, some of these steps may be redundant,
    but to avoid race conditions (eg 'validators' read a value before we patched)
    we perform them all.
    """
    validators.user_password_validator = user_password_validator

    schemas.default_user_schema = default_user_schema
    schemas.user_new_form_schema = user_new_form_schema
    schemas.user_edit_form_schema = user_edit_form_schema
    if hasattr(schemas, 'user_perform_reset_form_schema'):
        schemas.user_perform_reset_form_schema = user_perform_reset_form_schema
    schemas.default_update_user_schema = default_update_user_schema
    schemas.default_resource_schema = default_resource_schema


def user_password_validator(key, data, errors, context):
    """ Strengthen the built-in password validation to require more length and complexity.
    """
    value = data[key]

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif len(value) < password_min_length:
        errors[('password',)].append(
            _('Your password must be {min} characters or longer'.format(min=password_min_length))
        )
    else:
        for policy in password_patterns:
            if not re.search(policy, value):
                errors[('password',)].append(
                    _('Must contain at least one number, lowercase letter, capital letter, and symbol')
                )


def _apply_schema_validator(user_schema, field_name, validator_name='user_password_validator',
                            validator=user_password_validator):
    if field_name in user_schema:
        for idx, user_schema_func in enumerate(user_schema[field_name]):
            if user_schema_func.__name__ == validator_name:
                user_schema[field_name][idx] = validator
                break
        else:
            user_schema[field_name].append(validator)
    return user_schema


def _remove_schema_validator(user_schema, field_name, validator):
    if field_name in user_schema\
            and validator in user_schema[field_name]:
        user_schema[field_name].remove(validator)
    return user_schema


def default_user_schema():
    """ Add our password validator function to the default list.
    """
    user_schema = DEFAULT_USER_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def user_new_form_schema():
    """ Apply our password validator function when creating a new user.
    """
    user_schema = USER_NEW_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def user_perform_reset_form_schema():
    """ Apply our password validator function when resetting a password.
    """
    user_schema = USER_PERFORM_RESET_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password1')
    return user_schema


def user_edit_form_schema():
    """ Apply our password validator function when editing an existing user.
    """
    user_schema = USER_EDIT_FORM_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    user_schema = _apply_schema_validator(user_schema, 'password1')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    return user_schema


def default_update_user_schema():
    """ Apply our password validator function when updating a user.
    """
    user_schema = DEFAULT_UPDATE_USER_SCHEMA
    user_schema = _apply_schema_validator(user_schema, 'password')
    _remove_schema_validator(user_schema, 'fullname', ignore_missing)
    user_schema = _apply_schema_validator(
        user_schema, 'fullname',
        validator_name='not_empty', validator=not_empty)
    user_schema = user_creation_helpers.add_custom_validator_to_user_schema(user_schema)
    return user_schema


def default_resource_schema():
    """ Add URL validators to the default resource schema.
    """
    resource_schema = RESOURCE_SCHEMA.copy()
    # We can't make an entirely shallow copy, or else it will be permanently
    # modified by eg schema.default_show_package_schema, but we don't want
    # infinite depth either.
    for key in resource_schema:
        resource_schema[key] = resource_schema[key][:]
    resource_schema['url'].append(get_validator('valid_url'))
    return resource_schema


@chained_action
@side_effect_free
def user_show(original_action, context, data_dict):
    '''
    Allow organisation admins to view email addresses.
    '''
    user = context.get('user')
    if not user:
        user_obj = context.get('auth_user_obj')
        if user_obj:
            user = user_obj.name
    if authz.has_user_permission_for_some_org(user, 'admin'):
        context['keep_email'] = True
    return original_action(context, data_dict)


@chained_action
def user_update(original_action, context, data_dict):
    '''
    Unlock an account when the password is reset.
    '''
    return_value = original_action(context, data_dict)
    if u'reset_key' in data_dict:
        account_id = get_or_bust(data_dict, 'id')
        unlock_account(account_id)
    return return_value
