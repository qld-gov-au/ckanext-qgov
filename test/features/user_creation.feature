@user_creation
Feature: User creation

    Scenario: SysAdmin can create 'Excluded display name words' in ckan admin config
        Given "SysAdmin" as the persona
        When I log in
        And I go to "/ckan-admin/config"
        Then I should see "Excluded display name words"
        When I fill in "ckanext.data_qld.excluded_display_name_words" with "gov"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"

    Scenario: SysAdmin create a new user to the site.
        Given "SysAdmin" as the persona
        When I log in
        And I go to "/user/register"
        Then I should see an element with xpath "//input[@name='fullname']"
        When I fill in "name" with "publisher_user"
        And I fill in "fullname" with "gov user"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should not see "The username cannot contain the word 'publisher'. Please enter another username."
        And I should not see "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name."

    Scenario: Non logged-in user register to the site.
        Given "Unauthenticated" as the persona
        When I go to register page
        And I expand the browser height
        Then I should see an element with xpath "//input[@name='fullname']"
        When I fill in "name" with "publisher_user"
        And I fill in "fullname" with "gov user"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "The username cannot contain the word 'publisher'. Please enter another username."
        And I should see "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name."
