# encoding: utf-8

'''Tests for the ckanext.qgov extension resource URL filter.
'''

from paste.registry import Registry
import pylons
import unittest

from ckan.lib.cli import MockTranslator
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as df

import plugin


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

VALID_RESOURCE_URLS = [
    # No whitelist/blacklist; any domain is ok
    {'url_cases': [{'input': 'http://foo'}, {'input': 'https://google.com'}, {'input': 'example.com', 'expected': 'http://example.com'}]},
    # Domain matches whitelist
    {'whitelist': 'gov.au translink.com.au', 'url_cases': [{'input': 'http://www.translink.com.au'}, {'input': 'https://www.qld.gov.au'}, {'input': 'www.qld.gov.au', 'expected': 'http://www.qld.gov.au'}]},
    # Domain does not match blacklist
    {'blacklist': 'evil.com', 'url_cases': [{'input': 'https://example.com'}, {'input': 'http://evil.com.au'}]},
    {'blacklist': '1.2.3.4', 'url_cases': [{'input': 'https://example.com.1.2.3.4'}]},
    {'blacklist': 'private', 'url_cases': [
        {'input': 'http://www.qld.gov.au'},
        {'input': 'http://example.com'},
        {'input': 'http://1.0.0.0'},
        {'input': 'http://9.255.255.255'},
        {'input': 'http://11.0.0.0'},
        {'input': 'http://20.0.0.0'},
        {'input': 'http://126.255.255.255'},
        {'input': 'http://128.0.0.0'},
        {'input': 'http://169.253.255.255'},
        {'input': 'http://169.255.0.0'},
        {'input': 'http://172.15.255.255'},
        {'input': 'http://172.32.0.0'},
        {'input': 'http://192.167.255.255'},
        {'input': 'http://192.169.0.0'},
    ]},
    # Domains matches whitelist and does not match blacklist
    {'whitelist': 'gov.au translink.com.au', 'blacklist': '127.0.0.1', 'url_cases': [{'input': 'http://www.qld.gov.au'}]},
    # File upload skips whitelist and blacklist
    {'whitelist': 'gov.au translink.com.au', 'url_cases': [{'input': 'example.pdf'}, {'input': 'https://www.qld.gov.au/example.pdf'}, {'input': 'www.qld.gov.au/example.csv'}], 'upload': True},
    {'blacklist': 'example.pdf', 'url_cases': [{'input': 'example.pdf'}], 'upload': True},
]

INVALID_RESOURCE_URLS = [
    # Domain does not match whitelist
    {'whitelist': 'gov.au translink.com.au', 'url_cases': ['http://www.example.com', 'https://data.gov']},
    # Hostname matches blacklist or resolves to an address on the blacklist
    {'blacklist': '127.0.0.1 evil.com', 'url_cases': ['https://evil.com', 'http://subdomain.evil.com', 'http://127.0.0.1/', 'http://localhost/']},
    {'blacklist': 'private', 'url_cases': [
        'http://127.0.0.1/',
        'http://localhost/',
        'http://0.0.0.0/',
        'http://0.255.255.255/',
        'http://10.0.0.0/',
        'http://10.255.255.255/',
        'http://169.254.0.0:1234/latest/',
        'http://169.254.255.255',
        'http://172.16.0.0/',
        'http://172.31.255.255/',
        'http://192.168.0.0/',
        'http://192.168.255.255/',
    ]},
    # Hostname matches both whitelist and blacklist
    {'whitelist': 'example.com', 'blacklist': 'example.com', 'url_cases': ['http://example.com']},
    {'whitelist': 'localhost', 'blacklist': '127.0.0.1', 'url_cases': ['http://localhost/']},
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
            plugin.valid_url(key, flattened_data, None, None)
            self.assertEqual(flattened_data[key], test.get('expected', input_url))

    def test_valid_hostnames(self):
        """ Test that hostnames are accepted when they pass whitelist/blacklist
        validation, if any.
        """
        key = ('resources', 0, 'url')
        for test in VALID_RESOURCE_URLS:
            config = {'ckanext.qgov.resource_domains.whitelist': test.get('whitelist', ''),
                      'ckanext.qgov.resource_domains.blacklist': test.get('blacklist', '')}
            mock_objects(config)
            qgov_plugin = plugin.QGOVPlugin()
            qgov_plugin.configure(config)
            for case in test['url_cases']:
                input_url = case.get('input')
                print "Testing valid URL {} with whitelist [{}] and blacklist [{}]".format(input_url, test.get('whitelist', ''), test.get('blacklist', ''))
                if test.get('upload', False):
                    url_type = 'upload'
                else:
                    url_type = 'link'
                flattened_data = {key: input_url, ('resources', 0, 'url_type'): url_type}
                plugin.valid_resource_url(key, flattened_data, None, None)
                self.assertEqual(flattened_data[key], case.get('expected', input_url))

    def test_invalid_hostnames(self):
        """ Test that hostnames are rejected when they match the blacklist
        or do not match the whitelist.
        """
        key = ('resources', 0, 'url')
        for test in INVALID_RESOURCE_URLS:
            config = {'ckanext.qgov.resource_domains.whitelist': test.get('whitelist', ''),
                      'ckanext.qgov.resource_domains.blacklist': test.get('blacklist', '')}
            mock_objects(config)
            qgov_plugin = plugin.QGOVPlugin()
            qgov_plugin.configure(config)
            for case in test['url_cases']:
                print "Testing invalid URL {} with whitelist {} and blacklist {}".format(case, test.get('whitelist', ''), test.get('blacklist', ''))
                if test.get('upload', False):
                    url_type = 'upload'
                else:
                    url_type = 'link'
                flattened_data = {key: case, ('resources', 0, 'url_type'): url_type}
                self.assertRaises(df.Invalid, plugin.valid_resource_url, key, flattened_data, None, None)

    def test_default_blacklist(self):
        """ Test that the blacklist defaults to 'private' if not provided.
        """
        mock_objects({})
        qgov_plugin = plugin.QGOVPlugin()
        qgov_plugin.configure({})
        key = ('resources', 0, 'url')
        for input_url in ['http://127.0.0.1', 'localhost']:
            print "Testing private URL {}".format(input_url)
            flattened_data = {key: input_url}
            self.assertRaises(df.Invalid, plugin.valid_resource_url, key, flattened_data, None, None)


if __name__ == '__main__':
    unittest.main()
