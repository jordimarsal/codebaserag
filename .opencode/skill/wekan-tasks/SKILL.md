---
name: wekan-tasks
description: Mirror harness workflow states on the project's Wekan kanban board — create a feature card, move it between state lists, comment progress. Use whenever a harness feature changes state and the wekan-tickets module is installed (harness/wekan.json present).
---

# wekan-tasks — Wekan ticket mirror for the harness SDD flow

The harness is the source of truth (`harness/feature_list.json`); Wekan is the
**visible trace**. Every workflow state transition is mirrored on the board: the
card IS the ticket. Wekan sync must NEVER block the SDD flow — on any failure,
log it in `harness/progress/current.md` and continue.

## Configuration and secrets

All connection data lives in `harness/wekan.json`:

- `url` — base URL of the self-hosted Wekan instance.
- `board_name` — board title (empty = project name from `harness/feature_list.json`).
- `list_map` — SDD state → list title. Default lists: `pending`, `spec_ready`,
  `in_progress`, `blocked`, `done`. Card position == feature status.
- `credentials_file` — path to a **gitignored** env file that must define:

  ```
  WEKAN_API_BEARER_TOKEN=...
  WEKAN_API_USER_ID=...
  ```

- `enabled` — kill switch. If `false`, or if `harness/wekan.json` is absent, skip
  every Wekan action silently.

Read secrets via bash `sed`, never with file-read tools (`.env` files are usually
read-denied). The token may end with `=` — `cut -d= -f2` truncates it:

```bash
CFG_URL="$(sed -n 's/^"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' harness/wekan.json)"
CRED="$(sed -n 's/^"credentials_file"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' harness/wekan.json)"
TOK="$(sed -n 's/^WEKAN_API_BEARER_TOKEN=//p' "$CRED")"
USR="$(sed -n 's/^WEKAN_API_USER_ID=//p' "$CRED")"
AUTH=(-H "Authorization: Bearer $TOK" -H "X-User-Id: $USR")
# Self-signed certs → always: curl -sk
```

If the server is unreachable or credentials fail: log once in
`harness/progress/current.md`, stop syncing, keep working.

## Resolve the board (once per session)

1. **Board lookup:** `GET /api/boards` only lists PUBLIC boards. Try it first;
   if the board is private, fall back to a mongo lookup (only when mongo
   credentials are available in the credentials file or the operator provides
   them — never guess):

   ```bash
   curl -sk "${AUTH[@]}" "$CFG_URL/api/boards"   # public boards, [{_id,title},...]
   # fallback (needs mongo creds):
   docker exec wekan-mongo mongosh --quiet \
     "mongodb://$MUSR:$MPW@localhost:27017/test?authSource=admin" \
     --eval 'db.boards.findOne({title:"<project>"},{_id:1,title:1})'
   ```

2. **Create if missing** (idempotent; the creator becomes board admin) and ensure
   the five `list_map` lists exist:

   ```bash
   BOARD=$(curl -sk "${AUTH[@]}" -X POST "$CFG_URL/api/boards" \
     -H "Content-Type: application/json" -d '{"title":"<project>"}' \
     | python3 -c "import json,sys; print(json.load(sys.stdin)['_id'])")
   # POST returns {_id, defaultSwimlaneId}; keep the swimlane id
   SWIMLANE=$(curl -sk "${AUTH[@]}" "$CFG_URL/api/boards/$BOARD" | python3 -c "import json,sys; print(json.load(sys.stdin)['defaultSwimlaneId'])")
   for L in pending spec_ready in_progress blocked done; do
     curl -sk "${AUTH[@]}" -X POST "$CFG_URL/api/boards/$BOARD/lists" \
       -H "Content-Type: application/json" -d "{\"title\":\"$L\"}"
   done
   ```

3. **Resolve list ids** once and reuse them:

   ```bash
   curl -sk "${AUTH[@]}" "$CFG_URL/api/boards/$BOARD/lists"   # [{_id,title},...]
   ```

## Role traces (who does what, when)

| Event | Agent | Wekan action |
|---|---|---|
| Feature added / first seen at session start | leader | Create card (or reuse the card id from the feature's `"wekan_card"`); fill title + description (title, description, acceptance criteria) |
| Spec written | spec-author | Move card → `spec_ready`; comment with the spec path |
| Human approves spec | leader | Move card → `in_progress` |
| Implementation starts | implementer | Set `startAt` to today |
| Task progresses / blocked | implementer | Comment with progress; if blocked move → `blocked` (and back when unblocked) |
| Review verdict | reviewer | Comment with verdict; on approval move → `done` and set `endAt` to today |
| Rework requested | reviewer | Move card back → `in_progress`; comment with findings |

The leader records the created card id in the feature object:
`"wekan_card": "<cardId>"` in `harness/feature_list.json` — agents then never
re-search the board for the card.

## Operations

```bash
# Create a card — swimlaneId is REQUIRED (500 without it)
curl -sk "${AUTH[@]}" -X POST "$CFG_URL/api/boards/$BOARD/lists/$LIST_PENDING/cards" \
  -H "Content-Type: application/json" \
  -d '{"title":"<feature title>","description":"<desc + acceptance>","authorId":"'$USR'","swimlaneId":"'$SWIMLANE'"}'
# → {"_id":"<cardId>"}

# Move a card to another list (= state transition)
curl -sk "${AUTH[@]}" -X PUT "$CFG_URL/api/boards/$BOARD/lists/$OLD_LIST/cards/$CARD" \
  -H "Content-Type: application/json" -d '{"listId":"'$NEW_LIST'"}'

# Comment
curl -sk "${AUTH[@]}" -X POST "$CFG_URL/api/boards/$BOARD/cards/$CARD/comments" \
  -H "Content-Type: application/json" -d '{"comment":"spec_ready — see harness/specs/<name>/"}'

# Set startAt / endAt / dueAt (ISO 8601; date-only saves as T00:00:00Z)
curl -sk "${AUTH[@]}" -X PUT "$CFG_URL/api/boards/$BOARD/lists/$LIST/cards/$CARD" \
  -H "Content-Type: application/json" -d '{"startAt":"2026-09-07","endAt":"2026-09-08"}'
```

## Common errors

| Symptom | Cause and fix |
|---|---|
| 401/403 listing `/api/boards` | That route only returns PUBLIC boards; use the mongo fallback for private boards. |
| 401 Unauthorized | Token truncated (ends with `=`) or missing `X-User-Id`. Re-extract with `sed`; always send both headers. |
| 500 "Swimlane ID is required" | Add `swimlaneId` when creating the card. |
| 405 Method Not Allowed | Wrong route/method, or the token was cut. |
| Empty board lookup | Board does not exist yet → create it (see above). |

## Never do

- Never put secrets in `harness/wekan.json` or commit the credentials file.
- Never use `POST /users/login` to obtain a token (fails for API users).
- Never block the SDD flow on Wekan errors — log and continue.
- Never invent dates: leave `dueAt`/`startAt`/`endAt` empty unless specified.
