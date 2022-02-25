import ckan.model as model
import sqlalchemy as sa

from ckan.lib.cli import CkanCommand
from datetime import datetime


class UpdateFullname(CkanCommand):
    """
    Update an existing user's fullname (Displayed name) values to Displayed name required
    """

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        # Below is 18th May 2021 10.42am in UTC.
        date_threshold = datetime(2021, 5, 18, 00, 42)

        model.Session.query(model.User) \
            .filter(sa.not_(sa.func.lower(sa.func.coalesce(model.User.fullname, '')).like('data.qld%'))) \
            .filter(model.User.created < date_threshold) \
            .update({'fullname': 'Displayed name required'}, synchronize_session='fetch')
        model.Session.commit()
