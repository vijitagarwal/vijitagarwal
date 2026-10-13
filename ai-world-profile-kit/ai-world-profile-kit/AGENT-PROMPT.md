# Prompt for a coding agent

Use an agent that runs in a terminal on your computer and is already signed in to GitHub (Claude Code, Codex CLI, or the agent mode in Cursor / VS Code with its terminal). A chat window that cannot run `git` on your machine cannot do this.

Unzip the kit, then give the agent the unzipped `ai-world-profile-kit` folder and paste the prompt below. Replace `<PATH-TO-KIT>` with the real path. Give it nothing else: no preview page and no earlier chat.

---

You are working in a terminal on my computer. Task: publish a finished GitHub profile README to my public profile repository `vijitagarwal/vijitagarwal`. The design is already built. Your only job is to place the files and push them. Do not design, rewrite, reformat, optimise or "improve" anything.

INPUT
The folder `<PATH-TO-KIT>` contains:
- `repo/README.md` and `repo/assets/*.svg` (23 SVG images). This is everything that gets committed.
- `avatar/` is for me to upload by hand in GitHub settings. Do not commit it.
- `HOW-TO-PUSH.md` is the same procedure written for a human.

HARD RULES
1. Never edit, re-save, minify, prettify or regenerate any file from the kit. The SVGs and the README must be copied byte for byte. Do not run svgo, prettier or any formatter.
2. Never run `git init`. Never use `--allow-unrelated-histories`. Never force-push (`--force`, `--force-with-lease`). Never rewrite history.
3. Clone into a brand-new empty folder. Do not touch any other repository or folder.
4. If anything is unexpected (clone or auth fails, the repo contains files other than an old README and its images, a push is rejected, a rebase conflicts), stop and tell me exactly what happened. Do not improvise a workaround.

STEPS
1. `git clone https://github.com/vijitagarwal/vijitagarwal.git` into a new folder and `cd` into it. Print `git branch --show-current` and `git ls-files`.
2. Remove everything currently tracked with `git rm -r -q .` so that no old README text or old image survives. If `git ls-files` shows any file that is not an old README or one of its images (a LICENSE, for example), list it and ask me before removing it.
3. Copy the contents of the kit's `repo/` folder into the clone's root, so `README.md` is at the top level and `assets/` is next to it.
4. Verify, and show me the output of each check:
   - there is exactly one README in the repo, `README.md` at the root;
   - `git grep -n -e "<<<<<<<" -e ">>>>>>>" -- README.md` prints nothing;
   - every `src="assets/..."` in `README.md` exists on disk, and every file in `assets/` is referenced by `README.md`;
   - every `.svg` passes `xmllint --noout` (skip this if `xmllint` is not installed, and say so);
   - every copied file is byte-identical to its original in the kit (`cmp`);
   - `git status --short`, summarised in one line per change type.
5. Stop here and show me the results. Wait for me to answer "commit" before going on. (If I already told you to run everything end to end, skip this pause.)
6. Then run: `git add -A`, `git commit -m "Redesign profile README: AI world theme"`, `git pull --rebase`, `git push`.
7. Report the commit hash and the link https://github.com/vijitagarwal. Remind me to hard-refresh the page and to upload `avatar/avatar-1000.png` in GitHub Settings, because you cannot do that part.
