# encoding: utf-8
""" Some useful functions for interacting with the current request.
"""
from ckan.common import request


def get_post_params(field_name):
    """ Retrieve a list of all POST parameters with the specified name
    for the current request.

    This uses 'request.POST' for Pylons and 'request.form' for Flask.
    """
    if hasattr(request, 'form'):
        return request.form.getlist(field_name)
    else:
        return request.POST.getall(field_name)


def get_query_params(field_name):
    """ Retrieve a list of all GET parameters with the specified name
    for the current request.

    This uses 'request.GET' for Pylons and 'request.args' for Flask.
    """
    if hasattr(request, 'args'):
        return request.args.getlist(field_name)
    else:
        return request.GET.getall(field_name)


def delete_param(field_name):
    """ Remove the parameter with the specified name from the current
    request. This requires the request parameters to be mutable.
    """
    for collection_name in ['args', 'form', 'GET', 'POST']:
        collection = getattr(request, collection_name, {})
        if field_name in collection:
            del collection[field_name]


def scoped_attrs():
    """ Returns a mutable dictionary of attributes that exist in the
    scope of the current request, and will vanish afterward.
    """
    return request.environ['webob.adhoc_attrs']
