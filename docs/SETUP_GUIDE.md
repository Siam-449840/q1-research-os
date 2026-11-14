# Setup Guide

From a clean machine to your first gated research project. Time: about 20 minutes for the core,
plus optional tools.

---

## 1. Requirements

| Need | Version | Why | Check |
|---|---|---|---|
| macOS, Linux, or Windows with WSL2 | any recent | the scripts are POSIX shell + Python | n/a |
| Python | ≥ 3.9 | `rosctl` (stdlib only, no packages) | `python3 --version` |
| git | any | version control is part of the method (protocol freeze, provenance) | `git --version` |
| uv | recent | reproducible Python environments for your analysis code, tool installs | `uv --version` |
| An AI coding agent | Claude Code and/or Antigravity (others that read `AGENTS.md` also work) | does the research work | n/a |
| Disk | ≥ 10 GB free recommended | datasets, PDFs, environments | `df -h ~` |

Install uv if missing: `brew install uv` (macOS) or follow https://docs.astral.sh/uv/getting-started/installation/.

## 2. Install the framework

```bash
git clone https://github.com/Siam-449840/q1-research-os.git
cd q1-research-os
./install.sh                 # links `rosctl` into ~/.local/bin
rosctl doctor                # shows what is installed and how to get what is missing
```

If `rosctl` is "not found", add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` or `~/.bashrc`
and open a new terminal.

### Optional components

```bash
./install.sh --with-tools     # paper-search-mcp, PaperQA2, academic-refchecker, bibvet, zotero-mcp (via uv)
./install.sh --with-extras    # pinned K-Dense scientific skills + claude-scholar → curated 29-skill pack
./install.sh --global-skills  # copy q1-* skills to ~/.claude/skills (all Claude Code projects)
```

After `--with-extras`, add the printed line to your shell profile:

```bash
export ROS_EXTRA_SKILLS="$HOME/.local/share/q1-research-os/extra-skills"
```

New projects then receive the curated skills automatically (statistics, visualisation, writing,
peer review, citation management, geospatial, Bayesian modelling, anti-AI-style writing, and others).
All third-party skills are fetched at the commits pinned in [`tools.lock`](../tools.lock).

## 3. Create a project

```bash
rosctl init ~/research/rice-transfer --domain agriculture
cd ~/research/rice-transfer
```

What you get:

```
AGENTS.md  CLAUDE.md  GEMINI.md      ← the constitution (identical; one per agent family)
PROPOSAL.md                          ← you write this (docs/PROPOSAL_GUIDE.md)
.claude/skills/ .agents/skills/ .agent/skills/   ← q1-* skills (+ extras) for every agent
.ros/state.json  .ros/domain/  .ros/core/        ← managed by rosctl
literature/ protocol/ data/ analysis/ results/ manuscript/ refs/ ledgers/ review/ submission/
```

Available domain packs: `agriculture` (deep, 13 subfields), `software-engineering`, `_template`
(blank, for any discipline; see "Add your discipline" in the README).

## 4. Connect your agent

### Claude Code

1. Open a terminal in the project folder and run `claude` (or open the folder in the desktop app).
2. Claude Code reads `CLAUDE.md` automatically and discovers the skills in `.claude/skills/`.
3. Optional MCP servers: `cp .mcp.json.example .mcp.json` (requires `--with-tools`). Approve the
   servers when Claude Code asks.
4. Start prompt:

   ```
   Use the q1-pipeline skill. Read AGENTS.md and PROPOSAL.md, run `rosctl status`, and work through
   the stages. Stop at every human gate and give me the checkpoint in my communication language.
   ```

### Antigravity

1. Open the project folder as the workspace.
2. Antigravity reads `AGENTS.md` / `GEMINI.md` as workspace rules and the skills in `.agents/skills/`
   (`.agent/skills/` is included for older versions).
3. Optional MCP servers: add `paper-search` (command `paper-search-mcp`) and `zotero` (command
   `zotero-mcp`, argument `serve`, env `ZOTERO_LOCAL=true`) in Antigravity's MCP server settings, using
   the same definitions as `.mcp.json.example`.
4. Start prompt:

   ```
   Follow AGENTS.md. Use the q1-pipeline skill in .agents/skills. Start with `rosctl status` and
   continue from the current stage; stop at each human gate with a checkpoint.
   ```

### Other agents (Codex, Gemini CLI, Cursor, ...)

Any agent that reads `AGENTS.md` (or can be told to) works: point it at `AGENTS.md` and
`.agents/skills/q1-pipeline/SKILL.md`. The gates are enforced by `rosctl`, not by the agent.

## 5. Optional services

| Service | Use | Setup |
|---|---|---|
| Zotero 7 | personal library, PDF annotation, BibTeX export | install Zotero desktop; Settings → Advanced → enable the local API; add the Better BibTeX plugin for stable citekeys |
| PaperQA2 (`pqa`) | question answering over your PDFs with cited passages | needs an LLM API key; with Google Gemini set `GEMINI_API_KEY` and pass `--llm gemini/<model>` etc. (see `q1-literature`). Use `pqa ... view` to check flags without any API call |
| Google Earth Engine | satellite data at scale | free registration for research / non-commercial use |
| Copernicus CDS | ERA5 / AgERA5 | free account; put the API key in `~/.cdsapirc` (never in the project) |
| OpenAlex | snowballing (no key needed) | optional `export OPENALEX_MAILTO=you@example.org` for the polite pool |

Keep every key in your shell profile or a git-ignored `.env`, never in committed files.

## 6. Verify the installation

```bash
rosctl doctor
rosctl lint-proposal examples/agriculture-rice-yield-transfer/PROPOSAL.md   # from the framework folder: expect 100/100
python3 -m unittest discover -s tests                                      # from the framework folder: expect OK
```

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `rosctl: command not found` | `~/.local/bin` not on PATH | add it to your shell profile, open a new terminal |
| `rosctl approve` says REFUSED | not an interactive terminal (an agent tried to approve) | run it yourself in a normal terminal; this is by design |
| `approve` says "running inside an AI agent session" | you ran it from the agent's shell or a terminal it spawned | open your own Terminal app and run it there |
| Gate: "not verified against a registry" | `refs.bib` changed since the last verification | `rosctl verify-refs` (needs internet), then fix any `not_found` / `title_mismatch` / `retracted` entry |
| Gate: "locator does not resolve uniquely" | provenance row points at nothing or at several rows | use `keycol=keyval:column`, `$.json.path` or `line:N` |
| Gate: "no split manifest" | CV code does not export its folds | write `results/splits/<design>.csv` (fold,split,group) or justify `NOT_APPLICABLE.md` |
| Gate fails "PROTOCOL.md changed after freeze" | protocol edited above `## Deviations` | `git checkout` the frozen text; record changes under Deviations |
| Gate fails "sha256 mismatch" | a raw data file changed | restore it from the source; derived data belongs in `data/processed/` |
| `check numbers` flags software versions or seeds | they were written as plain text | put them in `code spans` |
| `init` refuses: "refusing to overwrite" | target folder already has files with the same names | init into a new folder, then move your existing material in |
| Agent ignores the skills | skills folder not where the agent looks | Claude Code: `.claude/skills`; Antigravity: `.agents/skills` or `.agent/skills`; restart the agent |
| MCP server fails to start | tool not installed | `./install.sh --with-tools`, then restart the agent |

## 8. Updating

```bash
cd q1-research-os && git pull && ./install.sh
```

Existing projects keep their copy of the constitution, skills and domain pack (so a running study is
never changed under your feet). To adopt a newer skill version in a project, copy the skill folder
over manually and note it in `ledgers/DECISION_LOG.csv`.
