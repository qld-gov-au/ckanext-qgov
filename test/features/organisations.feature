@users
Feature: Organization APIs

    Scenario: Organisation membership is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "organisation_admin"') and contains(string(), '"name": "editor"')]"

    Scenario: Organisation membership is accessible to admins of the organisation
        Given "Organisation Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "organisation_admin"') and contains(string(), '"name": "editor"')]"

    Scenario: Organisation membership is not accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Organisation membership is not accessible to other admins
        Given "Foodie" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Organisation membership is not accessible anonymously
        When I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"


    Scenario: Organisation overview is accessible to admins of the organisation
        Given "Organisation Admin" as the persona
        When I log in
        And I view the "department-of-health" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"

    Scenario: Organisation overview is accessible to non-admins
        Given "Publisher" as the persona
        When I log in
        And I view the "department-of-health" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"

    Scenario: Organisation overview is accessible to other admins
        Given "Foodie" as the persona
        When I log in
        And I view the "department-of-health" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"

    Scenario: Organisation overview is accessible anonymously
        When I view the "department-of-health" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "department-of-health"')]"
