---
name: code-maintenance
description: >
  Skill for periodic codebase maintenance and hygiene. Use this skill whenever the user asks to
  "maintain", "clean up", "refactor", "tidy up", or "improve code quality" of the codebase.
  Also trigger when the user mentions: cleaning docs, adding tests, extracting shared code,
  splitting large files, replacing hand-rolled utilities with libraries, or consolidating
  duplicate code. Even partial mentions like "too many docs", "file is too big", "we should
  use a library for this", "DRY up", "TODO comments piling up", "address FIXMEs", or
  "clean up tech debt markers" should trigger this skill.
---

# Code Maintenance Skill

This skill guides you through seven maintenance tasks for any codebase.
Run them in order, or let the user pick specific ones. Each task is independent — skip any
that are not needed.

## Prerequisites — Read Before You Touch Anything

Before starting **any** task, read the project's existing docs and scan the project structure
(`ls`, `package.json`, config files) so you understand the current state. Pay **special
attention** to these three — they contain hard-won lessons and constraints that directly
affect maintenance work:

- **DEV_NOTE.md** (or equivalent architecture doc) — Architecture decisions, framework quirks,
  known pitfalls, and workarounds. This prevents you from re-introducing bugs that have
  already been solved or contradicting established patterns.
- **TESTING.md** (or equivalent test guide) — How tests are organized, which frameworks are
  used, naming conventions, and any special setup (mocks, fixtures, environment). Follow
  these conventions exactly when writing new tests.
- **DEPLOYMENT.md** (or equivalent ops doc) — Target environments, build constraints, and
  runtime limitations. Changes that work locally but violate deployment constraints will
  break production.

Skipping this step leads to changes that conflict with established decisions or break in
production. Always review these docs first, even if you think you already know the codebase.

---

## Task 1: Clean Up Documentation

**Goal:** Remove redundant, stale, or low-value docs. Keep the doc tree lean and navigable.

**Steps:**

1. List all markdown files in the repo root and subdirectories (excluding node_modules, dist).
2. For each doc, assess:
   - Is it a duplicate of another doc? (merge or delete the weaker one)
   - Is it a temporary note that has been superseded by code or another doc? (delete)
   - Is it outdated — references removed features, old APIs, or wrong paths? (update or delete)
   - Is it too short to justify its own file? (fold into a parent doc)
3. Consolidate related docs where it makes sense (e.g., merge scattered deployment notes
   into a single DEPLOYMENT doc).
4. After cleanup, ensure every remaining doc has a clear purpose stated in its first paragraph.

**What NOT to do:**
- Don't delete or flag as duplicates the AI agent instruction files — they serve different
  AI tools and must all be kept separately:
  - `AGENTS.md` (Claude Code)
  - `GEMINI.md` (Gemini)
  - `.github/copilot-instructions.md` (GitHub Copilot)
- Don't delete any `.claude/` config files.
- Don't delete migration files (SQL, Drizzle, Prisma, etc.).

---

## Task 2: Crystallize Knowledge into Long-term Docs

**Goal:** Capture recent development learnings — framework patterns, infrastructure decisions,
debugging insights — into permanent documentation, so they survive beyond chat history.

**Steps:**

1. Review recent git history (`git log --oneline -30`) to identify new patterns, architectural
   decisions, or infrastructure changes that aren't yet documented.
2. Check if any architecture/decision docs (DEV_NOTE.md or similar) cover the current state
   accurately. Update sections that are stale or incomplete.
3. Look for knowledge that only lives in code comments or commit messages — things like:
   - Why a particular caching/storage strategy was chosen
   - Framework quirks and workarounds discovered during development
   - Database migration patterns and gotchas
   - Build & distribution pipeline details
   - Internationalization / locale handling decisions
4. Add these as concise sections in appropriate long-term docs. Use the project's existing
   doc language and style.
5. If a topic is large enough to warrant its own file, create it — but prefer extending
   existing docs to reduce file count.

**Principle:** Write for a new team member joining in 3 months. They should be able to
understand *why* things are the way they are, not just *what* they are.

---

## Task 3: Expand Test Coverage

**Goal:** Improve test coverage systematically.

First, detect the project's test framework (Vitest, Jest, Mocha, pytest, etc.) and existing
test structure.

**Coverage targets (in priority order):**

1. **Utility functions & pure logic** — 100% coverage target.
   - Algorithm modules, shared helpers, pure data transformations
   - Build scripts and CLI utilities

2. **API routes / endpoints** — 100% coverage target.
   - Every endpoint should have request/response tests
   - Test validation, error responses, edge cases (empty input, invalid params, etc.)
   - Mock external dependencies at the boundary

3. **UI components** — Aim for major component coverage.
   - Test rendering, user interactions, state transitions
   - Use the project's DOM testing setup (jsdom, happy-dom, etc.)

4. **E2E smoke tests** — Light coverage for critical user paths.
   - The most important happy-path flows
   - Initialization and configuration loading

**How to write tests:**
- Follow existing test patterns and directory structure
- Use descriptive test names that explain the scenario, not the implementation
- Keep tests focused — one behavior per test

**What NOT to do:**
- Don't test framework internals
- Don't write tests that duplicate what the type system already checks
- Don't mock so deeply that the test only verifies mock wiring

---

## Task 4: Refactor Large Files

**Goal:** No single source file should be so large that it's hard to navigate or reason about.

**Threshold:** Files over ~300 lines deserve a look. Over ~500 lines, split them.

**Steps:**

1. Find large files:
   ```bash
   find . \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) \
     -type f -not -path "*/node_modules/*" -not -path "*/dist/*" -print0 \
     | xargs -0 wc -l | sort -rn | head -20
   ```
2. For each large file, identify natural seams:
   - Separate types/interfaces into a dedicated types file if they're substantial
   - Extract logically independent sections into their own modules
   - Group related functions that serve one domain into a focused file
3. After splitting, verify:
   - All imports resolve correctly
   - Tests still pass
   - Type checking passes

**Splitting strategies:**
- Route handlers: one file per route group
- Services: one file per domain concern
- Components: one component per file
- Constants/config: separate from logic

**What NOT to do:**
- Don't split files just because they're slightly over the threshold if they're cohesive.
- Don't create too many tiny files — a 50-line file that imports 5 siblings is worse than
  a 300-line file that stands alone.

---

## Task 5: Extract Shared Code (DRY)

**Goal:** If the same logic appears 3+ times, extract it into a shared module.

**Steps:**

1. Search for duplicated patterns:
   - Similar fetch/request wrappers
   - Repeated validation logic
   - Copy-pasted error handling
   - Duplicate type definitions across modules
   - Repeated utility functions (type guards, normalization, formatting)
2. Decide where shared code should live:
   - Cross-cutting utilities → a shared/common directory
   - Module-specific helpers → within that module's directory
3. Extract and replace all call sites.
4. Add tests for newly extracted functions.
5. Run full test suite and type checking to verify.

**What NOT to do:**
- Don't extract code that's only used twice — the threshold is 3 times.
- Don't create a "god utils" file. Keep utils focused by domain.
- Don't over-abstract — if two pieces of code look similar but serve different purposes
  and might evolve independently, leave them separate.

---

## Task 6: Replace Hand-rolled Code with Libraries

**Goal:** Use mature, well-maintained libraries instead of reinventing the wheel.
Less custom code means fewer bugs and easier onboarding.

**Preferred libraries:**

| Category | Preferred | Notes |
|---|---|---|
| Charts | `echarts` | Don't hand-write SVG charts |
| Icons | `@phosphor-icons/react` (first choice), `lucide-react` (second), or pure CSS | Don't inline SVG icons |
| Utility functions | `es-toolkit` (first choice), `lodash-es` (legacy only) | debounce, throttle, deepClone, merge, etc. `es-toolkit` is a smaller, faster, TS-native replacement |
| Date/time | `date-fns` (first choice), `dayjs` (lightweight alternative) | Don't hand-roll date formatting/timezone logic |
| State management | `zustand` | Prefer over manual context/ref state |
| CSS utilities | `clsx` + `tailwind-merge`, plus `cva` for type-safe variants | For conditional class composition and component variant systems |

**Steps:**

1. Search for hand-rolled implementations:
   - Custom SVG icons → replace with icon library
   - Manual chart rendering with raw SVG/Canvas → use chart library
   - Custom debounce/throttle/deepClone/merge → use utility library
   - Custom date formatting/timezone math → use date library
   - Manual global state with context/refs → consider state management library
2. For each replacement:
   - Install the library if not present
   - Replace the custom code with the library equivalent
   - Remove the old custom implementation
   - Verify with tests and type checking
3. For embeddable widgets or bundles that need to stay small:
   - Be cautious about bundle size
   - Prefer lightweight alternatives or tree-shakeable imports
   - Inline SVG or CSS-only solutions may be acceptable for icons

**What NOT to do:**
- Don't add a library just to use one function from it — weigh the dependency cost.
- Don't replace well-tested custom code that has no bugs and works perfectly,
  unless the library version is significantly cleaner.
- Don't add heavy libraries to lightweight/embeddable bundles.

---

## Task 7: Resolve TODO/FIXME Comments

**Goal:** Don't carry tech debt markers into the next maintenance round.
By the end of this task, every TODO/FIXME left in the code should be one you
*chose* to leave — not one nobody dared touch.

This task runs **last on purpose**: Tasks 3–6 frequently make older TODOs
obsolete (a refactor closes a "TODO: split this", a library swap closes a
"FIXME: handle timezones"), so triaging at the end avoids wasted work.

**Markers to scan:** `TODO`, `FIXME`, `HACK`, `XXX`, `BUG`. These are the
universal ones across languages and comment styles. Use word boundaries to
avoid matching inside identifiers like `todoList`.

**Steps:**

1. Find all markers (excluding generated and vendored code):
   ```bash
   rg -n --word-regexp '(TODO|FIXME|HACK|XXX|BUG)' \
     -g '!node_modules' -g '!dist' -g '!build' -g '!.next' \
     -g '!*.lock' -g '!*.min.*'
   ```
   Fall back to `grep -rEn '\b(TODO|FIXME|HACK|XXX|BUG)\b' …` if `rg` is
   unavailable.

2. For each match, read the surrounding code (5–10 lines above and below) so
   you understand what the comment was actually warning about, then pick **one
   of three outcomes**:

   - **Resolve now** — Do the work in this maintenance round. Most TODOs that
     survive Tasks 3–6 are small enough to close in minutes. Delete the
     comment after the fix.
   - **Convert to a tracked issue** — If it's a real backlog item (a known
     bug, a future feature, a constraint waiting on something external),
     file it on the project's issue tracker (GitHub Issues / Linear / etc.)
     and remove the inline comment. Optionally replace it with
     `// see issue #123` if the location is non-obvious from the issue body.
     Confirm with the user before opening external issues.
   - **Delete** — If the surrounding code has changed and the concern no
     longer applies, just delete the comment. State the reason in the commit
     body so the decision is auditable.

3. Re-run the scan and confirm only intentional, time-bounded markers remain.
   A clean report at the end of the task is the success signal.

**What NOT to do:**

- Don't blindly delete TODOs without reading the surrounding code — the
  comment may be the only documentation of a subtle invariant.
- Don't add new TODO/FIXME comments during this maintenance round. If you
  hit something you can't fix, either open an issue and link it, or note it
  in the round summary — don't leave a fresh orphan marker.
- Don't touch TODOs inside:
  - Third-party code (`node_modules`, `vendor`, `dist`, `build`).
  - Test fixtures, sample data, or copy-pasted reference snippets — those
    are inputs, not real markers.
  - Translated strings (i18n catalogs) that legitimately contain the word.
- Don't auto-create issues in bulk without confirming with the user — a
  flood of low-quality issues is worse than the original TODOs.

---

## Running the Maintenance

When the user triggers this skill:

1. Ask which tasks they want to run, or if they want all seven.
2. For each selected task, show a brief summary of what you found and your proposed changes
   before making them.
3. After each task, run the project's test suite and type checking to verify nothing broke.
4. At the end, summarize all changes made.

If running all tasks, go in order 1→7 since later tasks may depend on earlier cleanup.

## Commit Strategy: One Maintenance Round = One Commit

**A single maintenance run should land as a single squashed commit on the target branch.**

While *executing*, you can use stepwise commits as checkpoints to make verification and
rollback granular (e.g., one commit per task, or one per cross-package step). But before
declaring the round complete, squash them all into one commit with a structured body that
summarizes each section of work.

**Why:**
- Maintenance commits are noise in `git log` / `git blame` — squashing keeps history readable.
- A single maintenance commit is easy to revert wholesale if something turns out wrong later.
- The structured body (sectioned by task: docs / DRY / tests / etc.) preserves the "what
  changed and why" without bloating commit count.

**How:**
- After verification passes (tests + typecheck + build smoke + lint clean), run
  `git reset --soft <base-branch>` to collapse the staged checkpoint commits.
- Create one commit with a body that has a section per task category, listing concrete
  changes (files / decisions / rationale).
- Mention verification results at the bottom (e.g., "32 shared tests pass, 51 web tests
  pass, app typecheck pass, web build pass, lint clean").

**Exceptions** — keep separate commits when:
- The user is reviewing intermediate state and wants the granular history.
- The maintenance round spans multiple PRs or branches.
- One sub-task has its own non-trivial review need (e.g., a large refactor that benefits
  from focused review on its own).

When in doubt, squash. The default is one commit per round.
