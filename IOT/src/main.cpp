#include "ECE140_WIFI.h"
#include "ECE140_MQTT.h"
#include <Adafruit_BMP085.h>
#include "esp_adc_cal.h"
#include <WiFi.h>
#include <esp_wifi.h>

const char* clientId = CLIENT_ID;
const char* topicPrefix = TOPIC_PREFIX;

ECE140_MQTT mqtt(clientId, topicPrefix);
ECE140_WIFI wifi;

// WiFi credentials
const char* ucsdUsername = "";//UCSD_USERNAME;
const char* ucsdPassword = "";//UCSD_PASSWORD;
const char* wifiSsid = /*"RESNET-GUEST-DEVICE";//*/WIFI_SSID;
const char* nonEnterpriseWifiPassword = /*"ResnetConnect";//*/NON_ENTERPRISE_WIFI_PASSWORD;

unsigned long lastPublish = 0;

Adafruit_BMP085 bmp;
bool sensorAttached = true;

String MAC;

void setup() {
    Serial.begin(115200);

    delay(1000);
    Serial.println("Starting ESP32 sensor node...");

    if (!bmp.begin()) {
        Serial.println("Could not find a valid BMP085 sensor, switching to onboard!");
        sensorAttached = false;
    }

    if (strlen(ucsdUsername) > 0 && strlen(ucsdPassword) > 0) {
        wifi.connectToWPAEnterprise(wifiSsid, ucsdUsername, ucsdPassword);
    } else {
        wifi.connectToWiFi(wifiSsid, nonEnterpriseWifiPassword);
    }

    uint8_t baseMac[6];
    esp_err_t ret = esp_wifi_get_mac(WIFI_IF_STA, baseMac);
    if (ret == ESP_OK) {
        char macStr[18]; // 6 bytes * 2 chars + 5 colons + null terminator
        sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
            baseMac[0], baseMac[1], baseMac[2], baseMac[3], baseMac[4], baseMac[5]);
        MAC = macStr;
    } else {
      Serial.println("Failed to read MAC address");
    }

    Serial.println("Device MAC address: " + MAC);
}

void loop() {
    mqtt.loop();

    if (millis() - lastPublish > 5000) {
        lastPublish = millis();
    
        String payload;
        float temperature;
        if (sensorAttached) {
            temperature = bmp.readTemperature();

            float pressure = bmp.readPressure();
            
            payload = "{\"value\": " + String(pressure) + "}";
            mqtt.publishMessage(MAC + "/pressure", payload);
            Serial.println(payload);
        } else {
            temperature = temperatureRead() - 15;
        }

        payload = "{\"value\": " + String(temperature) + "}";
        mqtt.publishMessage(MAC + "/temperature", payload);
        Serial.println(payload);
    }
}