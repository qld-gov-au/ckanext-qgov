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

    Scenario: Organisation list is accessible via the dashboard
        Given "SysAdmin" as the persona
        When I log in
        And I go to the dashboard
        And I press "My Organisations"
        Then I should see "Test Organisation"
        And I should see an element with xpath "//a[contains(@href, 'organization/new') and contains(string(), 'Add Organisation')]"

    Scenario: As a sysadmin, when I create an organisation with a long name, it should be preserved
        Given "SysAdmin" as the persona
        When I log in
        And I go to organisation page
        And I click the link to "/organization/new"
        And I fill in title with random text starting with "Org name more than 35 characters"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        And I take a debugging screenshot
        # Breadcrumb should be truncated but preserve full name in a tooltip
        Then I should see an element with xpath "//ol[contains(@class, 'breadcrumb')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"

        # Search facets should be truncated but preserve full name in a tooltip
        When I create a dataset and resource with key-value parameters "notes=Testing long org name::owner_org=Org name more than" and "name=Test"
        And I press "Org name more than"
        Then I should see an element with xpath "//li[contains(@class, 'nav-item')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
        When I press the element with xpath "//li[contains(@class, 'nav-item')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
        Then I should see an element with xpath "//li[contains(@class, 'nav-item') and contains(@class, 'active')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
        When I go to dataset page
        Then I should see an element with xpath "//li[contains(@class, 'nav-item')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
        When I press the element with xpath "//li[contains(@class, 'nav-item')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
        Then I should see an element with xpath "//li[contains(@class, 'nav-item') and contains(@class, 'active')]//a[contains(string(), 'Org name more than') and contains(string(), '...') and contains(@title, 'Org name more than 35 characters')]"
