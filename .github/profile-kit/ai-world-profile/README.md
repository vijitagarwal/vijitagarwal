# Self-updating contribution graphic: ai-world-profile

`ai-world-profile/ledger.svg` is redrawn from your public GitHub contribution calendar by `.github/workflows/refresh-ai-world-profile.yml`.

**When it runs:** every day at 02:23 UTC, whenever you press **Run workflow** for "Refresh ai-world-profile ledger" in the repository's Actions tab, and whenever you change a file in this folder. It runs whether or not the README currently shows this theme, so switching themes later never shows an old picture.

**What it does:** asks GitHub for your contribution counts for the last 12 calendar months, redraws `ai-world-profile/ledger.svg` with the files in this folder (nothing to install), and, only if the picture changed, commits it as `github-actions[bot]`. Those commits do not count as your contributions and do not add green squares. It only reads public data. It touches nothing outside the `ai-world-profile` folder.

**Files**

| File | What it is |
| --- | --- |
| `refresh.py` | the script the workflow runs |
| `output.txt` | one line saying where the picture is saved, counted from the top of the repository (`ai-world-profile/ledger.svg`); keep it in step with the theme folder's name |
| `graphic.py` | the design of the picture (layout, colours, how bars and towers are sized) |
| `kitlib.py` | small drawing and date helpers |
| `glyphs.json` | the letter shapes, so the text looks identical on any machine without fonts |
| `frame.json` | the parts of the picture that never change with the data |
| `NOTICE.md` | licences of the fonts the letter shapes come from |

**Try it by hand** (Python 3.8 or newer, nothing to install). `--print-snapshot` shows the numbers without writing anything:

```bash
GH_TOKEN=<a GitHub token> python3 .github/profile-kit/ai-world-profile/refresh.py --login <your-username> --print-snapshot
```

**If the picture stops updating**

1. Open the repo's **Actions** tab and the latest "Refresh ai-world-profile ledger" run. The red step says what went wrong in plain words.
2. GitHub pauses scheduled workflows in a public repository after 60 days without repository activity. If the workflow shows as disabled, click **Enable workflow**, then **Run workflow**.
3. If GitHub refuses the built-in token, add a repository secret named `PROFILE_TOKEN` (Settings, Secrets and variables, Actions) holding a classic personal access token with no scopes ticked.

**Rename the folder?** Do not. The alternate README, `output.txt` and the workflow all use the folder's name.

**Switch it off:** delete `.github/workflows/refresh-ai-world-profile.yml`. The picture stays as it is.
