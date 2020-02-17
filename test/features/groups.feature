@users
Feature: group_show API

    Scenario: Ensure group membership is accessible to sysadmins
        Given "Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure group membership is accessible to group admins
        Given "Group Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "publisher"')]"

    Scenario: Ensure group membership is not accessible to non-admin members
        Given "Walker" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure group membership is not accessible to admins of other groups
        Given "Group Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Ensure group membership is not accessible anonymously
        When I view the "silly-walks" group API "including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"


    Scenario: Ensure group overview without membership is accessible to non-admin members
        Given "Walker" as the persona
        When I log in
        And I view the "silly-walks" group API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"

    Scenario: Ensure group overview without membership is accessible to admins of other groups
        Given "Foodie" as the persona
        When I log in
        And I view the "silly-walks" group API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"

    Scenario: Ensure group overview without membership is accessible anonymously
        When I view the "silly-walks" group API "not including" users
        And I take a screenshot
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"
