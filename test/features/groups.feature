@users
Feature: Group APIs

    Scenario Outline: Group membership is accessible to admins of the group
        Given "<Persona>" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "group_admin"') and contains(string(), '"name": "walker"')]"

        Examples: Admins
            | Persona      |
            | SysAdmin     |
            | Group Admin  |

    Scenario Outline: Group membership is not accessible to non-admins
        Given "<Persona>" as the persona
        When I log in
        And I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

        Examples: Non-admin users
            | Persona             |
            | Organisation Admin  |
            | Walker              |

    @unauthenticated
    Scenario: Group membership is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I view the "silly-walks" group API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: Group overview is accessible to everyone
        Given "Unauthenticated" as the persona
        When I go to "/group"
        Then I should see "silly-walks"
        And I should not see an element with xpath "//a[contains(@href, '?action=read')]"
        And I should see an element with xpath "//a[contains(@href, '/group/silly-walks')]"

        When I view the "silly-walks" group API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "silly-walks"')]"
