from behave import step
from behaving.web.steps import *  # noqa: F401, F403
from behaving.personas.steps import *  # noqa: F401, F403
from behaving.web.steps.url import when_i_visit_url


@step('I go to homepage')
def go_to_home(context):
    when_i_visit_url(context, '/')


@step('I log in')
def log_in(context):

    assert context.persona
    context.execute_steps(u"""
        When I go to homepage
        And I click the link with text that contains "Log in"
        And I fill in "login" with "$name"
        And I fill in "password" with "$password"
        And I press the element with xpath "//button[contains(string(), 'Login')]"
        Then I should see an element with xpath "//a[contains(string(), 'Log out')]"
    """)


@step('I go to dataset page')
def go_to_dataset_page(context):
    when_i_visit_url(context, '/dataset')


@step('I go to organisation page')
def go_to_organisation_page(context):
    when_i_visit_url(context, '/organization')


@step('I go to register page')
def go_to_register_page(context):
    when_i_visit_url(context, '/user/register')


@step('I go to the user autocomplete API')
def go_to_user_autocomplete(context):
    when_i_visit_url(context, '/api/2/util/user/autocomplete?q=admin')


@step('I go to the user list API')
def go_to_user_list(context):
    when_i_visit_url(context, '/api/3/action/user_list')


@step('I view the {group_id} group API including users')
def go_to_group_including_users(context, group_id):
    when_i_visit_url(context, r'/api/3/action/group_show?id={}&include_users=true'.format(group_id))


@step('I view the {organisation_id} organisation API including users')
def go_to_organisation_including_users(context, organisation_id):
    when_i_visit_url(context, r'/api/3/action/organization_show?id={}&include_users=true'.format(organisation_id))
