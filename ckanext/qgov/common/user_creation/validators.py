from ckan.plugins import toolkit


def _get_user():
    """ Retrieve the current user object.
    """
    # 'g' is not a regular data structure so we can't use 'hasattr'
    if 'userobj' in dir(toolkit.g):
        return toolkit.g.userobj
    else:
        return None


def data_qld_user_name_validator(key, data, errors, context):
    user = _get_user()
    is_sysadmin = user is not None and user.sysadmin

    if not is_sysadmin and 'publisher' in data[key].lower() and user.name.lower() != data[key].lower():
        raise toolkit.Invalid("The username cannot contain the word 'publisher'. Please enter another username.")


def data_qld_displayed_name_validator(key, data, errors, context):
    user = _get_user()
    is_sysadmin = user is not None and user.sysadmin

    if not is_sysadmin:
        excluded_names = toolkit.config.get('ckanext.data_qld.excluded_display_name_words', '').split('\r\n')
        for name in excluded_names:
            # In some case, name value can be "   ", we need to remove the space.
            if name.strip() and name.strip().lower() in data[key].lower():
                raise toolkit.Invalid(
                    "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name.")
