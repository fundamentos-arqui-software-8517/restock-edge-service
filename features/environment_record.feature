# language: en
# Feature: Register Environment Telemetry Record
# Related User Story: US-ES-02 – As an IoT device I want to register temperature and humidity readings
#                                so that the edge service can detect environment anomalies.

Feature: Register environment telemetry record
  As a Restock IoT smart scale device
  I want to register a temperature and humidity reading to the edge service
  So that environment anomalies are detected and the record is stored

  Scenario: Successful environment record with normal readings
    Given a registered device with id "device-001"
    And the device has temperature thresholds between 0.1 and 90.1 Celsius
    And the device has humidity thresholds between 0.1 and 90.1 percent
    When the device sends temperature 25.0 and humidity 60.0
    Then the environment record is created successfully
    And no anomaly is flagged for temperature
    And no anomaly is flagged for humidity
    And the response contains average temperature and average humidity

  Scenario: Environment record flags temperature anomaly
    Given a registered device with id "device-001"
    And the device has temperature thresholds between 0.1 and 30.0 Celsius
    When the device sends temperature 50.0 and humidity 60.0
    Then the environment record is created successfully
    And the response contains temperature_is_anomaly as true

  Scenario: Environment record rejected for unknown device
    Given no device with id "device-unknown" is registered
    When the device sends temperature 25.0 and humidity 60.0
    Then the request is rejected with a "Device not found" error
