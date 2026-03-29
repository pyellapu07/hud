# Personal OS Widget

A compact Windows desktop widget that lives pinned to your desktop background — never on top of your apps, always visible on your home screen.

Built with Python + CustomTkinter.

---

## Features

| Tab | What it does |
|-----|-------------|
| **Tasks** | Add tasks with sub-steps, priority, and timed reminders (toast notifications) |
| **Buy** | Quick-capture buy list with Urgent / Groceries / Someday categories |
| **Jobs** | Daily application counter, streak heatmap, Gmail sync across multiple accounts |
| **Assets** | Net worth tracker — gold (live price), stocks, MF, crypto, FD, cash |
| **Calendar** | Full Google Calendar month grid with event Join buttons |

---

## Requirements

- Windows 10 / 11
- Python 3.10 or newer — [python.org](https://python.org)

---

## Quick Start

```
1. Clone or download this repo
2. Place your credentials.json in the personal_os/ folder  ← see section below
3. Double-click  personal_os/setup.bat
4. On first launch you'll see a setup screen — enter your name and Gmail accounts
```

`setup.bat` installs all dependencies and creates a Windows Task Scheduler entry so the widget launches automatically 15 seconds after every login.

To launch manually at any time: double-click **open.bat**

---

## Google Credentials Setup (5 minutes)

The widget connects to Google Calendar and Gmail using **your own** Google Cloud project. This means your data never passes through anyone else's server.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project → New Project** — name it anything (e.g. "Personal OS")
3. Select your new project

### Step 2 — Enable APIs

In the left sidebar go to **APIs & Services → Enable APIs and Services**, then enable:
- **Google Calendar API**
- **Gmail API**

### Step 3 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON file
5. Rename it to `credentials.json`
6. Place it in the `personal_os/` folder

### Step 4 — Add yourself as a test user

Until you publish the app for Google review, only listed test users can sign in:

1. Go to **APIs & Services → OAuth consent screen**
2. Scroll to **Test users → Add users**
3. Add every Google account you want to connect

> **Sharing with others?**
> Each person who uses this widget should create their own `credentials.json` from their own Google Cloud project — the setup takes about 5 minutes and keeps everyone's data completely separate. There is no shared backend.

---

## Files

```
personal_os/
├── widget.py              Main application
├── setup.bat              First-time installer (run this)
├── open.bat               Manual launcher
├── requirements.txt       Python dependencies
├── settings.example.json  Settings schema reference
├── credentials.json       ← YOU provide this (gitignored)
└── README.md
```

**Gitignored** (created at runtime, never committed):
`credentials.json`, `*_token.json`, `settings.json`, `tasks.json`, `buylist.json`, `jobs.json`, `assets.json`, `widget_pos.json`, `gmail_processed.json`

---

## Privacy

All data is stored locally in JSON files on your machine. Nothing is sent to any external server except:
- Google Calendar API (to read your events)
- Gmail API (to read job-related email subjects)
- Yahoo Finance API (to fetch live gold price)
- open.er-api.com (USD → INR exchange rate)

---

## Uninstall

To remove the auto-launch task:
```
schtasks /Delete /TN "PersonalOSWidget" /F
```

Then delete the `personal_os/` folder.
