@resources
Feature: Resource UI

    Scenario Outline: Link resource should create a link to its URL
        Given "SysAdmin" as the persona
        When I create a resource with name "<name>" and URL "<url>"
        And I press the element with xpath "//a[contains(@title, '<name>') and contains(string(), '<name>')]"
        Then I should see "<url>"

        Examples:
        | name | url |
        | Good link | http://www.qld.gov.au |
        | Good IP address | http://1.2.3.4 |
        | Domain starting with numbers | http://1.2.3.4.example.com |
        | Domain ending with numbers | http://example.com.1.2.3.4 |
        | Domain ending with private | http://example.com.private |

    Scenario: Link resource with missing or invalid protocol should use HTTP
        Given "SysAdmin" as the persona
        When I create a resource with name "Non-HTTP link" and URL "git+https://github.com/ckan/ckan.git"
        And I press the element with xpath "//a[contains(@title, 'Non-HTTP link') and contains(string(), 'Non-HTTP link')]"
        And I should see "http://git+https://github.com/ckan/ckan.git"
