@users
Feature: user_list API

    Scenario: Ensure user autocomplete is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I search the autocomplete API for "admin"
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Ensure user autocomplete is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I search the autocomplete API for "admin"
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Ensure user autocomplete is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I search the autocomplete API for "admin"
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"

    Scenario: Ensure user autocomplete is not accessible anonymously
        When I search the autocomplete API for "admin"
        And I take a screenshot
        Then I should see an element with xpath "//body//div[contains(string(), 'Internal server error')]"
        And I should not see an element with xpath "//*[contains(string(), '"name": "admin"')]"


    Scenario: Ensure user list is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: Ensure user list is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "admin"')]"

    Scenario: Ensure user_list is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure user_list is not accessible anonymously
        When I go to the user list API
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'requires an authenticated user')]"


    Scenario: Ensure organisation membership is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API including users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure organisation membership is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API including users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure organisation membership is not accessible to non-admin members
        Given "Publisher" as the persona
        When I log in
        And I view the "department-of-health" organisation API including users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure organisation membership is not accessible to admins of other organisations
        Given "Foodie" as the persona
        When I log in
        And I view the "department-of-health" organisation API including users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure organisation membership is not accessible anonymously
        When I view the "department-of-health" organisation API including users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"
