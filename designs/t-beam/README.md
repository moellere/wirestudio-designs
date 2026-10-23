# LilyGO T-Beam (template)

A starting point for the LilyGO T-Beam, not a finished build: every
onboard peripheral wired to the pins the board uses, ready to add to.

- SX1276 LoRa radio on SPI, set to 915 MHz. T-Beams are sold in 433,
  868 and 915 MHz variants; set `frequency` to match yours and your
  region before transmitting.
- NEO-6M GPS on its own UART (GPIO34 RX, GPIO12 TX, 9600 baud).
- The user button on GPIO38.
- An SSD1306/SH1106 OLED on I2C and a DHT sensor on GPIO13, the usual
  add-ons; delete them if your board has neither.

The AXP192 power-management chip has no ESPHome core component, so the
design leaves it out; the board powers its peripherals at its defaults.

The author's own T-Beam runs standalone LoRaWAN firmware rather than
this design.
