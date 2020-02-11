@users
Feature: user_list API

    Scenario: Test to ensure user autocomplete is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the user autocomplete API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Test to ensure user autocomplete is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the user autocomplete API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Test to ensure user autocomplete is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user autocomplete API
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Test to ensure user autocomplete is not accessible anonymously
        When I go to the user autocomplete API
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"


    Scenario: Test to ensure user list is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: Test to ensure user list is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: Test to ensure user_list is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Test to ensure user_list is not accessible anonymously
        When I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"

