# encoding: utf-8
""" Functions for URL Management System interaction.
"""
from logging import getLogger

from ckan.lib import base
from ckan.controllers import group
from ckan.controllers import package, user
from ckan.lib import helpers

LOG = getLogger(__name__)

RAW_ABORT = base.abort
URLM_ENDPOINT = None
URLM_PROXY = None


def configure_urlm(app_path, proxy):
    """
    app_path: The path to the URL Management system
    proxy: The proxy, if any, to be used in contacting the URL Management system.
    """
    global URLM_ENDPOINT, URLM_PROXY
    URLM_ENDPOINT = app_path
    URLM_PROXY = proxy

    LOG.info("Using URL Management system at %s via proxy %s", URLM_ENDPOINT, URLM_PROXY)


def intercept_404():
    """ Monkey-patch ourselves into the 404 handler.
    """
    base.abort = abort_with_purl
    group.abort = base.abort
    package.abort = base.abort
    # related.abort = base.abort
    user.abort = base.abort


def abort_with_purl(status_code=None, detail='', headers=None, comment=None):
    """ Consult PURL about a 404, redirecting if it reports a new URL.
    """
    if status_code == 404:
        global URLM_ENDPOINT, URLM_PROXY
        LOG.warn("Page [%s] not found; checking URL Management System at %s",
                 base.request.url, URLM_ENDPOINT)
        purl_request = URLM_ENDPOINT.format(source=base.request.url)
        try:
            import json
            import urllib2
            if URLM_PROXY:
                proxy_handler = urllib2.ProxyHandler(
                    {'http': 'http://' + URLM_PROXY, 'https': 'https://' + URLM_PROXY}
                )
                req = urllib2.build_opener(proxy_handler).open(purl_request)
            else:
                req = urllib2.urlopen(purl_request)
            response = json.load(req)
            if response['Status'] == 301:
                location = response['Headers']['location']
                LOG.info("Found; redirecting to %s", location)
                helpers.redirect_to(location, 301)
                return
            else:
                LOG.warn("No match in URL Management System")
        except urllib2.URLError as ex:
            LOG.error("Failed to contact URL Management system: %s", ex)

    return RAW_ABORT(status_code, detail, headers, comment)
