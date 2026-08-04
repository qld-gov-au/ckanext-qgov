# encoding: utf-8

import pytest

from ckan import model
from ckan.lib import authenticator as core_authenticator
from ckan.tests import factories

from ckanext.qgov.common.authenticator import qgov_authenticate


class MockGlobal(object):

    def __init__(self):
        self.recaptcha_publickey = None


core_authenticator.g = MockGlobal()


class TestUsernamePasswordAuthenticator(object):

    def test_authenticate_succeeds_if_login_and_password_are_correct(self):
        password = "Default1Password$"
        user = factories.User(password=password)
        identity = {"login": user['name'], "password": password}

        username = qgov_authenticate(identity)
        assert username.name == user['name']

    def test_authenticate_fails_if_user_is_deleted(self):
        password = "Default1Password$"
        user = factories.User(password=password)
        identity = {"login": user['name'], "password": password}
        model.User.get(user['id']).delete()
        assert qgov_authenticate(identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        password = "Default1Password$"
        user = factories.User(password=password)
        identity = {"login": user['name'], "password": password}
        model.User.get(user['id']).set_pending()
        assert qgov_authenticate(identity) is None

    def test_authenticate_fails_if_password_is_wrong(self):
        user = factories.User()
        identity = {"login": user['name'], "password": "wrong-password"}
        assert qgov_authenticate(identity) is None

    @pytest.mark.parametrize(
        "identity",
        [
            {},
            {"login": "some-user"},
            {"password": "somepass"},
            {"login": "nonexistent-user", "password": "somepass"}
        ]
    )
    def test_authenticate_fails_if_incomplete_credentials(self, identity):
        assert qgov_authenticate(identity) is None
