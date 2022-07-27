@config
Feature: Config

    Scenario: Assert that configuration values are customised
        Given "SysAdmin" as the persona
        When I log in and go to admin config page
        Then I should see "Intro Text"
        And I should see "Excluded display name words:"
        And I should see an element with xpath "//textarea[@id='field-ckanext.data_qld.excluded_display_name_words' and contains(string(), 'gov')]"
        And I should not see an element with id "field-ckan-main-css"
        And I should not see an element with id "field-ckan-site-custom-css"
