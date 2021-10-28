# encoding: utf-8
""" Provides a hook to lock accounts after 10 failed login attempts.
"""

import logging
from ckan.lib.authenticator import UsernamePasswordAuthenticator
from ckan.model import User, Session
from ckan.model.meta import metadata

from sqlalchemy import Column, types, DDL
from sqlalchemy.ext.declarative import declarative_base

from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

BASE = declarative_base()

LOG = logging.getLogger(__name__)


def intercept_authenticator():
    """ Replaces the existing authenticate function with our custom one.
    """
    if 'user' in metadata.tables and 'login_attempts' not in metadata.tables['user'].columns:
        LOG.warn("'login_attempts' field does not exist, adding...")
        DDL("ALTER TABLE public.user ADD COLUMN login_attempts SMALLINT DEFAULT 0").execute(Session.get_bind())
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
        user = User.by_name(identity.get('login'))
        if user is None:
            LOG.debug('Login failed - username %r not found', identity.get('login'))
            return None

        qgov_user = Session.query(QGOVUser).filter_by(name=identity.get('login')).first()
        if qgov_user.login_attempts >= 10:
            LOG.debug('Login as %r failed - account is locked', identity.get('login'))
        elif user.validate_password(identity.get('password')):
            # reset attempt count to 0
            qgov_user.login_attempts = 0
            Session.commit()
            return user.name
        else:
            LOG.debug('Login as %r failed - password not valid', identity.get('login'))

        qgov_user.login_attempts += 1
        Session.commit()
        return None


class QGOVUser(BASE):
    """ Extend the standard User object to add a login attempt count.
    """
    __tablename__ = 'user'
    __mapper_args__ = {'include_properties': ['id', 'name', 'login_attempts']}
    id = Column(types.UnicodeText, primary_key=True)
    name = Column(types.UnicodeText, nullable=False, unique=True)
    login_attempts = Column(types.SmallInteger)
