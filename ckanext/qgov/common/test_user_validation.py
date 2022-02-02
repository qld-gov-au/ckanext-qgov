# encoding: utf-8

'''Tests for username and Displayed Name filtering.
'''

import unittest

from ckan.plugins import toolkit

from .user_creation import validators

PUBLISHER_USERNAME = 'publisher-123'
NON_PUBLISHER_USERNAME = 'test-123'


class MockUser(object):
    """ Stub class to represent a logged-in user.
    """

    def __init__(self, sysadmin, name, fullname):
        """ Set up a stub name to return.
        """
        self.name = name
        self.fullname = fullname
        self.sysadmin = sysadmin


def mock_objects(username=None, displayed_name=None, sysadmin=False):
    validators._get_user = lambda: MockUser(sysadmin, username, displayed_name)


class TestUserValidation(unittest.TestCase):
    """ Test our user validation rules.
    """

    def test_can_register_user(self):
        """ Test that a user can be created/updated.
        """
        mock_objects()
        validators.data_qld_user_name_validator('username', {'username': NON_PUBLISHER_USERNAME}, None, None)

    def test_cannot_set_publisher_name(self):
        """ Test that usernames may not contain 'publisher' by default.
        """
        mock_objects()
        self.assertRaises(toolkit.Invalid, validators.data_qld_user_name_validator, 'username', {'username': PUBLISHER_USERNAME}, None, None)

    def test_sysadmin_can_set_publisher_name(self):
        """ Test that sysadmins can update usernames to contain 'publisher'.
        """
        mock_objects(sysadmin=True)
        validators.data_qld_user_name_validator('username', {'username': PUBLISHER_USERNAME}, None, None)

    def test_publisher_can_retain_name(self):
        """ Test that publishers can update their profiles
        without changing their usernames.
        """
        mock_objects(username=PUBLISHER_USERNAME)
        validators.data_qld_user_name_validator('username', {'username': PUBLISHER_USERNAME}, None, None)


if __name__ == '__main__':
    unittest.main()
