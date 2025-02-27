@users
Feature: User APIs

    Scenario Outline: User autocomplete is accessible to admins
        Given "<Persona>" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |
            | Group Admin   |

    Scenario: User autocomplete is not accessible to non-admins
        Given "TestOrgMember" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    @unauthenticated
    Scenario: User autocomplete is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario Outline: User list is accessible to admins
        Given "<Persona>" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "admin"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |
            | Group Admin   |

    Scenario: User list is not accessible to non-admins
        Given "TestOrgMember" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: User list is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    Scenario Outline: User detail including email is accessible to org admins
        Given "<Persona>" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "admin"') and contains(string(), '"email": "admin@localhost"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |

    Scenario: User detail without email is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "admin"')]"
        And I should not see "admin@localhost"

    Scenario: User detail for self is accessible to non-admins
        Given "TestOrgMember" as the persona
        When I log in
        And I go to the "test_org_member" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "test_org_member"') and contains(string(), '"email": "test_org_member@localhost"')]"

    Scenario: Non-self user detail is not accessible to non-admins
        Given "TestOrgEditor" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: User detail is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the "test_org_member" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    Scenario Outline: User profile page including email is accessible to org admins
        Given "<Persona>" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//h1[string() = 'Administrator']"
        And I should see an element with xpath "//dd[string() = 'admin@localhost']"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |

    Scenario: User profile page without email is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//h1[string() = 'Administrator']"
        And I should not see "admin@localhost"

    Scenario: User profile page for self is accessible to non-admins
        Given "TestOrgMember" as the persona
        When I log in
        And I go to the "test_org_member" profile page
        Then I should see an element with xpath "//h1[string() = 'Test Member']"
        And I should see an element with xpath "//dd[string() = 'test_org_member@localhost']"

    Scenario: Non-self user profile page is not accessible to non-admins
        Given "TestOrgMember" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    @unauthenticated
    Scenario: User profile page is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the "test_org_member" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    Scenario: Dashboard page is accessible to non-admins
        Given "TestOrgEditor" as the persona
        When I log in
        And I go to the dashboard
        Then I should see my datasets
        And I should see "Add Dataset"

    Scenario: Dashboard news feed can display organisational changes
        Given "SysAdmin" as the persona
        When I log in
        And I go to organisation page
        And I press "Test Organisation"
        And I press "Manage"
        And I press "Update"
        And I visit "/dashboard"
        Then I should see an element with xpath "//li[contains(string(), 'updated the organisation')]/a[contains(string(), 'Test Organisation') and contains(@href, '/organization/')]/..//a[contains(string(), 'Administrator') and @href='/user/admin']"

    @email
    Scenario: As a registered user, when I have locked my account with too many failed logins, I can reset my password to unlock it
        Given "CKANUser" as the persona
        When I lock my account
        And I go to "/user/login"
        And I attempt to log in with password "$password"
        Then I should see "Login failed"
        When I request a password reset
        Then I should see an element with xpath "//div[contains(string(), 'A reset link has been emailed to you')]"
        When I wait for 3 seconds
        Then I should receive an email at "$email" containing "You have requested your password"
        When I parse the email I received at "$email" and set "{domain}/user/reset/{path}Have"
        And I go to "/user/reset/$path"
        Then the browser's URL should contain "/user/reset/"
        And the browser's URL should contain "key="
        When I fill in "password1" with "$password"
        And I fill in "password2" with "$password"
        And I press the element with xpath "//button[@class='btn btn-primary']"
        And I log in
        Then I should see "Dashboard"

    Scenario: Register user password must be 10 characters or longer and contain number, lowercase, capital, and symbol
        Given "Unauthenticated" as the persona
        When I expand the browser height
        And I go to register page
        And I fill in "name" with "name"
        And I fill in "fullname" with "fullname"
        And I fill in "email" with "email@test.com"
        And I fill in "password1" with "pass"
        And I fill in "password2" with "pass"
        And I press "Create Account"
        Then I should see "Password: Your password must be 10 characters or longer"
        When I fill in "password1" with "password1234"
        And I fill in "password2" with "password1234"
        And I press "Create Account"
        Then I should see "Password: Must contain at least one number, lowercase letter, capital letter, and symbol"

    Scenario: As a sysadmin, when I go to the sysadmin list, I can promote and demote other sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I click the link to a url that contains "/ckan-admin/"
        And I take a debugging screenshot
        Then I should see an element with xpath "//table//a[string() = 'Administrator' and @href = '/user/admin']"
        And I should not see "Test Admin"

        When I fill in "promote-username" with "test_org_admin"
        And I press "Promote"
        And I take a debugging screenshot
        Then I should see "Promoted Test Admin to sysadmin"
        And I should see an element with xpath "//table//a[string() = 'Test Admin' and @href = '/user/test_org_admin']"

        When I press the element with xpath "//tr/td/a[@href = '/user/test_org_admin']/../following-sibling::td//button[contains(@title, 'Revoke') or contains(@data-bs-title, 'Revoke')]"
        Then I should see "Revoked sysadmin permission from Test Admin"
        And I should not see an element with xpath "//table//a[@href = '/user/test_org_admin']"
