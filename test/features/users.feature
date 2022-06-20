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
        Given "Publisher" as the persona
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
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |
            | Group Admin   |

    Scenario: User list is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: User list is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"

    Scenario Outline: User detail is accessible to admins
        Given "<Persona>" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |
            | Group Admin   |

    Scenario: User detail for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "editor" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "editor"')]"

    Scenario: Non-self user detail is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: User detail is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the "editor" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"

    Scenario Outline: User profile page is accessible to admins
        Given "<Persona>" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//h1[string() = 'Administrator']"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |
            | Group Admin   |

    Scenario: User profile page for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "editor" profile page
        Then I should see an element with xpath "//h1[string() = 'Publisher']"

    Scenario: Non-self user profile page is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    @unauthenticated
    Scenario: User profile page is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I go to the "editor" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    Scenario: Dashboard page is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the dashboard
        Then I should see an element with xpath "//h2[contains(string(), 'News feed')]"

    @email
    Scenario: As a registered user, when I have locked my account with too many failed logins, I can reset my password to unlock it
        Given "Walker" as the persona
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
        Then I log in

    Scenario: Register user password must be 10 characters or longer and contain number, lowercase, capital, and symbol
        When I go to register page
        And I fill in "name" with "name"
        And I fill in "fullname" with "fullname"
        And I fill in "email" with "email@test.com"
        And I fill in "password1" with "pass"
        And I fill in "password2" with "pass"
        And I press "Create Account"
        Then I should see "Password: Your password must be 10 characters or longer"
        Then I fill in "password1" with "password1234"
        And I fill in "password2" with "password1234"
        And I press "Create Account"
        Then I should see "Password: Must contain at least one number, lowercase letter, capital letter, and symbol"
