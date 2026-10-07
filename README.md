# API-First Notes App

A Django REST Framework backend where **the API is the product**. Built as if a mobile
app depends on it: versioned URLs, one pagination envelope, one error shape, and tests
that pin the response shapes so they can't change by accident.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
python manage.py test              # 28 tests
```

## Endpoints (all under `/api/v1/`)

| Method | Path | What it does |
|---|---|---|
| POST | `auth/register/` | Create account, returns `{id, username, token}` |
| POST | `auth/token/` | Log in, returns `{token}` |
| GET / POST | `notes/` | List my notes (non-archived by default) / create |
| GET / PUT / PATCH / DELETE | `notes/{id}/` | Note detail |
| POST | `notes/{id}/archive/` · `unarchive/` | Flip archived state |
| GET / POST | `notes/{id}/shares/` | List / add shares (`shared_with` = username, `permission` = `view`\|`edit`) |
| DELETE | `notes/{id}/shares/{share_id}/` | Revoke a share |
| GET / PATCH | `shared-notes/`, `shared-notes/{id}/` | Notes shared with me; PATCH needs `edit` permission |
| GET / DELETE | `tags/`, `tags/{id}/` | My tags with `notes_count`; deleting detaches from notes |

Send `Authorization: Token <token>` on every request except register/login.

### Query parameters on `GET notes/`

| Param | Example | Notes |
|---|---|---|
| `search` | `?search=sprint` | Matches title, body, tag names |
| `tag` | `?tag=work,ideas` | Notes with **any** of these tags |
| `archived` | `?archived=true` | `false` (default), `true`, `all` |
| `updated_after` / `updated_before` | `?updated_after=2026-01-01T00:00:00Z` | ISO 8601 |
| `ordering` | `?ordering=-created_at` | `updated_at`, `created_at`, `title` (prefix `-` to reverse) |
| `page`, `page_size` | `?page=2&page_size=50` | Default 20, max 100 |

## Response contracts

**Note**
```json
{
  "id": 1,
  "title": "Sprint plan",
  "body": "ship the API",
  "tags": ["work"],
  "is_archived": false,
  "created_at": "2026-10-04T09:00:00Z",
  "updated_at": "2026-10-04T09:00:00Z"
}
```

**Every list** (notes, tags, shares, shared notes)
```json
{ "count": 27, "next": "http://.../?page=2", "previous": null, "results": [ ... ] }
```

**Every error**
```json
{ "error": { "code": "validation_error", "message": "One or more fields are invalid.",
             "details": { "title": ["This field may not be blank."] } } }
```
`details` is `null` for non-validation errors (`not_authenticated`, `permission_denied`, `not_found`, `throttled`, ...).

## Try it

```bash
curl -X POST localhost:8000/api/v1/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"a-Strong-pass-987"}'

TOKEN=<token from above>

curl -X POST localhost:8000/api/v1/notes/ \
  -H "Authorization: Token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Sprint plan","body":"ship the API","tags":["work"]}'

curl -H "Authorization: Token $TOKEN" 'localhost:8000/api/v1/notes/?tag=work&search=sprint'
```

## Design decisions worth knowing

- **Tags are a list of names**, not objects/ids. Mobile clients send `["work","ideas"]`; the
  server trims, lower-cases, de-dupes, and creates per-user `Tag` rows on the fly. Max 20 per note.
- **Sharing is per-note, per-user** with `view`/`edit`. Recipients use a separate
  `shared-notes/` resource so owner-only fields and actions never leak. Editors can change
  `title` and `body` only, never tags, archive state, or shares.
- **Archived is a state, not a delete.** Hidden from the default list, still fetchable by id.
- **No N+1**: `prefetch_related("tags")` on notes, `select_related("owner")` on shared notes;
  a test asserts the list query count stays flat as notes grow.
- **Changing a response shape is a breaking change.** Tests assert exact key sets. If you need
  a new shape, add `/api/v2/` instead of editing v1.
- Throttling is on (30/min anon, 300/min users); adjust in `config/settings.py`.

## Ideas to extend

- Public share links (random token, read-only)
- Soft delete / trash with restore
- Full-text search (Postgres `SearchVector`)
- Optimistic concurrency (`If-Match` with `updated_at`) to stop lost updates
- drf-spectacular for an OpenAPI schema
