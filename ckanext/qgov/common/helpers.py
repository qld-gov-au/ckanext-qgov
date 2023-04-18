# encoding: utf-8

import datetime
import json
import logging
import random
import requests

from bs4 import BeautifulSoup

from ckan import model
from ckan.lib import formatters
from ckan.plugins import toolkit
from ckan.plugins.toolkit import _, g, h, get_action

LOG = logging.getLogger(__name__)


def make_uncached_response(response):
    response.headers.set('cache-control', 'no-cache'),
    response.headers.set('Pragma', 'no-cache')
    return response


def format_attribution_date(date_string=None):
    """ Format a date nicely.
    """
    if date_string:
        dateobj = datetime.datetime.strptime(date_string.split('T')[0],
                                             '%Y-%m-%d')
    else:
        dateobj = datetime.datetime.now()
    return dateobj.strftime('%d %B %Y')


def format_resource_filesize(size):
    """ Show a file size, formatted for humans.
    """
    try:
        return formatters.localised_filesize(int(size))
    except ValueError:
        # assume it's already formatted
        return size


def group_id_for(group_name):
    """ Determine the ID for a provided group name, if any.
    """
    group = model.Group.get(group_name)

    if group and group.is_active():
        return group.id

    LOG.error("%s group was not found or not active", group_name)
    return None


def organisation_list():
    """Returns a list of organisations with all the organisation fields

    :rtype: Array of organisations

    """
    return toolkit.get_action('organization_list')(data_dict={'all_fields': True})


def random_tags():
    """ Show the most-used tags in a random order.
    """
    tags = h.unselected_facet_items('tags', limit=15)
    random.shuffle(tags)
    return tags


def user_has_admin_access(include_editor_access):
    user = toolkit.c.userobj
    # If user is "None" - they are not logged in.
    if user is None:
        return False
    if user.sysadmin:
        return True

    groups_admin = user.get_groups('organization', 'admin')
    groups_editor = user.get_groups('organization', 'editor') if include_editor_access else []
    groups_list = groups_admin + groups_editor
    organisation_list = [g for g in groups_list if g.type == 'organization']
    return len(organisation_list) > 0


def format_activity_data(data):
    """Returns the activity data with actors username replaced with Publisher for non-editor/admin/sysadmin users

    :rtype: string

    """
    if (user_has_admin_access(True)):
        return data

    soup = BeautifulSoup(data, 'html.parser')

    for actor in soup.select(".actor"):
        actor.string = 'Publisher'
        # the img element is removed from actor span so need to move actor span to the left to fill up blank space
        actor['style'] = 'margin-left:-40px'

    return soup.prettify(formatter="html5")


def activity_type_nice(activity_type):
    """Performs some replacement and rearrangement of the activity type for display in the activity notification email
    :rtype: string
    """
    activity_type = activity_type.replace('organization', _('organization'))
    activity_type = activity_type.replace('package', 'dataset')
    activity_type = activity_type.split()
    activity_type.reverse()
    return ' '.join(activity_type)


def get_resource_name(data_dict):
    """ Retrieve the name of a resource given its ID.
    """
    context = {'ignore_auth': False, 'model': model,
               'user': g.user}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources', [])
        for resource in resources:
            if data_dict['resource_id'] == resource['id']:
                return resource['name']
        return None
    return None


def generate_download_url(package_id, resource_id):
    """ Construct a URL to download a resource given its ID.
    """
    context = {'ignore_auth': False, 'model': model,
               'user': g.user}
    try:
        resource = get_action('resource_show')(context, {"id": resource_id})
        if 'error' not in resource:
            return resource.get('url')
    except Exception:
        return ''


def generate_json_schema(package_id, validation_schema):
    """ Retrieve the validation schema for a package, if any.
    """
    validation_schema_url = generate_download_url(package_id,
                                                  validation_schema)
    req = requests.get(validation_schema_url, verify=False)
    if req.status_code == requests.codes.ok:
        try:
            return json.loads(req.text)
        except Exception:
            return {"error": "Failed to parse json schema"}
    else:
        return {"error": "Failed to retrieve json schema"}


def get_validation_resources(data_dict):
    """ Return the validation schemas associated with a package.
    """
    context = {'ignore_auth': False, 'model': model, 'user': g.user}
    package = get_action('package_show')(context, data_dict)
    if 'error' not in package:
        resources = package.get('resources', [])
        validation_schemas = []
        for resource in resources:
            if resource['format'].upper() == 'CSV VALIDATION SCHEMA':
                validation_schemas.append(resource['id'])
        return validation_schemas
    return package
