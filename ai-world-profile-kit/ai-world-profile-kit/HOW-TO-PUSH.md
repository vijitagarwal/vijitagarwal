# Publish the AI-world profile (by hand)

Your profile repo is `vijitagarwal/vijitagarwal`. Everything that goes into it is in the `repo/` folder of this kit:
`README.md` and an `assets/` folder with 23 SVG images. Nothing else gets committed.

This replaces whatever profile theme is live now, including the military one if you already published it.

Follow these in order. Do not use `git init` and do not use `--allow-unrelated-histories`; those are what made the old and new README show together last time.

## 1. Clone fresh into an empty folder

```bash
git clone https://github.com/vijitagarwal/vijitagarwal.git
cd vijitagarwal
git branch --show-current     # normally: main
git ls-files                  # see what is in the repo today
```

## 2. Remove what is there now

This clears the old README and any old images, so nothing old can show up next to the new profile.

```bash
git rm -r -q .
```

If `git ls-files` showed a file you want to keep (a LICENSE, for example), run `git restore --staged --worktree LICENSE` for that file afterwards.

## 3. Copy the kit in

Copy what is inside the kit's `repo/` folder into the repo root, so `README.md` sits at the top and `assets/` next to it.

macOS / Linux:

```bash
cp -R /path/to/ai-world-profile-kit/repo/. .
```

Windows PowerShell:

```powershell
Copy-Item -Recurse -Force C:\path\to\ai-world-profile-kit\repo\* .
```

## 4. Check before you commit

```bash
git status --short                                  # old files show as D (deleted); README.md and assets/ show as new (??)
git grep -n -e "<<<<<<<" -e ">>>>>>>" -- README.md  # must print nothing
ls assets | wc -l                                   # 23 (on Windows: (dir assets).Count)
```

## 5. Commit and push

```bash
git add -A
git commit -m "Redesign profile README: AI world theme"
git pull --rebase
git push
```

If `git push` is rejected, stop and send me the message. Do not force-push.

## 6. Upload the avatar

GitHub does not take the avatar from the repo. Go to **Settings → Public profile**, click your picture, choose **Upload a photo**, and pick `avatar/avatar-1000.png` from this kit.

## 7. Look at it

Open https://github.com/vijitagarwal and hard-refresh (Ctrl+Shift+R, or Cmd+Shift+R on a Mac). The images are cached for a short time, so if something looks old, wait a minute and refresh again.

## Notes

- The ledger is a snapshot of your monthly contributions (Nov 2025 to Oct 2026). It will not update by itself; ask me for a refreshed `ledger.svg` whenever you want it redone.
- In the Training run section, the five runs are your real projects and study topics. The loss curve is decoration and is labelled "illustrative" in the image.
- The animation stops for anyone whose system is set to "reduce motion" and they see a still version instead. That is intended.
- Phones shrink README images, so on a small screen the hero and the section titles stay readable and the small labels get tiny. GitHub does that for every image-based profile.
- To go back later, run `git revert HEAD` in a fresh clone and push, or repeat these steps with another kit.
