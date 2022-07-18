from behave import step
from behaving.personas.steps import *  # noqa: F401, F403
from behaving.mail.steps import *  # noqa: F401, F403
from behaving.web.steps import *  # noqa: F401, F403
from behaving.web.steps.url import when_i_visit_url
import email
import quopri
import requests
import uuid


@step(u'I get the current URL')
def get_current_url(context):
    context.browser.evaluate_script("document.documentElement.clientWidth")


@step(u'I go to homepage')
def go_to_home(context):
    when_i_visit_url(context, '/')


@step(u'I go to register page')
def go_to_register_page(context):
    context.execute_steps(u"""
        When I go to homepage
        And I click the link with text that contains "Register"
    """)


@step(u'I log in')
def log_in(context):
    assert context.persona
    context.execute_steps(u"""
        When I go to homepage
        And I resize the browser to 1024x2048
        And I click the link with text that contains "Log in"
        And I log in directly
    """)


@step(u'I log in directly')
def log_in_directly(context):
    """
    This differs to the `log_in` function above by logging in directly to a page where the user login form is presented
    :param context:
    :return:
    """

    assert context.persona
    context.execute_steps(u"""
        When I attempt to log in with password "$password"
        Then I should see an element with xpath "//a[@title='Log out']"
    """)


@step(u'I attempt to log in with password "{password}"')
def attempt_login(context, password):
    assert context.persona
    context.execute_steps(u"""
        When I fill in "login" with "$name"
        And I fill in "password" with "{}"
        And I press the element with xpath "//button[contains(string(), 'Login')]"
    """.format(password))


@step(u'I should see a login link')
def login_link_visible(context):
    context.execute_steps(u"""
        Then I should see an element with xpath "//h1[contains(string(), 'Login')]"
    """)


@step(u'I request a password reset')
def request_reset(context):
    assert context.persona
    context.execute_steps(u"""
        When I visit "/user/reset"
        And I fill in "user" with "$name"
        And I press the element with xpath "//button[contains(string(), 'Request Reset')]"
    """)


@step(u'I fill in "{name}" with "{value}" if present')
def fill_in_field_if_present(context, name, value):
    context.execute_steps(u"""
        When I execute the script "field = document.getElementById('field-{0}'); if (field) field.value = '{1}';"
    """.format(name, value))


@step(u'I create a resource with name "{name}" and URL "{url}"')
def add_resource(context, name, url):
    context.execute_steps(u"""
        When I log in
        And I visit "/dataset/new_resource/test-dataset"
        And I execute the script "document.getElementById('field-image-url').value='{url}'"
        And I fill in "name" with "{name}"
        And I fill in "description" with "description"
        And I fill in "size" with "1024" if present
        And I press the element with xpath "//form[contains(@class, 'resource-form')]//button[contains(@class, 'btn-primary')]"
    """.format(name=name, url=url))


@step(u'I fill in title with random text')
def title_random_text(context):
    assert context.persona
    context.execute_steps(u"""
        When I fill in "title" with "Test Title {0}"
    """.format(uuid.uuid4()))


@step(u'I go to dataset page')
def go_to_dataset_page(context):
    when_i_visit_url(context, '/dataset')


@step(u'I go to dataset "{name}"')
def go_to_dataset(context, name):
    when_i_visit_url(context, '/dataset/' + name)


@step(u'I edit the "{name}" dataset')
def edit_dataset(context, name):
    when_i_visit_url(context, '/dataset/edit/{}'.format(name))


@step(u'I go to group page')
def go_to_group_page(context):
    when_i_visit_url(context, '/group')


@step(u'I go to organisation page')
def go_to_organisation_page(context):
    when_i_visit_url(context, '/organization')


@step(u'I search the autocomplete API for user "{username}"')
def go_to_user_autocomplete(context, username):
    when_i_visit_url(context, '/api/2/util/user/autocomplete?q={}'.format(username))


@step(u'I go to the user list API')
def go_to_user_list(context):
    when_i_visit_url(context, '/api/3/action/user_list')


@step(u'I go to the "{user_id}" profile page')
def go_to_user_profile(context, user_id):
    when_i_visit_url(context, '/user/{}'.format(user_id))


@step(u'I go to the dashboard')
def go_to_dashboard(context):
    when_i_visit_url(context, '/dashboard')


@step(u'I go to the "{user_id}" user API')
def go_to_user_show(context, user_id):
    when_i_visit_url(context, '/api/3/action/user_show?id={}'.format(user_id))


@step(u'I view the "{group_id}" group API "{including}" users')
def go_to_group_including_users(context, group_id, including):
    when_i_visit_url(context, r'/api/3/action/group_show?id={}&include_users={}'.format(group_id, including in ['with', 'including']))


@step(u'I view the "{organisation_id}" organisation API "{including}" users')
def go_to_organisation_including_users(context, organisation_id, including):
    when_i_visit_url(context, r'/api/3/action/organization_show?id={}&include_users={}'.format(organisation_id, including in ['with', 'including']))


@step(u'I should be able to download via the element with xpath "{expression}"')
def test_download_element(context, expression):
    url = context.browser.find_by_xpath(expression).first['href']
    assert requests.get(url, cookies=context.browser.cookies.all()).status_code == 200


@step(u'I should be able to patch dataset "{package_id}" via the API')
def test_package_patch(context, package_id):
    url = context.base_url + 'api/action/package_patch'
    response = requests.post(url, json={'id': package_id}, cookies=context.browser.cookies.all())
    print("Response from endpoint {} is: {}, {}".format(url, response, response.text))
    assert response.status_code == 200
    assert '"success": true' in response.text


@step(u'I create a dataset with title "{title}"')
def create_dataset_titled(context, title):
    context.execute_steps(u"""
        When I visit "/dataset/new"
        And I fill in "title" with "{title}"
        And I fill in "notes" with "Description"
        And I fill in "version" with "1.0"
        And I fill in "author_email" with "test@me.com"
        And I fill in "de_identified_data" with "NO" if present
        And I press "Add Data"
        And I execute the script "document.getElementById('field-image-url').value='https://example.com'"
        And I fill in "name" with "Test Resource"
        And I execute the script "document.getElementById('field-format').value='HTML'"
        And I fill in "description" with "Test Resource Description"
        And I fill in "size" with "1024" if present
        And I press the element with xpath "//form[contains(@class, 'resource-form')]//button[contains(@class, 'btn-primary')]"
    """.format(title=title))


@step(u'I create a dataset with license {license} and resource file {file}')
def create_dataset_json(context, license, file):
    create_dataset(context, license, 'JSON', file)


@step(u'I create a dataset with license {license} and {file_format} resource file {file}')
def create_dataset(context, license, file_format, file):
    assert context.persona
    context.execute_steps(u"""
        When I visit "/dataset/new"
        And I fill in title with random text
        And I fill in "notes" with "Description"
        And I fill in "version" with "1.0"
        And I fill in "author_email" with "test@me.com"
        And I execute the script "document.getElementById('field-license_id').value={license}"
        Then I fill in "de_identified_data" with "NO" if present
        And I press "Add Data"
        And I attach the file {file} to "upload"
        And I fill in "name" with "Test Resource"
        And I execute the script "document.getElementById('field-format').value={file_format}"
        And I fill in "description" with "Test Resource Description"
        And I press the element with xpath "//form[contains(@class, 'resource-form')]//button[contains(@class, 'btn-primary')]"
    """.format(license=license, file=file, file_format=file_format))


@step(u'I should receive a base64 email at "{address}" containing "{text}"')
def should_receive_base64_email_containing_text(context, address, text):
    should_receive_base64_email_containing_texts(context, address, text, None)


@step(u'I should receive a base64 email at "{address}" containing both "{text}" and "{text2}"')
def should_receive_base64_email_containing_texts(context, address, text, text2):
    # The default behaving step does not convert base64 emails
    # Modified the default step to decode the payload from base64
    def filter_contents(mail):
        mail = email.message_from_string(mail)
        payload = mail.get_payload()
        payload += "=" * ((4 - len(payload) % 4) % 4)  # do fix the padding error issue
        payload_bytes = quopri.decodestring(payload)
        if len(payload_bytes) > 0:
            payload_bytes += b'='  # do fix the padding error issue
        decoded_payload = payload_bytes.decode('base64')
        print('decoded_payload: ', decoded_payload)
        return text in decoded_payload and (not text2 or text2 in decoded_payload)

    assert context.mail.user_messages(address, filter_contents)


@step(u'I log in and go to admin config page')
def log_in_go_to_admin_config(context):
    assert context.persona
    context.execute_steps(u"""
        When I log in
        And I go to admin config page
    """)


@step(u'I go to admin config page')
def go_to_admin_config(context):
    when_i_visit_url(context, '/ckan-admin/config')


@step(u'I log out')
def log_out(context):
    when_i_visit_url(context, '/user/logout')


# ckanext-qgov


@step(u'I lock my account')
def lock_account(context):
    when_i_visit_url(context, "/user/login")
    for x in range(11):
        attempt_login(context, "incorrect password")
