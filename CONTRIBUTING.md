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
  photos/       optional: up to 4 photos of the build (front.jpg, inside.jpg)
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

Photos must be still JPEG, PNG or WebP, at most 1 MB and 2048 px on
the long side, with lowercase names and no metadata. Phone photos carry
EXIF -- camera, time and usually GPS location -- so run

```
python scripts/strip_photos.py designs/<name>
```

which shrinks them, removes all metadata and fixes the names. The
studio's Share does the same for photos you attach there.

Run the checks locally with WireStudio installed:

```
pip install -r requirements.txt
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
- **Photos are of the build.** The device, its wiring, its enclosure,
  where it is mounted. No people, nothing identifying a home or a
  person, nothing you did not take yourself. A maintainer looks at
  every photo before it merges and declines anything else.
- **One design per pull request**, so each can be reviewed and merged
  on its own.
- **Updating your own design** is a pull request like any other. To
  change someone else's, open a new design with `derived_from` set.

## Reporting abuse

If a pull request or issue here contains abusive or illegal content,
do not download or share it. Report it to GitHub with **Report
content** (the `...` menu on the comment or file), which reaches GitHub
Trust & Safety. Then open an issue here that names the pull request
number only, so the maintainer can close it. GitHub can remove content
from a closed pull request; this repository cannot.

## Review

A maintainer reviews every pull request before it merges; CI passing is
necessary but not sufficient. Designs that are unsafe to build (mains
wiring without isolation, a battery with no protection) may be declined
or held for changes.
