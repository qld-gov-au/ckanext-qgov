from ckanext.data_qld.user_creation import validators as user_creation_validators


def is_validator_exist(field_schema, validator_name):
    for idx, schema_func in enumerate(field_schema):
        if schema_func.__name__ == validator_name:
            return True

    return False


def add_custom_validator_to_user_schema(schema):
    if not is_validator_exist(schema['name'], 'data_qld_user_name_validator'):
        schema['name'].append(user_creation_validators.data_qld_user_name_validator)

    if not is_validator_exist(schema['fullname'], 'data_qld_displayed_name_validator'):
        schema['fullname'].append(user_creation_validators.data_qld_displayed_name_validator)

    return schema
