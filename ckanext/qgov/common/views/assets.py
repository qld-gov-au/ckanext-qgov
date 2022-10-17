# encoding: utf-8

import logging

from flask import Blueprint

import re
from ckan.plugins.toolkit import g, redirect_to, ObjectNotFound, render, h

LOG = logging.getLogger(__name__)
INCLUDED_BUNDLES = None

blueprint = Blueprint(
    u'asset_redirects',
    __name__,
    url_prefix=u'/assets/'
)


def init():
    LOG.debug("Run init()")
    render(u'page.html')
    global INCLUDED_BUNDLES
    INCLUDED_BUNDLES = g.webassets[u'included'].copy()
    g.webassets[u'included'].clear()
    LOG.debug("INCLUDED_BUNDLES: %s", INCLUDED_BUNDLES)


def any_redirect(asset_type, name):
    global INCLUDED_BUNDLES
    if INCLUDED_BUNDLES is None:
        init()
    for bundle in INCLUDED_BUNDLES:
        h.include_asset(bundle)
    LOG.debug("Asset type and Name: %s, %s", asset_type, name)
    LOG.debug("Styles: %s", g.webassets[u'style'])
    for style in g.webassets[u'style']:
        pattern = re.search('/webassets/' + asset_type + '/[0-9a-f]*[_-]' + name + '.(css|js)')
        if pattern.search(style):
            return redirect_to(style)
    raise ObjectNotFound(u'No assets match')


blueprint.add_url_rule(u'<asset_type>/<name>', view_func=any_redirect)


def get_blueprints():
    return [blueprint]
