# FILE: CONTRIBUTING.md
# ====================================
# Contribution Guide
# ====================================
#
# This guide explains how to contribute to the Smart AI Emergency Response System.
# Read this before opening a pull request.

---

## 🚀 Getting Started

```bash
# 1. Fork the repo and clone your fork
git clone https://github.com/YOUR-USERNAME/smart-ai-emergency-response-system.git
cd smart-ai-emergency-response-system

# 2. Create a feature branch — NEVER commit to main directly
git checkout -b feature/your-feature-name

# 3. Start the full stack
cd deployment && docker-compose up --build

# 4. Make your changes, then run tests
cd backend && pytest ../tests/test_backend.py -v
```

---

## 🌿 Branching Strategy

| Branch pattern | Purpose |
|---|---|
| `main` | Production-ready, protected. Requires PR to merge. |
| `feature/name` | New features (e.g. `feature/sms-alerts`) |
| `fix/name` | Bug fixes (e.g. `fix/websocket-reconnect`) |
| `docs/name` | Documentation only |
| `test/name` | Tests only |

**Rule:** Every change goes through a pull request — no direct pushes to `main`.

---

## ✍️ Commit Messages (Conventional Commits)

Format: `type(scope): short description`

```
feat(backend):     add SMS notifications via Twilio
fix(frontend):     correct WebSocket exponential backoff delay
test(ai):          add preprocessing tensor shape assertion
docs(api):         document green-corridor endpoint parameters
refactor(dashboard): extract SummaryCards into its own component
chore(deps):       upgrade FastAPI to 0.112
```

**Types:** `feat` `fix` `test` `docs` `refactor` `chore` `style` `perf`

Keep the description under 72 characters. Use the body for "why" if needed.

---

## 🐍 Python Code Standards (Backend + AI)

- **Style**: PEP 8 — use `black backend/` to auto-format
- **Type hints**: All function signatures must have type hints
  ```python
  def hash_password(plain: str) -> str:     # ✅
  def hash_password(plain):                  # ❌
  ```
- **Docstrings**: All public functions and classes need docstrings
- **Imports**: Standard library → third-party → internal (separated by blank lines)
- **Error handling**: Specific exceptions only — never bare `except:`

---

## ⚛️ JavaScript / React Code Standards (Frontend)

- **Components**: Functional components only — no class components
- **One file, one component**: `AlertCard.jsx` exports only `AlertCard`
- **Hooks**: Custom hooks in `src/hooks/`, prefixed with `use`
- **Prop validation**: Document expected props in JSDoc comments above the component
- **No inline styles for colours**: Use CSS variables (`var(--red)`) not hex strings in JSX
- **Cleanup**: Every `useEffect` that sets up a side effect must return a cleanup function

---

## 🧪 Testing Requirements

Every PR must pass:

```bash
# 1. Backend tests
cd backend && pytest ../tests/test_backend.py -v

# 2. Database integrity
psql -U postgres -d emergency_db -f tests/test_database.sql

# 3. Frontend manual checklist
# Work through tests/test_frontend.md and check all boxes

# 4. AI model tests (only if ai-module/ was changed)
pytest tests/test_ai_model.py -v
```

**Test coverage rule**: New backend endpoints must have at least one test in `test_backend.py`.

---

## 📝 Pull Request Checklist

Before submitting a PR, verify:

- [ ] `pytest tests/test_backend.py -v` — all tests pass
- [ ] `docker-compose up --build` works from a clean clone
- [ ] New API endpoints are documented in `docs/api_docs.md`
- [ ] Model changes are documented in `docs/project_report.md`
- [ ] No secrets committed (grep for passwords, API keys, tokens)
- [ ] `.env` file is NOT committed (it's in `.gitignore`)
- [ ] Frontend checklist `tests/test_frontend.md` completed
- [ ] PR description explains WHAT changed and WHY

---

## 🗂 Project Structure Reference

```
backend/app/
├── routes/    HTTP handlers — thin, call services, return responses
├── services/  Business logic — all complex operations live here
├── models/    SQLAlchemy DB models — define table structure
├── schemas/   Pydantic validators — define API request/response shape
├── database/  Engine, session factory, get_db dependency
└── config/    Settings from environment variables

frontend/src/
├── pages/      Route-level components — own data fetching via hooks
├── components/ Reusable presentational components — receive data via props
├── hooks/      Custom hooks — extract and share stateful logic
├── services/   API calls (api.js) and WebSocket client (socket.js)
└── utils/      Pure helper functions and constants
```

---

## 🐛 Reporting Bugs

Open a GitHub Issue with:
1. Steps to reproduce (numbered list)
2. Expected behaviour
3. Actual behaviour (include error messages)
4. Environment: OS, Python version, Node version, Docker version
5. Relevant logs: `docker-compose logs backend` output

---

## 💡 Suggesting Features

Open a GitHub Discussion before coding to:
- Avoid duplicate work
- Get early feedback on the approach
- Agree on the API contract before implementation

---

## 📄 Licence

By contributing, you agree that your contributions will be licensed under the same licence as this project.
