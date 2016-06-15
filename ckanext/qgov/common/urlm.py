import ckan.lib.base as base
from ckan.lib.base import request

import json
from pylons.controllers.util import redirect

from logging import getLogger
LOG = getLogger(__name__)

RAW_ABORT = base.abort

def configure_for_environment(site_url):
    global URLM_ENDPOINT, URLM_PROXY
    if 'staging' in site_url:
        URLM_ENDPOINT = 'https://test.smartservice.qld.gov.au/services/url/translate/v3.json?sourceurl={source}'
    elif site_url.endswith('-tst'):
        URLM_ENDPOINT = 'https://test.smartservice.qld.gov.au/services/url/translate/v3.json?sourceurl={source}'
        URLM_PROXY = 'proxy:3128'
    elif site_url.endswith('-local'):
        URLM_ENDPOINT = 'http://localhost:8091/url/translate/v3.json?sourceurl={source}'
        URLM_PROXY = 'proxy:3128'
    else:
        URLM_ENDPOINT = 'https://www.smartservice.qld.gov.au/services/url/translate/v3.json?sourceurl={source}'

    LOG.info("Using URL Management system at {endpoint} via proxy {proxy}".format(endpoint=URLM_ENDPOINT, proxy=URLM_PROXY))

def intercept_404():
    base.abort = abort_with_purl

def abort_with_purl(status_code=None, detail='', headers=None, comment=None):
    if status_code == 404:
        global URLM_ENDPOINT, URLM_PROXY
        LOG.warn("Page [{path}] not found; checking URL Management system at {endpoint}".format(path=request.url, endpoint=URLM_ENDPOINT))
        purl_request = URLM_ENDPOINT.format(source = request.url)
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

