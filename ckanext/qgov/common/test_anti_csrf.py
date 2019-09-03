# encoding: utf-8

'''Tests for the ckanext.qgov extension CSRF filter.
'''

import re
import unittest

import anti_csrf

NUMBER_FIELDS = re.compile(r'(![0-9]+)/([0-9]+)/')
STUB_TOKEN = 'some_token_or_other'

class MockUser(object):
    """ Stub class to represent a logged-in user.
    """

    def __init__(self, name):
        """ Set up a stub name to return.
        """
        self.name = name

def mock_objects(username='unit-test'):
    """ Monkey-patch necessary functions in the CSRF filter to imitate core CKAN.
    """
    anti_csrf._get_user = lambda: MockUser(username)
    anti_csrf._get_response_token = lambda: STUB_TOKEN
    anti_csrf._get_secret_key = lambda: 'secret'
    anti_csrf._set_response_token_cookie = lambda token: token

class TestAntiCsrfFilter(unittest.TestCase):
    """ Test our anti-CSRF filter with mock CKAN objects.
    """

    def test_read_token_values(self):
        """ Test that tokens are parsed correctly. Note that invalid tokens are parsed as blanks.
        """
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
        self.assertEqual(anti_csrf.read_token_values(good_token), expected_value)
        for bad_token in bad_tokens:
            print "Testing bad token '{}'".format(bad_token)
            self.assertEqual(anti_csrf.read_token_values(bad_token), {})

    def test_validate_token(self):
        """ Test that tokens are properly validated.
        Correct format, current timestamp, HMAC integrity check passed.
        """
        mock_objects()

        good_token = anti_csrf.create_response_token()
        bad_tokens = [
            good_token.replace('unit-test', 'evil-unit-test'),
            good_token.replace('!', 'x!'),
            NUMBER_FIELDS.sub(r'!123/\2/', good_token),
            NUMBER_FIELDS.sub(r'\1/123/', good_token)
        ]

        print "Testing good token {}".format(good_token)
        self.assertTrue(anti_csrf.validate_token(good_token))
        for bad_token in bad_tokens:
            print "Testing invalid token '{}'".format(bad_token)
            self.assertFalse(anti_csrf.validate_token(bad_token))
            self.assertFalse(anti_csrf.is_soft_expired(bad_token))

    def test_soft_token_expiry(self):
        """ Test that tokens are rotated when they are getting old.
        They may still be accepted after this point.
        """
        good_token = anti_csrf.create_response_token()
        self.assertFalse(anti_csrf.is_soft_expired(good_token))

        import time
        old_values = "{}/{}/{}".format(int(time.time()) - 11 * 60, 123, 'unit-test')
        old_token = "{}!{}".format(anti_csrf.get_digest(old_values), old_values)

        print "Testing soft-expired token {}".format(old_token)
        self.assertTrue(anti_csrf.is_soft_expired(old_token))

    def test_username_with_slash(self):
        """ Test that usernames containing slashes are handled robustly.
        """
        mock_objects('abc_123')
        bad_token = anti_csrf.create_response_token()
        mock_objects('abc/123')
        good_token = anti_csrf.create_response_token()

        print "Testing good token '{}'".format(good_token)
        self.assertTrue(anti_csrf.validate_token(good_token))
        print "Testing wrong user token '{}'".format(bad_token)
        self.assertFalse(anti_csrf.validate_token(bad_token))

    def test_inject_token(self):
        """ Test that tokens are correctly injected into HTML.
        """
        mock_objects()
        html_cases = [
            {"input": '''<form method="POST">
                     Form contents here</form>''',
             "expected": '''<form method="POST"><input type="hidden" name="{}" value="{}"/>
                     Form contents here</form>'''
            },
            {"input": '''<a data-module="confirm-action" href="/some/path">
                     Click here</a>''',
             "expected": '''<a data-module="confirm-action" href="/some/path?{}={}">
                     Click here</a>'''
            },
            {"input": '''<a data-module="confirm-action" href="/some/path?foo=baz">
                     Click here</a>''',
             "expected": '''<a data-module="confirm-action" href="/some/path?foo=baz&{}={}">
                     Click here</a>'''
            },
            {"input": '''<a href="/some/path" data-module="confirm-action">
                     Click here</a>''',
             "expected": '''<a href="/some/path?{}={}" data-module="confirm-action">
                     Click here</a>'''
            },
        ]
        for case in html_cases:
            injected_html = anti_csrf.apply_token(case['input'])
            print "Expecting exactly one token in {}".format(injected_html)
            self.assertEqual(injected_html,
                             case['expected'].format(anti_csrf.TOKEN_FIELD_NAME, STUB_TOKEN))
            self.assertEqual(injected_html, anti_csrf.apply_token(injected_html))

if __name__ == '__main__':
    unittest.main()
