# Contributing a design

## From the studio

1. Open the design and choose **Share**. Fill in your GitHub handle and
   a few tags. The studio downloads a zip holding a folder named after
   the design, with `design.json` and `meta.yaml` inside, and opens this
   repository's upload page.
2. Unzip it and drag the folder onto the upload page. GitHub forks the
   repository for you and offers to open a pull request: do.
3. CI runs. If it fails, the check's log says why. Fix the design in the
   studio, share it again, and upload the new files to the same branch
   of your fork; the pull request picks them up.

## By hand

Add a directory under `designs/`:

```
designs/<name>/
  design.json   the design, exported from WireStudio
  meta.yaml     who made it
  README.md     optional: what it is, what you built, what to watch for
```

`<name>` is lowercase letters, digits and hyphens, and must match the
`id` inside `design.json`.

`meta.yaml`:

```yaml
author: your-github-handle
tags: [climate, oled]             # up to 8, lowercase
derived_from: some-other-design   # optional: the design here yours started from
source: https://example.com/post  # optional: a write-up or build log
```

Run the checks locally with WireStudio installed:

```
pip install "wirestudio @ git+https://github.com/moellere/WireStudio" esphome
python scripts/check.py <name>
```

## Rules

- **License.** By opening a pull request you license the design under
  [CC-BY-4.0](LICENSE) and confirm it is yours to license. If it builds
  on someone else's design here, set `derived_from`; if it builds on
  one from elsewhere, say so in the README and make sure that license
  allows it.
- **No secrets.** Credentials stay `!secret name` references, as the
  studio writes them. CI refuses literal values, but check before you
  push: a secret in a pull request is public even if the PR is closed.
- **No images yet.** Photos need screening this repository does not do
  yet, so a design directory holds only the three files above.
- **One design per pull request**, so each can be reviewed and merged
  on its own.
- **Updating your own design** is a pull request like any other. To
  change someone else's, open a new design with `derived_from` set.

A maintainer reviews every pull request before it merges; CI passing is
necessary but not sufficient. Designs that are unsafe to build (mains
wiring without isolation, a battery with no protection) may be declined
or held for changes.
