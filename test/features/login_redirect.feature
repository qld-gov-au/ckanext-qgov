@login_redirect
Feature: Login Redirection

    @dashboard_login
    Scenario Outline: As an unauthenticated user, when I visit the dashboard URL I see the login page
        Given "TestOrgMember" as the persona
        When I visit "<URL>"
        Then I should see a login link
        When I log in directly
        Then I should see "News feed"

        Examples: Dashboard URLs
        | URL              |
        | /dashboard       |
        | /dashboard/      |

    @user_edit
    Scenario: As an unauthenticated organisation member, when I visit the user edit URL I see the login page. Upon logging in I am taken to the user edit page
        Given "TestOrgMember" as the persona
        When I visit "/user/edit"
        Then I should see a login link
        When I log in directly
        Then I should see "Change details"

    @dataset_setup
    Scenario: As a Sysadmin I set the visibility of a public record to private for the following scenarios
        Given "SysAdmin" as the persona
        When I log in
        Then I visit "/dataset/edit/annakarenina"
        When I select "True" from "private"
        And I fill in "author_email" with "test@example.com"
        And I press "Update Dataset"
        Then I should see an element with xpath "//span[contains(string(), 'Private')]"

    @private_dataset
    Scenario: As an unauthenticated user, when I visit the URL of a private dataset I see the login page
        Given "Unauthenticated" as the persona
        When I visit "/dataset/annakarenina"
        Then I should see a login link

    @public_dataset
    Scenario: As an unauthenticated user, when I visit the URL of a public dataset I see the dataset without needing to login
        Given "Unauthenticated" as the persona
        When I visit "/dataset/warandpeace"
        Then I should see an element with xpath "//h1[contains(string(), 'A Wonderful Story')]"
        And I should not see an element with xpath "//h1[contains(string(), 'Login')]"

    @private_dataset
    Scenario: As an unauthenticated organisation member, when I visit the URL of a private dataset I see the login page. Upon logging in I am taken to the private dataset
        Given "TestOrgMember" as the persona
        When I visit "/dataset/annakarenina"
        Then I should see a login link
        When I log in directly
        Then I should see an element with xpath "//h1[contains(string(), 'A Novel By Tolstoy')]"
        And I should see an element with xpath "//span[contains(string(), 'Private')]"

    @private_dataset
    Scenario: As an authenticated organisation member, when I visit the URL of a dataset private to my organisation I am taken to the private dataset
        Given "TestOrgMember" as the persona
        When I log in
        Then I visit "/dataset/annakarenina"
        Then I should see an element with xpath "//h1[contains(string(), 'A Novel By Tolstoy')]"
        And I should see an element with xpath "//span[contains(string(), 'Private')]"
