@users
Feature: User APIs

    Scenario: User autocomplete is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is not accessible anonymously
        When I search the autocomplete API for user "admin"
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"


    Scenario: User list is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: User list is not accessible anonymously
        When I go to the user list API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"


    Scenario: User detail is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User detail is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: User detail is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the "publisher" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: User detail for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "publisher" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: Non-self user detail is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: User detail is not accessible anonymously
        When I go to the "publisher" user API
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"


    Scenario: User profile page is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//h1[string() = 'Administrator']"

    Scenario: User profile page is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" profile page
        Then I should see an element with xpath "//h1[string() = 'Publisher']"

    Scenario: User profile page is accessible to group admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" profile page
        Then I should see an element with xpath "//h1[string() = 'Publisher']"

    Scenario: User profile page for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "publisher" profile page
        Then I should see an element with xpath "//h1[string() = 'Publisher']"

    Scenario: Non-self user profile page is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    Scenario: User profile page is not accessible anonymously
        When I go to the "publisher" profile page
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"


    Scenario: Dashboard page is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the dashboard
        Then I should see an element with xpath "//h2[contains(string(), 'News feed')]"

    Scenario: Dashboard page is not accessible anonymously
        When I go to the dashboard
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"


    Scenario: Password reset works
        When I request a password reset for "publisher"
        Then I should see an element with xpath "//div[contains(string(), 'A reset link has been emailed to you')]"

    Scenario: Register user password must be 10 characters or longer
        When I go to register page
        And I fill in "name" with "name"
        And I fill in "fullname" with "fullname"
        And I fill in "email" with "email@test.com"
        And I fill in "password1" with "pass"
        And I fill in "password2" with "pass"
        And I press "Create Account"
        Then I should see "Password: Your password must be 10 characters or longer"

    Scenario: Register user password must contain at least one number, lowercase letter, capital letter, and symbol
        When I go to register page
        And I fill in "name" with "name"
        And I fill in "fullname" with "fullname"
        And I fill in "email" with "email@test.com"
        And I fill in "password1" with "password1234"
        And I fill in "password2" with "password1234"
        And I press "Create Account"
        Then I should see "Password: Must contain at least one number, lowercase letter, capital letter, and symbol"
