# encoding: utf-8

'''Tests for the ckanext.qgov extension resource URL filter.
'''

from paste.registry import Registry
import pylons
import unittest

from ckan.lib.cli import MockTranslator
import ckan.lib.helpers as h

import intercepts


def mock_objects(config):
    registry = Registry()
    registry.prepare()
    registry.register(pylons.translator, MockTranslator())

    h.config = config


URL_DATA = [
    {'input': 'http://www.qld.gov.au'},
    {'input': 'https://www.qld.gov.au'},
    {'input': 'ftp://www.qld.gov.au'},
    {'input': 'www.qld.gov.au', 'expected': 'http://www.qld.gov.au'},
    {'input': 'git+https://github.com/ckan/ckan.git', 'expected': 'http://git+https://github.com/ckan/ckan.git'},
    {'input': 'example.pdf', 'expected': 'http://example.pdf', 'upload': False},
    {'input': 'example.pdf', 'upload': True},
]


class TestUrlValidation(unittest.TestCase):
    """ Test our URL validation.
    """

    def test_valid_urls(self):
        """ Test that URLs are checked against the allowed protocols,
        and http:// is prepended if they don't match.
        """
        key = ('resources', 0, 'url')
        mock_objects({})
        for test in URL_DATA:
            input_url = test.get('input')
            if test.get('upload', False):
                url_type = 'upload'
            else:
                url_type = 'link'
            print "Testing URL {} of type '{}'".format(input_url, url_type)
            flattened_data = {key: input_url, ('resources', 0, 'url_type'): url_type}
            intercepts.valid_url(key, flattened_data, None, None)
            self.assertEqual(flattened_data[key], test.get('expected', input_url))


if __name__ == '__main__':
    unittest.main()
