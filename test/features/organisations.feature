@users
Feature: Organization APIs

    Scenario Outline: Organisation membership is accessible to admins of the organisation
        Given "<Persona>" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "organisation_admin"') and contains(string(), '"name": "editor"')]"

        Examples: Admins
            | Persona             |
            | SysAdmin            |
            | Organisation Admin  |

    Scenario Outline: Organisation membership is not accessible to non-admins
        Given "<Persona>" as the persona
        When I log in
        And I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

        Examples: Non-admin users
            | Persona       |
            | Publisher     |
            | Walker        |
            | Group Admin   |

    @unauthenticated
    Scenario: Organisation membership is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I view the "department-of-health" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: Organisation overview is accessible to everyone
        Given "Unauthenticated" as the persona
        When I go to organisation page
        Then I should see "Department of Health"
        And I should not see an element with xpath "//a[contains(@href, '?action=read')]"
        And I should see an element with xpath "//a[contains(@href, '/organization/department-of-health')]"

        When I view the "department-of-health" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "department-of-health"')]"
