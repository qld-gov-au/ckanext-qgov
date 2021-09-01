@users
Feature: Group APIs

    Scenario: Group membership is accessible to sysadmins
        Given "SysAdmin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "walker"')]"

    Scenario: Group membership is accessible to admins of the group
        Given "Group Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "walker"')]"

    Scenario: Group membership is not accessible to non-admins
        Given "Walker" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Group membership is not accessible to other admins
        Given "Organisation Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"

    Scenario: Group membership is not accessible anonymously
        When I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false,') and contains(string(), 'Authorization Error')]"


    Scenario: Group overview is accessible to admins of the group
        Given "Group Admin" as the persona
        When I log in
        And I view the "silly-walks" group API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"

    Scenario: Group overview is accessible to non-admins
        Given "Walker" as the persona
        When I log in
        And I view the "silly-walks" group API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"

    Scenario: Group overview is accessible to other admins
        Given "Foodie" as the persona
        When I log in
        And I view the "silly-walks" group API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"

    Scenario: Group overview is accessible anonymously
        When I view the "silly-walks" group API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true,') and contains(string(), '"name": "silly-walks"')]"
