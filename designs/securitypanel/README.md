# Whole-house door/window/motion security panel

ESP8266 D1 Mini reads 12 contact + motion sensors through an MCP23017 over I2C and drives a piezo buzzer (RTTTL) on D7. Each sensor pin is its own gpio_input component bound to an expander_pin connection.

The author's own build: it runs as `securitypanel.yaml` in their ESPHome fleet.
The same design ships with WireStudio as the `securitypanel` example.
