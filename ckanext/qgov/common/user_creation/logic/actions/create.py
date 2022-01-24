import ckan.plugins.toolkit as toolkit
import ckan.logic.schema as schema

from ckanext.data_qld.user_creation import helpers as user_creation_helpers


@toolkit.chained_action
def user_create(original_action, context, data_dict):
    modified_schema = context.get('schema') or schema.default_user_schema()
    context['schema'] = user_creation_helpers.add_custom_validator_to_user_schema(modified_schema)
    return original_action(context, data_dict)
