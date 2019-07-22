# encoding: utf-8

import ckan.lib.base as base, ckan.lib.helpers as h, ckan.model as model
from ckan import __version__
from ckan.common import _, c, g, config, request
from ckan.logic import get_action
from ckan.lib.base import abort, BaseController, render
from ckan.lib.render import TemplateNotFound

import cgi, smtplib, paste.deploy.converters, requests
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from logging import getLogger
from time import time
LOG = getLogger(__name__)

def add_msg_niceties(recipient_name, body, sender_name, sender_url):
    return _(u"Dear %s,") % recipient_name \
           + u"\r\n\r\n%s\r\n\r\n" % body \
           + u"--\r\n%s (%s)" % (sender_name, sender_url)

def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

class MailerException(Exception):
    pass

def feedback_mail_recipient(recipient_name, recipient_email, sender_name, sender_url, subject, body, headers={}):
    mail_from = config.get('smtp.mail_from')
    body = add_msg_niceties(recipient_name, body, sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items(): msg[k] = v
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    msg['To'] = ", ".join(recipient_email)
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

class QGOVController(BaseController):

    def static_content(self, path):
        try:
            return render('static-content/{path}/index.html'.format(path=path))
        except TemplateNotFound:
            LOG.warn(path + " not found")
            base.abort(404)

    def submit_feedback(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}
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

                data_dict['resource_id'] = request.GET.get('resource_id','')
                data_dict['captcha'] = request.GET.get('captcha','')

                if (data_dict.get('captcha','') != '' or not(request.GET.get('captchaCatch','none') == 'dev' or request.GET.get('captchaCatch','none') == 'prod')):
                    #Do not indicate failure or success since captcha was filled likely bot;
                    #7 is the expected aurguments in the query string;
                    #captchaCatch is serverside generated value hence can either be 'dev' or 'prod'
                    h.redirect_to('/')
                    return package

                # If there is value for either maintenance_email or author_email, use that. If both of them null then send the email to online@qld.gov.au
                # Logic written to maintain legacy data
                # Once all the records in database have 'maintainer_email', remove this and feedback_email = package.get('maintainer_email','')
                if(not(package.get('maintainer_email')== '' or package.get('maintainer_email') is None)):
                    feedback_email = package.get('maintainer_email')
                elif (not(package.get('author_email')== '' or package.get('author_email') is None)):
                    feedback_email = package.get('author_email')
                else:
                    feedback_email = 'online@qld.gov.au'
                #feedback_email = package.get('maintainer_email','')
                if 'organization' in package and package['organization']:
                    feedback_organisation = strip_non_ascii(package['organization'].get('title',''))
                else:
                    feedback_organisation = 'None'
                feedback_resource_name = ''
                feedback_dataset = strip_non_ascii(package.get('title',''))

                package_name = strip_non_ascii(package.get('name',''))
                feedback_origins = "{0}/dataset/{1}".format(host,package_name)

                if data_dict['resource_id'] != '':
                    feedback_origins = "{0}/resource/{1}".format(feedback_origins,data_dict['resource_id'])
                    package_resources = package.get('resources',[])
                    for resource in package_resources:
                        if data_dict['resource_id'] == resource.get('id'):
                            feedback_resource_name = strip_non_ascii(resource.get('name',''))

                email_subject = '{0} Feedback {1} {2}'.format(host,feedback_dataset,feedback_resource_name)
                email_recipient_name = 'All'

                email_to = (config.get('feedback_form_recipients','')).split(',')
                if feedback_email != '' and feedback_email:
                    email_to.append(feedback_email)
                else:
                    feedback_email = ''

                email_to = [e for e in email_to if e is not None]

                email_to = [i.strip() for i in email_to if i.strip() != '']
                if len(email_to) != 0:
                    email_body = "Name: {0} \r\nEmail: {1} \r\nComments: {2} \r\nFeedback Organisation: {3} \r\n" \
                                "Feedback Email: {4} \r\nFeedback Dataset: {5} \r\nFeedback Resource: {6} \r\n" \
                                "Feedback URL: {7}://{8}".format(
                        cgi.escape(strip_non_ascii(data_dict['name'])),
                        cgi.escape(strip_non_ascii(data_dict['email'])),
                        cgi.escape(strip_non_ascii(data_dict['comments'])),
                        cgi.escape(feedback_organisation),
                        cgi.escape(strip_non_ascii(feedback_email)),
                        cgi.escape(feedback_dataset),
                        cgi.escape(feedback_resource_name),
                        cgi.escape(protocol),
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
