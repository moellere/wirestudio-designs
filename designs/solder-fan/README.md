# Solder exhaust fan controller

Wemos D1 Mini driving a 12V 4-wire PWM fan from a panel potentiometer: the knob sets the exhaust speed and the fan's tachometer reports RPM. The fan's +12V comes from a separate supply sharing ground with the board; only the 25kHz PWM (D5) and open-collector tach (D2) touch the ESP. A wirestudio port of the classic ESPHome solder-fan config.

The author's own build: it runs as `solder-fan.yaml` in their ESPHome fleet.
The same design ships with WireStudio as the `solder-fan` example.
