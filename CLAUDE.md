# The Office: instructions for Claude

This folder is a local page (`server.py` + `index.html`) that shows the user's Claude Code chats as desks and carries their requests to the right chat. It runs on 127.0.0.1 only.

## Setting it up for the user
When asked to set up the office: read `office.example.json`, ask the user for their projects and the folder each lives in, and write `office.json` in this folder. Ids are lowercase English (`[a-z0-9-]`). Suggest `keywords` in Hebrew and English (a regex, words joined by `|`). Put names that must not appear on the page in `privateNames` as `{"name": "alias"}`. The page reloads `office.json` by itself. When setup is done, tell the user one line: after a few days of use, press "💬 פידבק" ("Feedback") at the top of the office, answer three questions, and send the ready WhatsApp message.

## Leaving the user a question
When you need a decision from the user, add it to `tasks.json` in this folder (create it as `{"items": []}` if missing; see `tasks.example.json`):

```json
{"id": "TASK-3", "name": "Short title", "ask": "The yes/no question", "why": ["One line on why it matters"],
 "quick": true, "pick": "yes", "pickWhy": "Your recommendation in one line", "project": "<project id>",
 "chat": "<this chat's local_... id, if known>", "status": "waiting"}
```

- Write every card for someone who was not in the chat and opens it cold, days later:
  - `name` says what this is about: the thing and the part of it ("Business website: the top image"), not a bare label.
  - `ask` names the actual thing and the actual change ("Replace the image at the top of the home page with a photo of the shop?"), never "Go with the green one?".
  - First `why` line: what is happening now. Second: exactly what happens after a yes (and what stays the same).
  - Plain everyday words. No ids, file names, internal names or tech terms unless the user uses them.
  - Before saving, read the card alone. If a friend could not tell what they are agreeing to, rewrite it.
- `id`: 2-8 capital letters, a dash, a number. Never reuse one.
- Text fields (`name`, `ask`, each `why` line, `pickWhy`, `next`) can be a plain string or `{"he": "...", "en": "..."}`. The page shows the one that matches its language. Write the user's language at least; add both if they switch between them.
- Every thing the user has to do is one button. Instead of writing instructions ("open X, copy Y, paste in Z"), add `steps`: a list of up to 4 `{"do", "text", "label", "say"}`.
  - `do: "send"` opens the card's chat (or a new chat when there is none, or with `"to": "new"`) with `say` ready. `do: "copy"` puts `say` on the clipboard. `do: "fill"` puts `say` in the Ask box.
  - `text`: one short line on what the step does and how the user knows it worked. `label`: 2-4 words on the button.
  - Nothing is sent by a step. The user still presses Send in the chat.
- `quick: true` only for a real yes/no with no side effects you haven't described. Anything else: `quick: false` and a `next` line; the page sends the user to a chat for it.
- Before writing: read the file, keep a copy, write the whole file back as valid JSON. Never remove other items.
- Never put emails, phone numbers, passwords, keys or private names in this file.

## Reading the answer
An answered item has `"status": "answered"` and `"answer": {"value": "yes"|"no", "at": ...}`. An item with `later_until` is postponed to that date. A yes recorded here is the user's answer to that exact question only, not permission for anything else.

## Requests from the page
A message that ends with `(office request R-xxxxxx)` came from the page. The tag lets the page follow the chat; leave it alone and answer normally. A message that ends with `(office build B-xxxxxx)` asks you to build the next version: follow its steps, work only in `next/`, and never replace the live files without the user's yes.

## Feedback
When the user writes "פידבק" or "feedback", or asks how to send feedback on the office, collect it this way. Every answer comes back in the same shape, so the person who shared the office can compare them.

1. Ask these one at a time, in the user's language. Wait for each answer; "skip" is fine.
   1. What did you try to do first with the office, and did it work?
   2. Where did you get stuck, or what didn't you understand?
   3. What did you use the most?
   4. From 0 to 10, how disappointed would you be if the office disappeared tomorrow? Why?
   5. One thing you would change.
   6. Windows or Mac, and about how many days have you used it?
2. Take out project names, people's names, file paths, emails, phone numbers and anything else private. Keep the meaning.
3. Show the user one message in exactly this shape (Hebrew labels even if the answers are in English), with the version from the `VERSION` file:
   ```
   #פידבק-משרד
   גרסה: <VERSION>
   מחשב: <Windows/Mac>, <days> ימים
   ניסיתי קודם: <...>
   נתקעתי: <...>
   הכי שימושי: <...>
   אם ייעלם (0-10): <number>, כי <...>
   הייתי משנה: <...>
   ```
4. Tell the user to copy it and send it to the person who shared the office with them, in private or in the group where they got it. If they have a GitHub account, they can instead open https://github.com/itsu60ai/claude-office/issues/new?template=feedback.yml and paste the answers there.
5. Never send it yourself, and don't open the link for them.

## Limits
Nothing here sends messages, spends money or publishes. Don't add scheduled jobs, background AI calls or outside services to this folder.
