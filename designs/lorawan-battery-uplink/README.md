# TTGO LoRa32 v1 battery uplink (lorawan-for-esphome spike)

W2 worked example for the LoRaWAN external-component path: a TTGO LoRa32 v1 reads its battery voltage via the ADC and uplinks it through `lorawan-for-esphome` to a US915 sub-band 2 gateway. The smallest design that exercises the full new path -- external_components fetch, lorawan: block, payload sensor binding -- so the generator output can be gated by `esphome config` in CI and hand-flashed against the live ChirpStack for the spike's hardware-join test. Keys ride `fleet.secrets_ref` -> `!secret` references; the actual values are minted by the ChirpStack provision step (W3) and written to secrets.yaml. The standalone Arduino path is untouched.

The author's own build: it runs as `lorawan-battery-uplink.yaml` in their ESPHome fleet.
The same design ships with WireStudio as the `lorawan-battery-uplink` example.
