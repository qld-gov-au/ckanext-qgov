# encoding: utf-8

from ckan import model
from ckan.plugins.toolkit import config, g, Invalid


def _get_user(context):
    """ Retrieve the current user object.
    """
    if 'userobj' in context:
        return context.get('userobj')
    if 'user' in context:
        return model.User.get(context.get('user'))

    # 'g' is not a regular data structure so we can't use 'hasattr'
    if 'userobj' in dir(g):
        user = g.userobj
        if isinstance(user, str):
            user = model.User.get(user)
        return user
    else:
        return None


def data_qld_user_name_validator(key, data, errors, context):
    if context and context.get('reset_password', False):
        return
    user = _get_user(context)
    if user:
        if user.sysadmin:
            return
        # Retrieving this from the authorising account, instead of the target,
        # is not ideal, but so long as non-sysadmins can only edit their own profiles,
        # the logic is correct.
        # Is there a way to reliably retrieve the target account
        # when all we know is the new name?
        old_username = user.name.lower()
    else:
        old_username = None
    new_username = data[key].lower()

    if 'publisher' in new_username and old_username != new_username:
        raise Invalid("The username cannot contain the word 'publisher'. Please enter another username.")


def data_qld_displayed_name_validator(key, data, errors, context):
    if context and context.get('reset_password', False):
        return
    user = _get_user(context)
    if user:
        if user.sysadmin:
            return
        old_name = (user.fullname or '').lower()
    else:
        old_name = None
    new_name = data[key].lower()

    if old_name != new_name:
        excluded_names = config.get('ckanext.data_qld.excluded_display_name_words', '').split('\r\n')
        for name in excluded_names:
            # In some case, name value can be "   ", we need to remove the space.
            if name.strip() and name.strip().lower() in new_name:
                raise Invalid(
                    "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name.")
