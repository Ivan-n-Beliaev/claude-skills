# Claude Code skills

Three skills I use with Claude Code. Each folder is one skill: a `SKILL.md` the agent reads, plus the scripts and reference notes it calls.

| Skill | What it does |
|---|---|
| `tutorial` | Turns raw screen-recording takes of an app into a finished YouTube tutorial: cuts dead air, sets the speed, frames the camera, then writes captions, chapters, title, description, tags and thumbnails. |
| `corpus` | Turns a NotebookLM notebook (a book, a set of papers) into linked concept notes in an Obsidian vault. Claims cite numbered passages in the source where NotebookLM returns a resolvable span, and the rest are labelled as unanchored. Two audit scripts flag citation anchors that do not exist and, for quotes written in bold before their citation, quotes whose best-matching passage differs from the cited one. |
| `social-poster` | Builds a 4:5 post image from HTML and has the agent check it at feed size before delivery. |

## How they were written

AI agents wrote the scripts and drafted most of the prose. I specified each skill, ran it on real work, reviewed the output, and had the rules written back into the skill after each failed run. Most of the "do not" lines in these files come from a specific failed run. Where the files say "the user", that is me.

These are working files, not a product. Timings, rates and counts come from my own runs. Layout and platform figures, such as YouTube badge sizes and character limits, are approximations. The tutorial notes carry numbers from two generations of the edit; `scripts/buildplan.py` holds the current ones.

## Use

Copy a folder into `.claude/skills/` in your project. The examples use my own product, Pelaa, a video analysis app for hockey coaches. Replace the product name, colours and paths with yours.

Requirements differ per skill:

- `tutorial`: `ffmpeg` and `ffprobe`, Python 3 with `numpy` and `Pillow`, Node with `puppeteer`, and an AssemblyAI key in `ASSEMBLYAI_API_KEY`. The recording's audio is uploaded to AssemblyAI for transcription. Defaults assume macOS.
- `corpus`: `VAULT_ROOT` set to your vault, the `nlm` NotebookLM CLI, and `import_sources.py` from the notebooklm-skill plugin (see Credits). `nlm` is an unofficial third-party client and may not comply with NotebookLM's terms; check them and use it at your own risk. Queries go to Google NotebookLM through that CLI. Use only sources you have the right to process.
- `social-poster`: Node with `puppeteer`, Python 3 with `Pillow`, and `COMMONS_UA` set to a descriptive user agent with a contact, as Wikimedia's policy requires. Its scripts call the Wikimedia Commons API. Template images (`icon.png`, `plate.png`) are not included.

## Credits

The `corpus` skill started from the notebooklm-skill plugin in [ArtemXTech/personal-os-skills](https://github.com/ArtemXTech/personal-os-skills), MIT, Copyright (c) 2025 Artem Zhutov. `corpus_resolve.py` reads the same JSON and writes the same passage format as that plugin's scripts.

## License

MIT for the code and text in this repository. Third-party names identify the tools they refer to and belong to their owners. The Pelaa name and logo are not licensed by this file.
