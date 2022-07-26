# encoding: utf-8
""" Functions for URL Management System interaction.
"""

from logging import getLogger
import requests

from ckan.plugins.toolkit import request

LOG = getLogger(__name__)

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


def get_purl_response(url):
    global URLM_ENDPOINT, URLM_PROXY
    LOG.warn("Page [%s] not found; checking URL Management System at %s",
             url, URLM_ENDPOINT)
    purl_request = URLM_ENDPOINT.format(source=request.url)
    try:
        if URLM_PROXY:
            kwargs = {'proxies': {'http': 'http://' + URLM_PROXY, 'https': 'https://' + URLM_PROXY}}
        else:
            kwargs = {}
        response = requests.get(purl_request, **kwargs).json()
        if response['Status'] == 301:
            location = response['Headers']['location']
            LOG.info("Found; redirecting to %s", location)
            return location
        else:
            LOG.warn("No match in URL Management System")
    except requests.exceptions.RequestException as ex:
        LOG.error("Failed to contact URL Management system: %s", ex)
