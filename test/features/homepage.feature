@smoke
Feature: Homepage

    @homepage
    @unauthenticated
    Scenario: Smoke test to ensure Homepage is accessible
        Given "Unauthenticated" as the persona
        When I go to homepage

    @homepage
    @unauthenticated
    Scenario: As a member of the public, when I go to the main stylesheet URL, I can see the stylesheet
        Given "Unauthenticated" as the persona
        When I visit "/assets/style/main"
        Then I should see "Bootstrap"
