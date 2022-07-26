# encoding: utf-8
""" Provide some extra routes for Queensland Government portals.
"""

import cgi
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from logging import getLogger
from time import time

import requests

from ckan import __version__
import ckan.lib.helpers as h
from ckan import model
from ckan.controllers.package import PackageController
from ckan.lib.render import TemplateNotFound
from ckan.plugins.toolkit import _, abort, asbool, config, g, get_action,\
    redirect_to, render, request, url_for, ObjectNotFound, NotAuthorized

LOG = getLogger(__name__)


def add_msg_niceties(recipient_name, body, sender_name, sender_url):
    """ Make email formatting prettier eg adding a polite greeting.
    """
    return _(u"Dear %s,") % recipient_name \
        + u"\r\n\r\n%s\r\n\r\n" % body \
        + u"--\r\n%s (%s)" % (sender_name, sender_url)


def _strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)


class MailerException(Exception):
    """ Placeholder exception type for SMTP failures.
    """
    pass


def _feedback_mail_recipient(recipient_name, recipient_email,
                             sender_name, sender_url, subject, body,
                             headers):
    """ Assemble and send a feedback email from the provided parts.
    """
    # Flake8 B006: Don't initialize this in the parameter, because
    # default parameters are shared between calls, and dict is mutable.
    headers = headers or {}
    mail_from = config.get('smtp.mail_from')
    body = add_msg_niceties(recipient_name, body, sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for key, value in headers.items():
        msg[key] = value
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    msg['To'] = ", ".join(recipient_email)
    msg['Date'] = Utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % __version__

    # Send the email using Python's smtplib.
    smtp_connection = smtplib.SMTP()
    smtp_server = config.get('smtp.server', 'localhost')
    smtp_starttls = asbool(
        config.get('smtp.starttls'))
    smtp_user = config.get('smtp.user')
    smtp_password = config.get('smtp.password')
    smtp_connection.connect(smtp_server)
    try:
        # Identify ourselves and prompt the server for supported features.
        smtp_connection.ehlo()

        # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
        # connection into TLS mode.
        if smtp_starttls:
            if smtp_connection.has_extn('STARTTLS'):
                smtp_connection.starttls()
                # Re-identify ourselves over TLS connection.
                smtp_connection.ehlo()
            else:
                raise MailerException("SMTP server does not support STARTTLS")

        # If 'smtp.user' is in CKAN config, try to login to SMTP server.
        if smtp_user:
            assert smtp_password, ("If smtp.user is configured then "
                                   "smtp.password must be configured as well.")
            smtp_connection.login(smtp_user, smtp_password)

        smtp_connection.sendmail(mail_from, recipient_email, msg.as_string())
        LOG.info("Sent email to %s", ','.join(recipient_email))

    except smtplib.SMTPException as ex:
        msg = '%r' % ex
        LOG.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()


class QGOVController(PackageController):
    """ Custom route implementations for Queensland Government portals.
    """

    def static_content(self, path):
        """ Render a page that needs the template engine,
        but doesn't need any data from CKAN.
        """
        try:
            return render('static-content/{}/index.html'.format(path))
        except TemplateNotFound:
            LOG.warn("%s not found", path)
            return abort(404)

    def submit_feedback(self):
        """ Retrieves the necessary data and sends a feedback email
        to the appropriate recipient.
        """
        context = {'model': model, 'session': model.Session,
                   'user': g.user, 'for_view': True,
                   'auth_user_obj': g.userobj}
        protocol, host = h.get_site_protocol_and_host()
        full_current_url = h.full_current_url()

        if protocol is not None and host is not None and host in full_current_url:
            package = get_action('package_show')(context, {'id': request.GET['id']})
            if 'error' not in package:
                data_dict = {}
                not_provided = 'Not provided'
                if 'name' not in request.GET:
                    data_dict['name'] = not_provided
                else:
                    data_dict['name'] = request.GET['name'].encode('utf8')
                if 'email' not in request.GET:
                    data_dict['email'] = not_provided
                else:
                    data_dict['email'] = request.GET['email'].encode('utf8')
                if 'comments' not in request.GET:
                    data_dict['comments'] = not_provided
                else:
                    data_dict['comments'] = request.GET['comments'].encode('utf8')

                data_dict['resource_id'] = request.GET.get('resource_id', '')
                data_dict['captcha'] = request.GET.get('captcha', '')

                if (data_dict.get('captcha', '') or request.GET.get('captchaCatch', 'none') not in ['dev', 'prod']):
                    # Do not indicate failure or success since captcha was filled likely bot;
                    # 7 is the expected arguments in the query string;
                    # captchaCatch is serverside generated value hence can either be 'dev' or 'prod'
                    return redirect_to('/')

                # If there is value for either maintenance_email or author_email, use that.
                # If both of them null then send the email to online@qld.gov.au
                # Logic written to maintain legacy data
                # Once all the records in database have 'maintainer_email',
                # remove this and feedback_email = package.get('maintainer_email', '')
                feedback_email = package.get('maintainer_email', '')
                if not feedback_email:
                    feedback_email = package.get('author_email', '')
                if not feedback_email:
                    feedback_email = 'onlineproducts@smartservice.qld.gov.au'

                if 'organization' in package and package['organization']:
                    feedback_organisation = _strip_non_ascii(package['organization'].get('title', ''))
                else:
                    feedback_organisation = 'None'
                feedback_resource_name = ''
                feedback_dataset = _strip_non_ascii(package.get('title', ''))

                package_name = _strip_non_ascii(package.get('name', ''))
                feedback_origins = "{0}/dataset/{1}".format(host, package_name)

                if data_dict['resource_id'] != '':
                    feedback_origins = "{0}/resource/{1}".format(feedback_origins, data_dict['resource_id'])
                    package_resources = package.get('resources', [])
                    for resource in package_resources:
                        if data_dict['resource_id'] == resource.get('id'):
                            feedback_resource_name = _strip_non_ascii(resource.get('name', ''))

                email_subject = '{0} Feedback {1} {2}'.format(host, feedback_dataset, feedback_resource_name)
                email_recipient_name = 'All'

                email_to = (config.get('feedback_form_recipients', '')).split(',')
                if feedback_email != '' and feedback_email:
                    email_to.append(feedback_email)
                else:
                    feedback_email = ''

                email_to = [e for e in email_to if e is not None]

                email_to = [i.strip() for i in email_to if i.strip() != '']
                if email_to:
                    email_body = "Name: {0} \r\nEmail: {1} \r\nComments: {2} \r\nFeedback Organisation: {3} \r\n" \
                        "Feedback Email: {4} \r\nFeedback Dataset: {5} \r\nFeedback Resource: {6} \r\n" \
                        "Feedback URL: {7}://{8}".format(
                            cgi.escape(_strip_non_ascii(data_dict['name'])),
                            cgi.escape(_strip_non_ascii(data_dict['email'])),
                            cgi.escape(_strip_non_ascii(data_dict['comments'])),
                            cgi.escape(feedback_organisation),
                            cgi.escape(_strip_non_ascii(feedback_email)),
                            cgi.escape(feedback_dataset),
                            cgi.escape(feedback_resource_name),
                            cgi.escape(protocol),
                            cgi.escape(feedback_origins)
                        )
                    try:
                        _feedback_mail_recipient(
                            email_recipient_name,
                            email_to,
                            g.site_title,
                            g.site_url,
                            email_subject,
                            email_body
                        )
                    except Exception:
                        return abort(404, 'This form submission is invalid or CKAN mail is not configured.')

                    # Redirect to home page if no thanks page is found
                    success_redirect = config.get('feedback_redirection', '/')
                    req = requests.get(protocol + '://' + host + success_redirect, verify=False)
                    if req.status_code == requests.codes.ok:
                        return redirect_to(success_redirect)
                    else:
                        return redirect_to('/')
                else:
                    return abort(404, 'Form submission is invalid, no recipients.')

            return package
        else:
            return abort(404, 'Invalid request source')

    def _get_context(self):
        return {'model': model, 'session': model.Session,
                'user': g.user, 'for_view': True,
                'auth_user_obj': g.userobj}

    def _is_dataset_public(self, id):
        try:
            get_action('package_show')(self._get_context(), {'id': id})
            return True
        except ObjectNotFound:
            # if nonexistent, handle it via standard channels
            return True
        except NotAuthorized:
            return False

    def read(self, id):
        """
        Override the default CKAN behaviour for private Dataset visibility
        for unauthenticated users.
        Instead of displaying "404 Dataset not found" message, give unauthenticated
        users a chance to login (if the dataset exists).
        :param id: Package id/name
        :return:
        """
        if not g.user and not self._is_dataset_public(id):
            return redirect_to(
                url_for('user.login', came_from='/dataset/{id}'.format(id=id))
            )

        return super(QGOVController, self).read(id)

    def resource_read(self, id, resource_id):
        """
        Override the default CKAN behaviour for private Dataset Resource visibility
        for unauthenticated users.
        Instead of displaying "404 Dataset not found" message, give unauthenticated
        users a chance to log in (if the dataset exists).
        :param id: Package id/name
        :param resource_id: Resource id
        :return:
        """
        if not g.user and not self._is_dataset_public(id):
            return redirect_to(
                url_for('user.login',
                        came_from='/dataset/{id}/resource/{resource_id}'.format(id=id, resource_id=resource_id))
            )

        return super(QGOVController, self).resource_read(id, resource_id)
