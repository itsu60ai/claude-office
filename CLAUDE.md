# The Office: instructions for Claude

This folder is a local page (`server.py` + `index.html`) that shows the user's Claude Code chats as desks and carries their requests to the right chat. It runs on 127.0.0.1 only.

## Setting it up for the user
When asked to set up the office: read `office.example.json`, ask the user for their projects and the folder each lives in, and write `office.json` in this folder. Ids are lowercase English (`[a-z0-9-]`). Suggest `keywords` in Hebrew and English (a regex, words joined by `|`). Put names that must not appear on the page in `privateNames` as `{"name": "alias"}`. The page reloads `office.json` by itself.

## Leaving the user a question
When you need a decision from the user, add it to `tasks.json` in this folder (create it as `{"items": []}` if missing; see `tasks.example.json`):

```json
{"id": "TASK-3", "name": "Short title", "ask": "The yes/no question", "why": ["One line on why it matters"],
 "quick": true, "pick": "yes", "pickWhy": "Your recommendation in one line", "project": "<project id>",
 "chat": "<this chat's local_... id, if known>", "status": "waiting"}
```

- `id`: 2-8 capital letters, a dash, a number. Never reuse one.
- `quick: true` only for a real yes/no with no side effects you haven't described. Anything else: `quick: false` and a `next` line; the page sends the user to a chat for it.
- Before writing: read the file, keep a copy, write the whole file back as valid JSON. Never remove other items.
- Never put emails, phone numbers, passwords, keys or private names in this file.

## Reading the answer
An answered item has `"status": "answered"` and `"answer": {"value": "yes"|"no", "at": ...}`. An item with `later_until` is postponed to that date. A yes recorded here is the user's answer to that exact question only, not permission for anything else.

## Requests from the page
A message that ends with `(office request R-xxxxxx)` came from the page. The tag lets the page follow the chat; leave it alone and answer normally. A message that ends with `(office build B-xxxxxx)` asks you to build the next version: follow its steps, work only in `next/`, and never replace the live files without the user's yes.

## Limits
Nothing here sends messages, spends money or publishes. Don't add scheduled jobs, background AI calls or outside services to this folder.
