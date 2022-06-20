@config
Feature: Config

    Scenario: Assert that configuration values are customised
        Given "SysAdmin" as the persona
        When I log in and go to admin config page
        Then I should see "Intro Text"
        And I should see an element with id "field-ckanext.data_qld.excluded_display_name_words"
        And I should not see an element with id "field-ckan-main-css"
        And I should not see an element with id "field-ckan-site-custom-css"
