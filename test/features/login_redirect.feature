@login_redirect
Feature: Login Redirection

    @dashboard_login
    Scenario: As an unauthenticated user, when I visit the dashboard URL I see the login page
        Given "TestOrgMember" as the persona
        When I go to the dashboard
        Then I should see the login form
        When I log in directly
        Then I should see "News feed"

    @user_edit
    Scenario: As an unauthenticated organisation member, when I visit the user edit URL I see the login page. Upon logging in I am taken to the user edit page
        Given "TestOrgMember" as the persona
        When I visit "/user/edit"
        Then I should see the login form
        When I log in directly
        Then I should see "Change details"

    @private_dataset
    @unauthenticated
    Scenario: As an unauthenticated user, when I visit the URL of a private dataset I see the login page
        Given "Unauthenticated" as the persona
        When I go to dataset "test-dataset"
        Then I should see the login form

    @public_dataset
    @unauthenticated
    Scenario: As an unauthenticated user, when I visit the URL of a public dataset I see the dataset without needing to login
        Given "Unauthenticated" as the persona
        When I go to dataset "public-test-dataset"
        Then I should see "public test"
        And I should not see an element with xpath "//h1[contains(string(), 'Login')]"

    @private_dataset
    Scenario: As an unauthenticated organisation member, when I visit the URL of a private dataset I see the login page. Upon logging in I am taken to the private dataset
        Given "TestOrgMember" as the persona
        When I go to dataset "test-dataset"
        Then I should see the login form
        When I log in directly
        Then I should see "private test"
        And I should see an element with xpath "//span[contains(string(), 'Private')]"

    @private_dataset
    Scenario: As an authenticated organisation member, when I visit the URL of a dataset private to my organisation I am taken to the private dataset
        Given "TestOrgMember" as the persona
        When I log in
        And I go to dataset "test-dataset"
        Then I should see an element with xpath "//h1[contains(string(), 'test-dataset')]"
        And I should see an element with xpath "//span[contains(string(), 'Private')]"
