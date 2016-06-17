import ckan.lib.base as base

from pylons.controllers.util import redirect

from logging import getLogger
LOG = getLogger(__name__)

RAW_ABORT = base.abort

def configure_for_environment(site_url):
    if 'staging' in site_url:
        endpoint = 'https://test.smartservice.qld.gov.au/services/url'
    elif site_url.endswith('-tst'):
        endpoint = 'https://test.smartservice.qld.gov.au/services/url'
        proxy = 'proxy:3128'
    elif site_url.endswith('-local'):
        endpoint = 'http://localhost:8091/url'
        proxy = 'proxy:3128'
    else:
        endpoint = 'https://www.smartservice.qld.gov.au/services/url'

    configure_urlm(endpoint, proxy)

def configure_urlm(app_path, proxy):
    """
    app_path: The path to the URL Management system, eg
    https://www.smartservice.qld.gov.au/services/url

    proxy: The proxy, if any, to be used in contacting the URL Management system.
    """
    global URLM_ENDPOINT, URLM_PROXY
    URLM_ENDPOINT = app_path + '/translate/v3.json?sourceurl={source}'
    URLM_PROXY = proxy

    LOG.info("Using URL Management system at {endpoint} via proxy {proxy}".format(endpoint=URLM_ENDPOINT, proxy=URLM_PROXY))

def intercept_404():
    base.abort = abort_with_purl

def abort_with_purl(status_code=None, detail='', headers=None, comment=None):
    if status_code == 404:
        global URLM_ENDPOINT, URLM_PROXY
        LOG.warn("Page [{path}] not found; checking URL Management system at {endpoint}".format(path=base.request.url, endpoint=URLM_ENDPOINT))
        purl_request = URLM_ENDPOINT.format(source = base.request.url)
        try:
            import json, urllib2
            if URLM_PROXY == None:
                r = urllib2.urlopen(purl_request)
            else:
                r = urllib2.build_opener(urllib2.ProxyHandler({'http': 'http://' + URLM_PROXY, 'https': 'https://' + URLM_PROXY})).open(purl_request)
            response = json.load(r)
            if response['Status'] == 301:
                location = response['Headers']['location']
                LOG.info("Found; redirecting to {location}".format(location=location))
                redirect(location, 301)
                return
            else:
                LOG.warn("No match in URL Management system")
        except urllib2.URLError, e:
            LOG.error("Failed to contact URL Management system: {error}".format(error=e))
            pass
    return RAW_ABORT(status_code, detail, headers, comment)

