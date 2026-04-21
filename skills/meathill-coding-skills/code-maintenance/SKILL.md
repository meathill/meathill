---
name: code-maintenance
description: >
  Skill for periodic codebase maintenance and hygiene. Use this skill whenever the user asks to
  "maintain", "clean up", "refactor", "tidy up", or "improve code quality" of the codebase.
  Also trigger when the user mentions: cleaning docs, adding tests, extracting shared code,
  splitting large files, replacing hand-rolled utilities with libraries, or consolidating
  duplicate code. Even partial mentions like "too many docs", "file is too big", "we should
  use a library for this", or "DRY up" should trigger this skill.
---

# Code Maintenance Skill

This skill guides you through six maintenance tasks for any codebase.
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
   find src -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" | xargs wc -l | sort -rn | head -20
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
| Utility functions | `lodash-es` | debounce, throttle, deepClone, merge, etc. |
| Date/time | `dayjs` | Don't hand-roll date formatting/timezone logic |
| State management | `zustand` | Prefer over manual context/ref state |
| CSS utilities | `clsx` + `tailwind-merge` | For conditional class composition |

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

## Running the Maintenance

When the user triggers this skill:

1. Ask which tasks they want to run, or if they want all six.
2. For each selected task, show a brief summary of what you found and your proposed changes
   before making them.
3. After each task, run the project's test suite and type checking to verify nothing broke.
4. At the end, summarize all changes made.

If running all tasks, go in order 1→6 since later tasks may depend on earlier cleanup.
