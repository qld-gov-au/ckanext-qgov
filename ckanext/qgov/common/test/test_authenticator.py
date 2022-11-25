# encoding: utf-8

import pytest
import ckan.lib.create_test_data as ctd
import ckan.lib.authenticator as authenticator
import ckanext.qgov.common.authenticator as qgovAuthenticator
CreateTestData = ctd.CreateTestData


class TestUsernamePasswordAuthenticator(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        qgovAuthenticator.intercept_authenticator()
        # Verify intercept replaced authenticator module
        self.authenticate = authenticator.UsernamePasswordAuthenticator()

    def test_authenticate_succeeds_if_login_and_password_are_correct(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}

        username = self.authenticate(environ, identity)
        # 2.9.6+
        if ",1" in username:
            assert username == user.id + ",1", username
        # 2.9.5-
        else:
            assert username == user.name, username

    def test_authenticate_fails_if_user_is_deleted(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.delete()
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.set_pending()
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_password_is_wrong(self):
        environ = {}
        user = CreateTestData.create_user("a_user")
        identity = {"login": user.name, "password": "wrong-password"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_no_login_or_pass(self):
        environ = {}
        identity = {}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_login(self):
        environ = {}
        identity = {"login": "some-user"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_password(self):
        environ = {}
        identity = {"password": "some-password"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_doesnt_exist(self):
        environ = {}
        identity = {"login": "inexistent-user"}
        assert self.authenticate(environ, identity) is None
