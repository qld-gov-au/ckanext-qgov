@smoke
Feature: Homepage

    @homepage
    @unauthenticated
    Scenario: Smoke test to ensure Homepage is accessible
        Given "Unauthenticated" as the persona
        When I go to homepage

    @homepage
    @unauthenticated
    Scenario: As a member of the public, when I go to the consistent asset URLs, I can see the asset
        Given "Unauthenticated" as the persona
        When I visit "/assets/css/main"
        Then I should see "Bootstrap"
        When I visit "/assets/css/font-awesome"
        Then I should see "Font Awesome"
        When I visit "/assets/css/select2"
        Then I should see "select2-container"
        When I visit "/assets/js/jquery"
        Then I should see "jQuery"
        When I visit "/assets/js/bootstrap"
        Then I should see "Bootstrap"
