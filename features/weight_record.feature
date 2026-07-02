# language: en
# Feature: Register Weight Telemetry Record
# Related User Story: US-ES-01 – As an IoT device I want to register my weight reading
#                                so that the edge service can compute the physical stock.

Feature: Register weight telemetry record
  As a Restock IoT smart scale device
  I want to register a weight reading to the edge service
  So that the physical stock is calculated and stored

  Scenario: Successful weight record creation with valid device
    Given a registered device with id "device-001"
    And the device has a custom supply weight threshold of 250.0 grams
    When the device sends a weight reading of 500.0 grams
    Then the weight record is created successfully
    And the physical stock is calculated as 2 units
    And the response contains the average physical stock

  Scenario: Weight record rejected for unknown device
    Given no device with id "device-unknown" is registered
    When the device sends a weight reading of 500.0 grams
    Then the request is rejected with a "Device not found" error
