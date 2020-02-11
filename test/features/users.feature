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
        Then I should see an element with xpath "//h1[contains(string(), 'The resource you have requested is currently unavailable.')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"
