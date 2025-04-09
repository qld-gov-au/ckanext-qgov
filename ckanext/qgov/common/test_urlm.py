# encoding: utf-8

'''Tests for the ckanext.qgov extension integration with PURL.
'''

from . import urlm


class TestUrlm():
    """ Test PURL redirects.
    """

    def test_purl_redirect(self):
        """ Test that PURL is consulted to find redirects.
        """
        urlm.configure_urlm('https://test.smartservice.qld.gov.au/services/url/translate/v3.json?sourceurl={source}', None)
        location = urlm.get_purl_response('https://www.qld.gov.au/data')
        assert '//data.qld.gov.au/' in location

    def test_purl_missing_redirect(self):
        """ Test that PURL returns blank when no redirect exists.
        """
        urlm.configure_urlm('https://test.smartservice.qld.gov.au/services/url/translate/v3.json?sourceurl={source}', None)
        assert urlm.get_purl_response('http://example.com') is None
