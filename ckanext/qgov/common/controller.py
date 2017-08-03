import ckan.lib.base as base
from ckan.lib.base import BaseController, render
from ckan.lib.render import TemplateNotFound

from logging import getLogger
LOG = getLogger(__name__)

class QGOVController(BaseController):

    def static_content(self, path):
        try:
            return render('static-content/{path}/index.html'.format(path=path))
        except TemplateNotFound:
            LOG.warn(path + " not found")
            base.abort(404)
