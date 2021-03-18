@resources
Feature: Resource UI

    Scenario Outline: Link resource should create a link to its URL
        Given "Admin" as the persona
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
        Given "Admin" as the persona
        When I create a resource with name "Non-HTTP link" and URL "git+https://github.com/ckan/ckan.git"
        And I press the element with xpath "//a[contains(@title, 'Non-HTTP link') and contains(string(), 'Non-HTTP link')]"
        And I should see "http://git+https://github.com/ckan/ckan.git"

    Scenario Outline: Link resource with private address should be rejected
        Given "Admin" as the persona
        When I create a resource with name "Bad link" and URL "<url>"
        Then I should see "URL: Domain is blocked"

        Examples:
        | url |
        | http://127.0.0.1/ |
        | http://0.0.0.0/ |
        | http://0.0.0.08/ |
        | http://0.255.255.255/ |
        | http://10.0.0.0/ |
        | http://10.255.255.255/ |
        | http://169.254.0.0:1234/latest/ |
        | http://169.254.255.255 |
        | http://172.16.0.0/ |
        | http://172.31.255.255/ |
        | http://192.168.0.0/ |
        | http://192.168.255.255/ |
