# wirestudio-designs

Designs people have built in [WireStudio](https://github.com/moellere/WireStudio)
and shared. Each one is a complete `design.json`: the board, the parts,
how they are wired, and enough for the studio to regenerate the ESPHome
config, schematic, PCB and enclosure.

## Using a design

In the studio, open **Community designs**, pick one, and import it. It
lands in your own design list as a copy you can change; nothing links it
back here.

Without the studio, each design's `design.json` is under
`designs/<name>/`. `index.json` on the
[`index` branch](https://github.com/moellere/wirestudio-designs/tree/index)
lists them all with their board, parts, author and tags.

## Sharing a design

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: **Share** in the
studio prepares the files, you open a pull request, CI checks the
design the way the studio does, and a maintainer reviews and merges it.

## What CI checks

Every design, on every pull request:

- it loads in WireStudio, migrated to the current schema;
- the ESPHome YAML WireStudio generates from it passes `esphome config`;
- it holds no literal credentials -- Wi-Fi passwords, API keys and
  LoRaWAN keys stay `!secret` references;
- its directory holds only `design.json`, `meta.yaml` and an optional
  `README.md`.

Passing CI means the design is well-formed. It does not mean anyone has
built it; a design's README says whether its author has.

## License

Designs are licensed under [CC-BY-4.0](LICENSE): use, change and
redistribute them, commercially or not, crediting the author. The
studio carries each design's author and `derived_from` link so credit
survives a remix. The scripts and workflows are [MIT](LICENSE-CODE).
