# encoding: utf-8
""" Provides a hook to lock accounts after 10 failed login attempts.
"""

import logging
from ckan.common import g
from ckan.lib.authenticator import UsernamePasswordAuthenticator
from ckan.lib.redis import connect_to_redis
from ckan.model import User, Session

from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

LOG = logging.getLogger(__name__)

LOGIN_THROTTLE_EXPIRY = 1800


def unlock_account(account_id):
    """ Unlock an account (erase the failed login attempts).
    """
    qgov_user = Session.query(User).filter(User.id == account_id).first()
    if qgov_user:
        login_name = qgov_user.name
        cache_key = '{}.ckanext.qgov.login_attempts.{}'.format(g.site_id, login_name)
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
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        """ Mimic most of UsernamePasswordAuthenticator.authenticate
        but add account lockout after 10 failed attempts.
        """
        if 'login' not in identity or 'password' not in identity:
            return None
        login_name = identity.get('login')
        user = User.by_name(login_name)
        if user is None:
            LOG.debug('Login failed - username %r not found', login_name)
            return None

        cache_key = '{}.ckanext.qgov.login_attempts.{}'.format(g.site_id, login_name)
        redis_conn = connect_to_redis()
        try:
            login_attempts = int(redis_conn.get(cache_key) or 0)
        except ValueError:
            # shouldn't happen but let's play it safe
            login_attempts = 0

        if login_attempts >= 10:
            LOG.debug('Login as %r failed - account is locked', login_name)
        elif user.validate_password(identity.get('password')):
            if login_attempts > 0:
                LOG.debug("Clearing failed login attempts for %s", login_name)
                # reset attempt count to 0
                redis_conn.delete(cache_key)
            return user.name
        else:
            LOG.debug('Login as %r failed - password not valid', login_name)

        redis_conn.set(cache_key, login_attempts + 1, ex=LOGIN_THROTTLE_EXPIRY)
        return None
