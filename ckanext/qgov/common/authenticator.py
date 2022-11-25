# encoding: utf-8
""" Provides a hook to lock accounts after 10 failed login attempts.
"""

import logging
from ckan.lib.authenticator import UsernamePasswordAuthenticator
from ckan.lib.redis import connect_to_redis
from ckan.model import User, Session
from ckan.plugins.toolkit import config

LOG = logging.getLogger(__name__)

LOGIN_THROTTLE_EXPIRY = 1800
OriginalUsernamePasswordAuthenticatorAuth = UsernamePasswordAuthenticator.authenticate


def unlock_account(account_id):
    """ Unlock an account (erase the failed login attempts).
    """
    qgov_user = Session.query(User).filter(User.id == account_id).first()
    if qgov_user:
        login_name = qgov_user.name
        cache_key = '{}.ckanext.qgov.login_attempts.{}'.format(config['ckan.site_id'], login_name)
        redis_conn = connect_to_redis()
        if redis_conn.get(cache_key):
            LOG.debug("Clearing failed login attempts for %s", login_name)
            redis_conn.delete(cache_key)
    else:
        LOG.debug("Account %s not found", account_id)


def intercept_authenticator():
    """ Replaces the existing authenticate function with our custom one.
    """
    UsernamePasswordAuthenticator.authenticate = QGOVAuthenticator().authenticate


class QGOVAuthenticator(UsernamePasswordAuthenticator):
    """ Extend UsernamePasswordAuthenticator so it's possible to
    configure this via who.ini.
    """

    def authenticate(self, environ, identity):
        """ Mimic most of UsernamePasswordAuthenticator.authenticate
        but add account lockout after 10 failed attempts.
        """
        # don't try to increment account lockout if account doesn't exist
        if 'login' not in identity or 'password' not in identity:
            return None
        login_name = identity.get('login')
        user = User.by_name(login_name)
        if user is None:
            LOG.debug('Login failed - username %r not found', login_name)
            return None

        cache_key = '{}.ckanext.qgov.login_attempts.{}'.format(config['ckan.site_id'], login_name)
        redis_conn = connect_to_redis()
        try:
            login_attempts = int(redis_conn.get(cache_key) or 0)
        except ValueError:
            # shouldn't happen but let's play it safe
            login_attempts = 0

        LOG.debug('%r has failed to log in %s time(s) previously', login_name, login_attempts)
        if login_attempts >= 10:
            LOG.debug('Login as %r failed - account is locked', login_name)
        else:
            return_value = OriginalUsernamePasswordAuthenticatorAuth(self, environ, identity)
            if return_value:
                if login_attempts > 0:
                    LOG.debug("Clearing failed login attempts for %s", login_name)
                    redis_conn.delete(cache_key)
                return return_value
            else:
                LOG.debug('Login as %r failed - password not valid', login_name)

        redis_conn.set(cache_key, login_attempts + 1, ex=LOGIN_THROTTLE_EXPIRY)
        return None
