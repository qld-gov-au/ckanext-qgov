# encoding: utf-8

'''Tests for username and Displayed Name filtering.
'''

import unittest

from ckan.plugins import toolkit

from .user_creation import validators

PUBLISHER_USERNAME = 'publisher-123'
PUBLISHER_DISPLAY_NAME = 'Gov account'
NON_PUBLISHER_USERNAME = 'test-123'
NON_PUBLISHER_DISPLAY_NAME = 'Public account'


class MockUser(object):
    """ Stub class to represent a logged-in user.
    """

    def __init__(self, sysadmin, name, fullname):
        """ Set up a stub name to return.
        """
        self.name = name
        self.fullname = fullname
        self.sysadmin = sysadmin


def mock_objects(username='', displayed_name='', sysadmin=False):
    validators._get_user = lambda: MockUser(sysadmin, username, displayed_name)
    validators.config = {'ckanext.data_qld.excluded_display_name_words': 'gov'}


class TestUserValidation(unittest.TestCase):
    """ Test our user validation rules.
    """

    def _assert_valid(self, username, fullname, context=None):
        data_dict = {'username': username, 'fullname': fullname}
        validators.data_qld_user_name_validator(key='username', data=data_dict, errors=None, context=context)
        validators.data_qld_displayed_name_validator(key='fullname', data=data_dict, errors=None, context=context)

    def _assert_not_valid_username(self, username):
        self.assertRaises(
            toolkit.Invalid, validators.data_qld_user_name_validator,
            'username', {'username': username, 'fullname': NON_PUBLISHER_DISPLAY_NAME}, None, None)

    def _assert_not_valid_display_name(self, fullname):
        self.assertRaises(
            toolkit.Invalid, validators.data_qld_displayed_name_validator,
            'fullname', {'username': NON_PUBLISHER_USERNAME, 'fullname': fullname}, None, None)

    def test_can_register_user(self):
        """ Test that a user can be created/updated.
        """
        mock_objects()
        self._assert_valid(NON_PUBLISHER_USERNAME, NON_PUBLISHER_DISPLAY_NAME)

    def test_cannot_set_publisher_name(self):
        """ Test that usernames may not contain 'publisher' by default.
        """
        mock_objects()
        self._assert_not_valid_username(PUBLISHER_USERNAME)
        self._assert_not_valid_display_name(PUBLISHER_DISPLAY_NAME)

    def test_sysadmin_can_set_publisher_name(self):
        """ Test that sysadmins can update usernames to contain 'publisher'.
        """
        mock_objects(sysadmin=True)
        self._assert_valid(PUBLISHER_USERNAME, PUBLISHER_DISPLAY_NAME)

    def test_publisher_can_retain_name(self):
        """ Test that publishers can update their profiles
        without changing their usernames.
        """
        mock_objects(username=PUBLISHER_USERNAME, displayed_name=PUBLISHER_DISPLAY_NAME)
        self._assert_valid(PUBLISHER_USERNAME, PUBLISHER_DISPLAY_NAME)

    def test_publisher_can_reset_password(self):
        """ Test that publishers can reset their passwords.
        """
        mock_objects()
        self._assert_valid(PUBLISHER_USERNAME, PUBLISHER_DISPLAY_NAME, context={'reset_password': True})


if __name__ == '__main__':
    unittest.main()
