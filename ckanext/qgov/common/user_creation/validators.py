# encoding: utf-8

from ckan.plugins.toolkit import config, g, Invalid


def _get_user():
    """ Retrieve the current user object.
    """
    # 'g' is not a regular data structure so we can't use 'hasattr'
    if 'userobj' in dir(g):
        return g.userobj
    else:
        return None


def data_qld_user_name_validator(key, data, errors, context):
    if context and context.get('reset_password', False):
        return
    user = _get_user()
    if user is None:
        is_sysadmin = False
        old_username = None
    else:
        is_sysadmin = user.sysadmin
        old_username = user.name.lower()
    new_username = data[key].lower()

    if not is_sysadmin and 'publisher' in new_username and old_username != new_username:
        raise Invalid("The username cannot contain the word 'publisher'. Please enter another username.")


def data_qld_displayed_name_validator(key, data, errors, context):
    if context and context.get('reset_password', False):
        return
    user = _get_user()
    if user is None:
        is_sysadmin = False
        old_name = None
    else:
        is_sysadmin = user.sysadmin
        old_name = (user.fullname or '').lower()
    new_name = data[key].lower()

    if not is_sysadmin and old_name != new_name:
        excluded_names = config.get('ckanext.data_qld.excluded_display_name_words', '').split('\r\n')
        for name in excluded_names:
            # In some case, name value can be "   ", we need to remove the space.
            if name.strip() and name.strip().lower() in new_name:
                raise Invalid(
                    "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name.")
