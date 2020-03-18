@users
Feature: User APIs

    Scenario: User autocomplete is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I search the autocomplete API for user "admin"
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: User autocomplete is not accessible anonymously
        When I search the autocomplete API for user "admin"
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"


    Scenario: User list is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User list is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: User list is not accessible anonymously
        When I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"


    Scenario: User detail is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the "admin" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: User detail is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: User detail is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the "publisher" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: User detail for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "publisher" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "publisher"')]"

    Scenario: Non-self user detail is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: User detail is not accessible anonymously
        When I go to the "publisher" user API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"


    Scenario: User profile page is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the "admin" profile page
        And I take a screenshot
        Then I should see an element with xpath "//h1[string() = 'admin']"

    Scenario: User profile page is accessible to organisation admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" profile page
        And I take a screenshot
        Then I should see an element with xpath "//h1[string() = 'publisher']"

    Scenario: User profile page is accessible to group admins
        Given "Organisation Admin" as the persona
        When I log in
        And I go to the "publisher" profile page
        And I take a screenshot
        Then I should see an element with xpath "//h1[string() = 'publisher']"

    Scenario: User profile page for self is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "publisher" profile page
        And I take a screenshot
        Then I should see an element with xpath "//h1[string() = 'publisher']"

    Scenario: Non-self user profile page is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the "admin" profile page
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"

    Scenario: User profile page is not accessible anonymously
        When I go to the "publisher" profile page
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"


    Scenario: Dashboard page is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the dashboard
        And I take a screenshot
        Then I should see an element with xpath "//h2[contains(string(), 'News feed')]"

    Scenario: Dashboard page is not accessible anonymously
        When I go to the dashboard
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), 'Not authorised to see this page')]"


    Scenario: Password reset works
        When I request a password reset for "publisher"
        And I take a screenshot
        Then I should see an element with xpath "//div[contains(string(), 'Please check your inbox for a reset code')]"
