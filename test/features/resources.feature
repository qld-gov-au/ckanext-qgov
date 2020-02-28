@resources
Feature: Resource UI

    Scenario: When I create a Link resource, I should see a link to its URL
        Given "Admin" as the persona
        When I log in
        When I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "url" with "http://www.qld.gov.au"
        And I fill in "Name" with "Good link"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        And I press the element with xpath "//a[@title = 'Good link' and contains(string(), 'Good link')]"
        And I take a screenshot
        Then I should see "http://www.qld.gov.au"

    Scenario: When I create a Link resource without a protocol, it should default to HTTP
        Given "Admin" as the persona
        When I log in
        When I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "url" with "www.qld.gov.au"
        And I fill in "Name" with "Good link without protocol"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        And I press the element with xpath "//a[@title = 'Good link without protocol' and contains(string(), 'Good link without protocol')]"
        And I take a screenshot
        Then I should see "http://www.qld.gov.au"

    Scenario: When I create a resource with an invalid link, I should see an error
        Given "Admin" as the persona
        When I log in
        When I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "url" with "git+https://github.com/ckan/ckan.git"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        And I take a screenshot
        Then I should see "URL: Must be a valid URL"
