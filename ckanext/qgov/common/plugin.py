import os, random, re
from logging import getLogger
from ckan.lib.base import h
import ckan.lib.formatters as formatters
import ckan.logic.validators as validators
from ckan.plugins import implements, SingletonPlugin, IConfigurer, IRoutes, ITemplateHelpers,IActions 
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.dictization_functions import Missing
from pylons import config
from pylons.i18n import _
import datetime
from ckanext.qgov.common.stats import Stats
import anti_csrf, authenticator, urlm, intercepts
import ckan.model as model
import requests
from ckan.logic.action.get import package_show
from pylons.controllers.util import abort
import cgi
import smtplib
from time import time
from ckan import __version__
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from ckan.common import _ as __, g
import paste.deploy.converters
from ckan.lib.mailer import add_msg_niceties

LOG = getLogger(__name__)

def random_tags():
    tags = h.unselected_facet_items('tags', limit=15)
    random.shuffle(tags)
    return tags

def format_resource_filesize(size):
    return formatters.localised_filesize(int(size))

def group_id_for(group_name):

    group = model.Group.get(group_name)

    if group and group.is_active():
        return group.id
    else:
        LOG.error("%s group was not found or not active", group_name)
        return None

def format_attribution_date(date_string=None):
    if date_string:
        return datetime.datetime.strptime(date_string.split('T')[0],'%Y-%m-%d').strftime('%d %B %Y')
    else:
        return datetime.datetime.now().strftime('%d %B %Y')

def user_password_validator(key, data, errors, context):
    password_min_length = int(config.get('password_min_length', '10'))
    password_patterns = config.get('password_patterns', r'.*[0-9].*,.*[a-z].*,.*[A-Z].*,.*[-`~!@#$%^&*()_+=|\\/ ].*').split(',')

    value = data[key]

    if value is None or value == '' or isinstance(value, Missing):
        raise ValueError(_('You must provide a password'))
    if not len(value) >= password_min_length:
        errors[('password',)].append(_('Your password must be {min} characters or longer'.format(min=password_min_length)))
    for policy in password_patterns:
        if not re.search(policy, value):
            errors[('password',)].append(_('Must contain at least one number, lowercase letter, capital letter, and symbol'))

@toolkit.side_effect_free
def submit_feedback(context,data_dict=None):
    controller = 'ckanext.qgov.data.controller:QGOVDataController'
    protocol, host = h.get_site_protocol_and_host()
    full_current_url = h.full_current_url()

    if protocol is not None and host is not None and host in full_current_url:
        package = package_show(context,data_dict)
        if 'error' not in package:
            not_provided = 'Not provided'
            if 'name' not in data_dict:
                data_dict['name'] = not_provided
            if 'email' not in data_dict:
                data_dict['email'] = not_provided
            if 'comments' not in data_dict:
                data_dict['comments'] = not_provided
            data_dict['resource_id'] = data_dict.get('resource_id','')

            feedback_email = package.get('maintainer_email','')
            feedback_organisation = package['organization'].get('title','')
            feedback_origins = "{0}/dataset/{1}".format(host,package['name'])
            feedback_resource_name = ''
            if data_dict['resource_id'] != '':
                feedback_origins = "{0}/resource/{1}".format(feedback_origins,data_dict['resource_id'])
                package_resources = package.get('resources',[])
                for resource in package_resources:
                    if data_dict['resource_id'] == resource.get('id'):
                        feedback_resource_name = resource.get('name')
            feedback_dataset = package.get('title','')

            email_subject = '{0} Feedback {1} {2}'.format(host,feedback_dataset,feedback_resource_name)
            email_recipient_name = 'All'

            email_to = (config.get('feedback_form_recipients','')).split(',')
            if feedback_email != '':
                email_to.append(feedback_email)

            email_to = [i.strip() for i in email_to if i.strip() != '']
            LOG.error(email_to)
            if len(email_to) != 0:
                email_body = "Name: {0}\nEmail: {1}\nComments: {2}\nFeedback Organisation: {3}\nFeedback Email: {4}\nFeedback Dataset: {5}\nFeedback Resource: {6}\nFeedback URL: {7}".format(
                    cgi.escape(data_dict['name']),
                    cgi.escape(data_dict['email']),
                    cgi.escape(data_dict['comments']),
                    cgi.escape(feedback_organisation),
                    cgi.escape(feedback_email),
                    cgi.escape(feedback_dataset),
                    cgi.escape(feedback_resource_name),
                    cgi.escape(feedback_origins)
                )
                try:
                    feedback_mail_recipient(
                        email_recipient_name,
                        email_to,
                        g.site_title,
                        g.site_url,
                        email_subject,
                        email_body
                    )
                except:
                    abort(404, 'This form submission is invalid or CKAN mail is not configured.')

                #Redirect to home page if no thanks page is found
                success_redirect = config.get('feedback_redirection','/')
                r = requests.get(protocol + '://' + host + success_redirect,verify=False)
                if r.status_code == requests.codes.ok:
                    h.redirect_to(success_redirect)
                else:
                    h.redirect_to('/')
            else:
                abort(404, 'Form submission is invalid no recipients.')
        return package
    else:
        abort(404, 'Invalid request source')

def feedback_mail_recipient(recipient_name, recipient_email, sender_name, sender_url, subject, body, headers={}):
    mail_from = config.get('smtp.mail_from')
    body = add_msg_niceties(recipient_name, body, sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items(): msg[k] = v
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = __("%s <%s>") % (sender_name, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')
    msg['Date'] = Utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % __version__

    # Send the email using Python's smtplib.
    smtp_connection = smtplib.SMTP()
    smtp_server = config.get('smtp.server', 'localhost')
    smtp_starttls = paste.deploy.converters.asbool(
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
        LOG.info("Sent email to {0}".format(','.join(recipient_email)))

    except smtplib.SMTPException, e:
        msg = '%r' % e
        LOG.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()

class QGOVPlugin(SingletonPlugin):
    """Apply custom functions for Queensland Government portals.

    ``IConfigurer`` allows us to add/modify configuration options.
    ``IRoutes`` allows us to add new URLs, or override existing URLs.
    """
    implements(IConfigurer, inherit=True)
    implements(IRoutes, inherit=True)
    implements(ITemplateHelpers, inherit=True)
    implements(IActions, inherit=True)

    def __init__(self, **kwargs):
        validators.user_password_validator = user_password_validator
        anti_csrf.intercept_csrf()
        authenticator.intercept_authenticator()
        urlm.intercept_404()
        intercepts.set_intercepts()

    def update_config(self, ckan_config):
        """Use our custom list of licences, and disable some unwanted features
        """
        ckan_config['ckan.template_title_deliminater'] = '|'
        here = os.path.dirname(__file__)

        #If path to qgov-licences exists add to path
        possible_licences_path = os.path.join(here, 'resources', 'qgov-licences.json')
        if os.path.isfile(possible_licences_path):
            ckan_config['licenses_group_url'] = 'file://'+ possible_licences_path

        #Theme Inclusions of public and templates
        possible_public_path = os.path.join(here, 'theme/public')
        if os.path.isdir(possible_public_path):
            ckan_config['extra_public_paths'] = possible_public_path + ',' + ckan_config.get('extra_public_paths', '')
        possible_template_path = os.path.join(here, 'theme/templates')
        if os.path.isdir(possible_template_path):
            ckan_config['extra_template_paths'] = possible_template_path + ',' + ckan_config.get('extra_template_paths', '')
        # block unwanted content
        ckan_config['openid_enabled'] = False

        # configure URL Management system
        urlm_path = ckan_config.get('urlm.app_path', None)
        if urlm_path:
            urlm_proxy = ckan_config.get('urlm.proxy', None)
            urlm.configure_urlm(urlm_path, urlm_proxy)
        else:
            urlm.configure_for_environment(ckan_config.get('ckan.site_url', ''))
        return ckan_config

    def before_map(self, routeMap):
        """ Use our custom controller, and disable some unwanted URLs
        """
        controller = 'ckanext.qgov.common.controller:QGOVController'
        routeMap.connect('/storage/upload_handle', controller=controller, action='upload_handle')
        routeMap.connect('/article/{path:[-_a-zA-Z0-9/]+}', controller=controller, action='static_content')

        return routeMap

    def get_helpers(self):
        """ A dictionary of extra helpers that will be available
        to provide QGOV-specific helpers to the templates.
        """
        helper_dict = {}
        helper_dict['top_organisations'] = Stats.top_organisations
        helper_dict['top_categories'] = Stats.top_categories
        helper_dict['resource_count'] = Stats.resource_count
        helper_dict['resource_report'] = Stats.resource_report
        helper_dict['resource_org_count'] = Stats.resource_org_count
        helper_dict['random_tags'] = random_tags
        helper_dict['format_resource_filesize'] = format_resource_filesize
        helper_dict['group_id_for'] = group_id_for
        helper_dict['format_attribution_date'] = format_attribution_date

        return helper_dict

    def get_actions(self):
        """Extend actions API
        """
        return {
            'submit_feedback' : submit_feedback
        }
