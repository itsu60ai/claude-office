# The Office

[עברית](README.md) · **English**

Run a few Claude Code chats at once and they scatter. One is writing code, one is waiting for your OK, one finished an hour ago and nobody noticed. The Office is a single page that shows all of them together, and lets you ask for something without hunting for the right chat.

### What you see

- **A desk for every chat.** Each chat that worked in the last 24 hours gets a desk with a small character. You see what it's doing right now (reading files, running a command, working in the browser), whether it finished and it's your turn, or whether it stopped midway, for example because it's waiting for your approval.
- **Ask Claude.** Write what you need in plain words. The page suggests which project it belongs to, and you can change it. Click, and a Claude chat opens with your text already typed. You press Send. From there the office follows it: is it working, did it ask you something, what did it answer.
- **Pictures.** Attach up to 4 images to a request (a screenshot, a sketch). They're saved in the office folder and Claude gets their path.
- **Questions waiting for you.** When Claude needs a decision, it can leave it in `tasks.json` and it shows up as a card. A simple question takes one tap: Yes, No or Later. One that needs a conversation opens the chat.
- **Ideas for the next version.** Missing something on the page? Write it down. Once you have a few, press Build and Claude builds a new version of the office on a separate copy. The page you're using doesn't change until you approve.
- **Hebrew and English.** A switch in the corner. The page remembers your choice.

The page updates itself every 10 seconds. No need to refresh.

### What it doesn't do

- **It never sends anything for you.** Every request opens in a chat and you press Send. Without your click, nothing happens.
- **It never leaves your computer.** The page runs only on your machine (127.0.0.1). No account, no outside server, no API key, no cost.
- **It doesn't run AI in the background.** It only reads the files Claude already writes on your computer.
- **It doesn't show private details.** Emails, phone numbers, passwords and keys never appear on the page, even if they came up in a chat. Names you choose to hide are replaced with an alias.

### Setup, once

You need: the Claude desktop app with Claude Code, and Python 3.8 or newer ([download](https://www.python.org/downloads/)).

1. Download the folder (Code → Download ZIP on GitHub) and unzip it wherever you like.
2. **Windows:** double-click `start.bat`.
   **Mac:** right-click `start.command` → Open. The first time, macOS asks whether to open a file from an unknown developer. Choose Open.
3. Your browser opens on the office. The black window that opened is what runs the page: keep it open, and close it when you want to stop.

The office already works at this point, with one general project.

### Make it yours

Open a new Claude Code chat in the office folder and paste:

```
Set up my office. Read README.en.md and office.example.json in this folder and create office.json with my projects.
Ask me what my projects are and which folder each one lives in, and suggest keywords for each one so the office guesses correctly where a request belongs.
If there are names of people that shouldn't appear on the page, add them to privateNames.
```

The page picks up the change on its own. No restart.

<details>
<summary>What's in office.json, if you'd rather edit it yourself</summary>

| Field | What it sets |
|---|---|
| `officeName` | The name at the top of the page, in Hebrew and English |
| `defaultLang` | `he` or `en`, the language on first open |
| `defaultProject` | The project picked when the page can't guess |
| `newProjectsFolder` | Where Claude checks for, and if needed creates, a new project |
| `projects` | Your projects. Each has `id` (lowercase English), `name`, `nameEn`, `folder`, `color`, `keywords` |
| `privateNames` | Names replaced with an alias, e.g. `{"Dana Cohen": "client"}` |

`keywords` is a search pattern: words separated by `|`, e.g. `shop|products|checkout`. A chat belongs to a project by the folder it was opened in.
</details>

### Let Claude leave you questions

`CLAUDE.md` in this folder tells Claude how to add a question to `tasks.json` and how to read your answer. To make every chat aware of it, ask Claude: "Add the section from the office's CLAUDE.md to my global instructions." There's a sample in `tasks.example.json`. A question can be written in Hebrew, English or both, and the page shows it in the language you picked. Without a `tasks.json`, the card simply doesn't show.

### Feedback

The office is new, and it gets better from what you tell us. After a few days of use, open a Claude chat in the office folder and write:

```
feedback
```

Claude asks six short questions, one at a time: what you tried, where you got stuck, what you used most, how much you'd miss it, what you'd change, and which computer you're on. It strips names and personal details and gives you a ready message that starts with `#פידבק-משרד`. You copy it and send it to whoever shared the office with you, in private or in the group. Claude never sends anything itself.

Have a GitHub account? You can also [fill in the form here](https://github.com/itsu60ai/claude-office/issues/new?template=feedback.yml).

### When something's off

- **The page is empty, no desks.** The office shows chats from the last 24 hours. Open a Claude Code chat, write something, and wait a few seconds.
- **"Python was not found".** Install Python from the link above. On Windows, tick "Add Python to PATH" during setup.
- **The port is taken.** Run it on another port: `python server.py 8780`, then open `http://127.0.0.1:8780`.
- **Mac.** We placed the Claude app's files on Mac where they usually live, but haven't tried it on a real Mac yet. If no desks show up, let us know.

### What's in the folder

| File | What it is |
|---|---|
| `index.html` | The page |
| `server.py` | The engine: reads your chats and tells the page what's happening. Python's built-in libraries only |
| `start.bat` / `start.command` | One-click start for Windows and Mac |
| `office.example.json` | Sample settings. Yours live in `office.json` |
| `tasks.example.json` | Sample questions waiting for you |
| `README.md` | This guide in Hebrew |
| `CLAUDE.md` | Instructions for Claude, including how to collect feedback |
| `VERSION` | The version number, added to every feedback message |
| `state/` | Created on its own: request history, pictures and backups. Never committed |
