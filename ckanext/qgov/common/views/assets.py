# encoding: utf-8

from flask import Blueprint

import re
from ckan.plugins.toolkit import g, redirect_to, ObjectNotFound, render, h

INCLUDED_BUNDLES = None

blueprint = Blueprint(
    u'asset_redirects',
    __name__,
    url_prefix=u'/assets/'
)


def get_included_bundles():
    global INCLUDED_BUNDLES
    if INCLUDED_BUNDLES is None:
        render(u'page.html')
        INCLUDED_BUNDLES = g.webassets[u'included'].copy()
        g.webassets[u'included'].clear()
    return INCLUDED_BUNDLES


def any_redirect(extension, name):
    for bundle in get_included_bundles():
        h.include_asset(bundle)
    if extension == u'css':
        asset_type = u'style'
    elif extension == u'js':
        asset_type = u'script'
    else:
        raise ObjectNotFound(u'Extension must be either "css" or "js"')
    pattern = '/webassets/[a-zA-Z_-]*/[0-9a-f]*[_-]{}.{}'.format(name, extension)
    for asset in g.webassets[asset_type]:
        if re.search(pattern, asset):
            return redirect_to(asset)
    raise ObjectNotFound(u'No assets match: {}.{}'.format(name, extension))


blueprint.add_url_rule(u'<extension>/<name>', view_func=any_redirect)


def get_blueprints():
    return [blueprint]
