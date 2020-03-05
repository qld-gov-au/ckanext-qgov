@resources
Feature: Resource UI

    Scenario: Link resource should create a link to its URL
        Given "Admin" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "url" with "http://www.qld.gov.au"
        And I fill in "name" with "Good link"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        And I press the element with xpath "//a[contains(@title, 'Good link') and contains(string(), 'Good link')]"
        Then I take a screenshot
        And I should see "http://www.qld.gov.au"

    Scenario: Link resource with missing or invalid protocol should use HTTP
        Given "Admin" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "url" with "git+https://github.com/ckan/ckan.git"
        And I fill in "name" with "Non-HTTP link"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        And I press the element with xpath "//a[contains(@title, 'Non-HTTP link') and contains(string(), 'Non-HTTP link')]"
        Then I take a screenshot
        And I should see "http://git+https://github.com/ckan/ckan.git"
