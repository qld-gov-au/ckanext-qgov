from ckan.lib.authenticator import UsernamePasswordAuthenticator
from ckan.model import User, Session

from sqlalchemy import Column, types
from sqlalchemy.ext.declarative import declarative_base

from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

Base = declarative_base()

import logging
log = logging.getLogger(__name__)

def intercept_authenticator():
    UsernamePasswordAuthenticator.authenticate = QGOVAuthenticator().authenticate

class QGOVAuthenticator(UsernamePasswordAuthenticator):
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        if not 'login' in identity or not 'password' in identity:
            return None
        user = User.by_name(identity.get('login'))
        if user is None:
            log.debug('Login failed - username %r not found', identity.get('login'))
            return None

        qgovUser = Session.query(QGOVUser).filter_by(name = identity.get('login')).first()
        if qgovUser.login_attempts >= 10:
            log.debug('Login as %r failed - account is locked', identity.get('login'))
        elif user.validate_password(identity.get('password')):
            # reset attempt count to 0
            qgovUser.login_attempts = 0
            Session.commit()
            return user.name
        else:
            log.debug('Login as %r failed - password not valid', identity.get('login'))

        qgovUser.login_attempts += 1
        Session.commit()
        return None

class QGOVUser(Base):
    __tablename__ = 'user'
    __mapper_args__ = {'include_properties' : ['id', 'name', 'login_attempts']}
    id = Column(types.UnicodeText, primary_key=True)
    name = Column(types.UnicodeText, nullable=False, unique=True)
    login_attempts = Column(types.SmallInteger)
