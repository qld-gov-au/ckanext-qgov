# encoding: utf-8

'''Tests for the ckanext.qgov extension CSRF filter.
'''

import re, unittest
import anti_csrf
from anti_csrf import *
from ckan.common import request, response, g

NUMBER_FIELDS = re.compile(r'(![0-9]+)/([0-9]+)/')

class TestAntiCsrfFilter(unittest.TestCase):

    def mock_objects(self, username='unit-test'):
        import urllib
        anti_csrf._get_safe_username = lambda: urllib.quote(username, safe='')
        anti_csrf._get_secret_key = lambda: 'secret'
        anti_csrf._set_response_token_cookie = lambda token: token

    def test_read_token_values(self):
        good_token = 'hash!123/456/someuser'
        expected_value = {
            "hash": unicode("hash"),
            "message": "123/456/someuser",
            "timestamp": 123,
            "nonce": 456,
            "username": "someuser"
        }
        bad_tokens = [
            'aaa',
            good_token.replace('/', '!'),
            NUMBER_FIELDS.sub(r'\1a/\2/', good_token),
            NUMBER_FIELDS.sub(r'\1/\2a/', good_token)
        ]

        print "Testing good token '{}'".format(good_token)
        self.assertEqual(read_token_values(good_token), expected_value)
        for bad_token in bad_tokens:
            print "Testing bad token '{}'".format(bad_token)
            self.assertEqual(read_token_values(bad_token), {})

    def test_validate_token(self):
        self.mock_objects()

        good_token = create_response_token()
        bad_tokens = [
            good_token.replace('unit-test', 'evil-unit-test'),
            NUMBER_FIELDS.sub(r'!123/\2/', good_token),
            NUMBER_FIELDS.sub(r'\1/123/', good_token)
        ]

        print "Testing good token {}".format(good_token)
        self.assertTrue(validate_token(good_token))
        for bad_token in bad_tokens:
            print "Testing invalid token '{}'".format(bad_token)
            self.assertFalse(validate_token(bad_token))

    def test_username_with_slash(self):
        self.mock_objects('abc_123')
        bad_token = create_response_token()
        self.mock_objects('abc/123')
        good_token = create_response_token()

        print "Testing good token '{}'".format(good_token)
        self.assertTrue(validate_token(good_token))
        print "Testing wrong user token '{}'".format(bad_token)
        self.assertFalse(validate_token(bad_token))

if __name__ == '__main__':
    unittest.main()
