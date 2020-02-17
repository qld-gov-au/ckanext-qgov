@users
Feature: organization_show API

    Scenario: Ensure organisation membership is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure organisation membership is accessible to organisation admins
        Given "Group Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure organisation membership is not accessible to non-admin members
        Given "Publisher" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure organisation membership is not accessible to admins of other organisations
        Given "Foodie" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure organisation membership is not accessible anonymously
        When I view the "department-of-health" organisation API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"


    Scenario: Ensure organisation overview without membership is accessible to non-admin members
        Given "Publisher" as the persona
        When I log in
        And I view the "department-of-health" organisation API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"

    Scenario: Ensure organisation overview without membership is accessible to admins of other organisations
        Given "Foodie" as the persona
        When I log in
        And I view the "department-of-health" organisation API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"

    Scenario: Ensure organisation overview without membership is accessible anonymously
        When I view the "department-of-health" organisation API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"
