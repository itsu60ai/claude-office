# המשרד / The Office

**[עברית](#עברית) · [English](#english)**

---

## עברית

כשעובדים עם כמה שיחות של Claude Code במקביל, הן מתפזרות. אחת כותבת קוד, אחת מחכה שתאשר משהו, אחת סיימה לפני שעה ואף אחד לא שם לב. המשרד הוא דף אחד שמראה את כולן ביחד, ונותן לך לכתוב בקשה בלי לחפש לאיזו שיחה היא שייכת.

### מה רואים בדף

- **שולחן לכל שיחה.** כל שיחה שעבדה ב-24 השעות האחרונות מקבלת שולחן עם דמות קטנה. רואים מה היא עושה עכשיו (קוראת קבצים, מריצה פקודה, עובדת בדפדפן), אם סיימה ומחכה לך, או אם עצרה באמצע, למשל כי היא מחכה לאישור.
- **"תשאל את המשרד".** כותבים מה צריך, בעברית רגילה. הדף מציע לאיזה פרויקט זה שייך, ואפשר לשנות. לוחצים, ונפתחת שיחה ב-Claude עם הטקסט כבר כתוב. אתה לוחץ "שלח". מכאן המשרד עוקב: אם השיחה עובדת, אם שאלה אותך משהו, ומה היא ענתה.
- **תמונות.** אפשר לצרף עד 4 תמונות לבקשה (צילום מסך, סקיצה). הן נשמרות בתיקייה של המשרד, וקלוד מקבל את הנתיב שלהן.
- **שאלות שמחכות לך.** כשקלוד צריך ממך החלטה, הוא יכול להשאיר אותה בקובץ `tasks.json`, והיא מופיעה בדף ככרטיס. שאלה פשוטה עונים בלחיצה: כן, לא או אחר כך. שאלה שצריכה שיחה פותחת את השיחה.
- **רעיונות לגרסה הבאה.** רואה משהו שחסר בדף? כותבים רעיון. כשמצטברים כמה, לוחצים "בנה", וקלוד בונה גרסה חדשה של המשרד על עותק נפרד. הדף שאתה עובד איתו לא משתנה עד שאתה מאשר.
- **עברית ואנגלית.** מתג בפינה. הדף זוכר את הבחירה.

הדף מתעדכן לבד כל 10 שניות, אין צורך לרענן.

### מה הוא לא עושה

- **לא שולח כלום בשמך.** כל בקשה נפתחת אצלך בשיחה, ואתה לוחץ "שלח". בלי לחיצה שלך לא קורה כלום.
- **לא יוצא מהמחשב.** הדף רץ רק אצלך (כתובת 127.0.0.1). אין חשבון, אין שרת בחוץ, אין מפתח API ואין עלות.
- **לא מפעיל AI ברקע.** הוא רק קורא את הקבצים ש-Claude כבר כותב על המחשב שלך.
- **לא מציג פרטים פרטיים.** מיילים, טלפונים, סיסמאות ומפתחות לא מופיעים בדף, גם אם הם הופיעו בשיחה. שמות שתבחר להסתיר מוחלפים בכינוי.

### התקנה, פעם אחת

צריך: אפליקציית Claude למחשב עם Claude Code, ו-Python 3.8 ומעלה ([הורדה](https://www.python.org/downloads/)).

1. מורידים את התיקייה (Code ← Download ZIP ב-GitHub) ופותחים אותה איפה שנוח.
2. **Windows:** לחיצה כפולה על `start.bat`.
   **Mac:** לחיצה ימנית על `start.command` ← Open. בפעם הראשונה Mac ישאל אם לפתוח קובץ ממקור לא מוכר, עונים Open.
3. הדפדפן נפתח על המשרד. החלון השחור שנפתח הוא המנוע של הדף: משאירים אותו פתוח, וסוגרים אותו כשרוצים לכבות.

בשלב הזה המשרד כבר עובד, עם פרויקט אחד כללי.

### להתאים אותו לפרויקטים שלך

פותחים שיחה חדשה ב-Claude Code, בתיקייה של המשרד, ומדביקים:

```
תסדר לי את המשרד. תקרא את README.md ואת office.example.json שבתיקייה הזו, ותיצור office.json עם הפרויקטים שלי.
תשאל אותי מה הפרויקטים ובאיזו תיקייה כל אחד יושב, ותציע לכל אחד מילות מפתח בעברית ובאנגלית כדי שהמשרד ינחש נכון לאן בקשה שייכת.
אם יש שמות של אנשים שלא אמורים להופיע בדף, תוסיף אותם ל-privateNames.
```

הדף קולט את השינוי לבד, בלי להפעיל מחדש.

<details>
<summary>מה יש ב-office.json, למי שרוצה לערוך לבד</summary>

| שדה | מה הוא קובע |
|---|---|
| `officeName` | השם שמופיע בראש הדף, בעברית ובאנגלית |
| `defaultLang` | `he` או `en`, השפה בפתיחה הראשונה |
| `defaultProject` | הפרויקט שנבחר כשהדף לא מצליח לנחש |
| `newProjectsFolder` | איפה קלוד יבדוק, ואם צריך יפתח, פרויקט חדש |
| `projects` | רשימת הפרויקטים. לכל אחד: `id` (אותיות קטנות באנגלית), `name`, `nameEn`, `folder`, `color`, `keywords` |
| `privateNames` | שמות שיוחלפו בכינוי, למשל `{"דנה כהן": "לקוחה"}` |

`keywords` הוא ביטוי חיפוש: מילים מופרדות ב-`|`, למשל `חנות|מוצרים|shop`. השיחה משויכת לפרויקט לפי התיקייה שבה היא נפתחה.
</details>

### לתת לקלוד להשאיר לך שאלות

בקובץ `CLAUDE.md` שבתיקייה יש הוראות לקלוד: איך להוסיף שאלה ל-`tasks.json` ואיך לקרוא את התשובה שלך. כדי שכל השיחות שלך יכירו את זה, אפשר לבקש מקלוד: "תוסיף להוראות הכלליות שלי את הקטע מ-CLAUDE.md של המשרד". דוגמה למבנה הקובץ יש ב-`tasks.example.json`. בלי `tasks.json` הכרטיס פשוט לא מופיע.

### כשמשהו לא עובד

- **הדף ריק, אין שולחנות.** המשרד מציג שיחות מ-24 השעות האחרונות. פותחים שיחה ב-Claude Code, כותבים בה משהו, ומחכים כמה שניות.
- **"Python was not found".** מתקינים Python מהקישור למעלה. ב-Windows מסמנים בהתקנה את "Add Python to PATH".
- **הפורט תפוס.** מריצים עם פורט אחר: `python server.py 8780`, ופותחים `http://127.0.0.1:8780`.
- **Mac.** את מיקום הקבצים של אפליקציית Claude ב-Mac הנחנו לפי המבנה המקובל, ועוד לא בדקנו על מחשב Mac אמיתי. אם השולחנות לא מופיעים, ספרו לנו.

### מה יש בתיקייה

| קובץ | מה הוא |
|---|---|
| `index.html` | הדף עצמו |
| `server.py` | המנוע: קורא את השיחות ומחזיר לדף מה קורה. רק ספריות שמגיעות עם Python |
| `start.bat` / `start.command` | הפעלה בלחיצה, ל-Windows ול-Mac |
| `office.example.json` | הגדרות לדוגמה. ההגדרות שלך נשמרות ב-`office.json` |
| `tasks.example.json` | דוגמה לשאלות שמחכות לך |
| `CLAUDE.md` | הוראות לקלוד |
| `state/` | נוצרת לבד: היסטוריית הבקשות, התמונות וגיבויים. לא עולה ל-Git |

---

## English

Run a few Claude Code chats at once and they scatter. One is writing code, one is waiting for your OK, one finished an hour ago and nobody noticed. The Office is a single page that shows all of them together, and lets you ask for something without hunting for the right chat.

### What you see

- **A desk for every chat.** Each chat that worked in the last 24 hours gets a desk with a small character. You see what it's doing right now (reading files, running a command, working in the browser), whether it finished and it's your turn, or whether it stopped midway, for example because it's waiting for your approval.
- **Ask the office.** Write what you need in plain words. The page suggests which project it belongs to, and you can change it. Click, and a Claude chat opens with your text already typed. You press Send. From there the office follows it: is it working, did it ask you something, what did it answer.
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
Set up my office. Read README.md and office.example.json in this folder and create office.json with my projects.
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

`CLAUDE.md` in this folder tells Claude how to add a question to `tasks.json` and how to read your answer. To make every chat aware of it, ask Claude: "Add the section from the office's CLAUDE.md to my global instructions." There's a sample in `tasks.example.json`. Without a `tasks.json`, the card simply doesn't show.

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
| `CLAUDE.md` | Instructions for Claude |
| `state/` | Created on its own: request history, pictures and backups. Never committed |
