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


def init():
    render(u'page.html')
    global INCLUDED_BUNDLES
    INCLUDED_BUNDLES = g.webassets[u'included'].copy()
    g.webassets[u'included'].clear()


def any_redirect(extension, name):
    if INCLUDED_BUNDLES is None:
        init()
    for bundle in INCLUDED_BUNDLES:
        h.include_asset(bundle)
    if extension == u'css':
        asset_type = u'style'
    elif extension == u'js':
        asset_type = u'script'
    else:
        raise ObjectNotFound(u'Extension must be either "css" or "js"')
    pattern = '/webassets/[a-zA-Z_-]*/[0-9a-f]*[_-]' + name + '.' + extension
    for asset in g.webassets[asset_type]:
        if re.search(pattern, asset):
            return redirect_to(asset)
    raise ObjectNotFound(u'No assets match pattern: %s', pattern)


blueprint.add_url_rule(u'<extension>/<name>', view_func=any_redirect)


def get_blueprints():
    return [blueprint]
