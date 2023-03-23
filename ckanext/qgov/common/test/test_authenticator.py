# encoding: utf-8

import pytest
from ckan.model import User
import ckan.lib.create_test_data as ctd
from ckan.plugins.toolkit import check_ckan_version

if check_ckan_version('2.10'):
    from ckanext.qgov.common.authenticator import qgov_authenticate
else:
    from ckanext.qgov.common.authenticator import QGOVAuthenticator
    qgov_authenticator = QGOVAuthenticator()

    def qgov_authenticate(identity):
        return qgov_authenticator.authenticate(None, identity)

CreateTestData = ctd.CreateTestData


@pytest.mark.usefixtures("clean_db")
class TestUsernamePasswordAuthenticator(object):

    def test_authenticate_succeeds_if_login_and_password_are_correct(self):
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}

        username = qgov_authenticate(identity)
        # 2.10
        if isinstance(username, User):
            assert username.name == user.name
        # 2.9.6+
        elif ",1" in username:
            assert username == user.id + ",1", username
        # 2.9.5-
        else:
            assert username == user.name, username

    def test_authenticate_fails_if_user_is_deleted(self):
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.delete()
        assert qgov_authenticate(identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.set_pending()
        assert qgov_authenticate(identity) is None

    def test_authenticate_fails_if_password_is_wrong(self):
        user = CreateTestData.create_user("a_user")
        identity = {"login": user.name, "password": "wrong-password"}
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
