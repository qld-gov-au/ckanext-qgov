@organisations
Feature: Organization APIs

    Scenario Outline: Organisation membership is accessible to admins of the organisation
        Given "<Persona>" as the persona
        When I log in
        And I view the "test-organisation" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "test_org_admin"') and contains(string(), '"name": "test_org_editor"')]"

        Examples: Admins
            | Persona       |
            | SysAdmin      |
            | TestOrgAdmin  |

    Scenario Outline: Organisation membership is not accessible to non-admins
        Given "<Persona>" as the persona
        When I log in
        And I view the "test-organisation" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

        Examples: Non-admin users
            | Persona       |
            | TestOrgEditor |
            | TestOrgMember |
            | Group Admin   |

    @unauthenticated
    Scenario: Organisation membership is not accessible anonymously
        Given "Unauthenticated" as the persona
        When I view the "test-organisation" organisation API "including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": false') and contains(string(), 'Authorization Error')]"

    @unauthenticated
    Scenario: Organisation overview is accessible to everyone
        Given "Unauthenticated" as the persona
        When I go to organisation page
        And I expand the browser height
        Then I should see "Food Standards Agency"
        And I should not see an element with xpath "//a[contains(@href, '?action=read')]"
        And I should see an element with xpath "//a[contains(@href, '/organization/food-standards-agency')]"
        When I press "Food Standards Agency"
        And I take a debugging screenshot
        And I press "Activity Stream"
        Then I should see "created the org"

        When I view the "food-standards-agency" organisation API "not including" users
        Then I should see an element with xpath "//*[contains(string(), '"success": true') and contains(string(), '"name": "food-standards-agency"')]"

    # 'Add Organisation' button is fixed in our fork
    @custom
    Scenario: Organisation list is accessible via the dashboard
        Given "SysAdmin" as the persona
        When I log in
        And I go to the dashboard
        And I press "My Organisations"
        Then I should see "Test Organisation"
        And I should see an element with xpath "//a[contains(@href, 'organization/new') and contains(string(), 'Add Organisation')]"
