# LIPM - LinkedIn Personal Monitor

![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

**Automatically monitor LinkedIn company pages, generate AI-powered commentary, and repost with Telegram approval workflow.**

A professional automation tool that monitors LinkedIn company pages, generates AI-powered commentary using OpenAI, and manages reposting through a Telegram bot approval system with encrypted credential storage.

---

## 🚀 Features

### Core Functionality
- ✅ **Automatic LinkedIn Monitoring** - Polls company pages every 10 minutes
- ✅ **Instant Startup Processing** - Fetches recent posts immediately on startup
- ✅ **AI-Powered Commentary** - GPT-4o-mini generates professional insights and commentary
- ✅ **Telegram Approval Workflow** - Approve/Revise/Skip/Like posts from your phone
- ✅ **Smart Duplicate Prevention** - Never processes the same post twice
- ✅ **Session Persistence** - LinkedIn stays logged in across runs

### Security & Privacy
- 🔐 **AES-256-GCM Encryption** - All credentials encrypted at rest
- 🔑 **Passphrase Protected** - Master password controls access
- 🛡️ **Local Storage Only** - No cloud dependencies, all data stays on your machine
- 🔒 **Session Security** - Secure browser session management

### Advanced Features
- 📊 **Post Database** - JSON-based tracking with status management
- 🔄 **Automatic Retry** - Failed posts retry automatically
- 📈 **Statistics Dashboard** - Track post counts by status
- 🎨 **Modern GUI** - Clean CustomTkinter interface
- 🤖 **15+ Commands** - Comprehensive Telegram bot control
- 📝 **Custom Commentary** - Override AI with manual text
- ❤️ **Auto-Like** - Automatically likes posts when reposting
- ⚡ **Early Exit Optimization** - Stops checking after detecting processed posts

---

## 📋 Prerequisites

### Required
- **Python 3.13+** - [Download Python](https://www.python.org/downloads/)
- **LinkedIn Account** - Personal profile with reposting permissions
- **Telegram Bot Token** - Create via [@BotFather](https://t.me/botfather)
- **Telegram Chat ID** - Your personal chat ID ([Get it here](https://t.me/userinfobot))
- **OpenAI API Key** - [Get API key](https://platform.openai.com/api-keys)

### Optional
- **Windows 10/11** - Recommended for executable version
- **Company Page Access** - Monitoring target (public or accessible pages)

## 🔧 Installation

### 1. Clone or Download
```bash
cd c:\.Codding-Projects\LIPM
```

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```powershell
playwright install chromium
```

## 🎯 Quick Start

### 1. Launch Application
```powershell
python -m linkedin_post_monitor.main
```

### 2. Enter Passphrase
```
!Paralax1
```

### 3. Configure Settings
- **LinkedIn**: Username, Password, Company Page URL
- **Telegram**: Bot Token, Chat ID
- **OpenAI**: API Key, Model (gpt-4o-mini)

### 4. Start Monitoring
Click "Start Monitoring" button

### 5. Approve in Telegram
Reply to approval messages with:
- `/approve` - Use AI commentary
- `/revise [your text]` - Use custom commentary
- `/skip` - Ignore post

## 📁 Project Structure

```
LIPM/
├── linkedin_post_monitor/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── gui.py               # CustomTkinter interface
│   ├── config_manager.py    # Encrypted settings manager
│   ├── encryption.py        # AES-256-GCM encryption
│   ├── linkedin_scraper.py  # Playwright automation
│   ├── ai_commentary.py     # OpenAI integration
│   ├── telegram_bot.py      # Telegram bot handler
│   ├── post_database.py     # JSON-based post tracking
│   ├── monitor.py           # Scheduling & orchestration
│   └── utils.py             # Utilities and helpers
├── requirements.txt
├── README.md
└── prompt-requirement.md
```

## 🔐 Security

- **Credentials encrypted** with AES-256-GCM
- **Passphrase-protected** (default: `!Paralax1`)
- **Stored locally** only
- **Never transmitted** to third parties

---

## � Installation Methods

### Method 1: Windows Executable (Recommended)
1. Download latest release from [Releases](https://github.com/AlertX1978/LIPM/releases)
2. Extract `LIPM-Package.zip`
3. Run `LIPM.exe`
4. Enter passphrase and configure settings

### Method 2: Python Source
See installation instructions above

---

## 🎮 Telegram Commands

### Primary Actions (Reply to approval messages)
- `/repost` - Approve and repost with AI commentary
- `/skip` - Skip this post permanently
- `/redo` - Regenerate AI commentary
- `/just_like` - Like original post without reposting
- `/just_repost` - Repost instantly without commentary

### Information & Management
- `/resend [number]` - Resend last X posts (default: 5)
- `/resend_pending` - Resend only pending posts
- `/summary [number]` - Get summary of last X posts
- `/statistics` - Show post statistics by status
- `/start` - Show welcome message
- `/help` - Display command reference

---

## 🔧 Configuration

### Default Settings
```json
{
  "workflow": {
    "polling_frequency_minutes": 10,
    "posts_per_check": 10,
    "auto_approve": false,
    "posts_lookback": 10
  }
}
```

### Environment Variables (Optional)
You can also configure via environment variables:
- `LIPM_PASSPHRASE` - Master passphrase
- `LINKEDIN_USERNAME` - LinkedIn email
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID

---

## 🛠️ Building from Source

### Build Executable
```powershell
# Windows
.\build.ps1

# Or using batch file
.\build.bat
```

Output: `dist\LIPM-Package\LIPM.exe`

### Build Installer
See [Windows Installer Guide](#windows-installer-setup) below

---

## 🔐 Security Notes

- **Passphrase**: Default is `!Paralax1` - CHANGE THIS on first run
- **Encryption**: AES-256-GCM with PBKDF2 key derivation
- **Storage**: All credentials stored in `config.json` (encrypted)
- **Session**: LinkedIn session in `data/linkedin_session/`
- **Database**: Post tracking in `data/posts.json`

⚠️ **Important**: Keep `config.json` secure and never commit it to version control

---

## �🐛 Troubleshooting

### Common Issues

**"Passphrase invalid"**
- First run: Use default `!Paralax1`
- Subsequent: Use your configured passphrase
- Reset: Delete `config.json` to start fresh

**"LinkedIn login failed"**
- Check credentials in GUI settings
- Verify LinkedIn account is not locked
- Try manual login in browser first

**"Telegram bot not responding"**
- Verify bot token is correct
- Check chat ID matches your Telegram user
- Start conversation with bot first: `/start`

**"Posts not being detected"**
- Verify company page URL is correct
- Check monitoring is started (green indicator)
- Review logs in `logs/lipm.log`

---

## 📊 Project Structure

```
LIPM/
├── linkedin_post_monitor/       # Main application package
│   ├── main.py                  # Entry point & GUI
│   ├── monitor.py               # Orchestration & scheduling
│   ├── linkedin_scraper.py      # Playwright automation
│   ├── ai_commentary.py         # OpenAI integration
│   ├── telegram_bot.py          # Telegram bot handler
│   ├── post_database.py         # JSON database
│   ├── config_manager.py        # Settings & encryption
│   ├── encryption.py            # AES-256-GCM crypto
│   ├── gui.py                   # CustomTkinter UI
│   └── utils.py                 # Helpers & logging
├── data/                        # Application data
│   ├── posts.json              # Post tracking database
│   └── linkedin_session/       # Browser session
├── logs/                        # Log files
│   └── lipm.log               # Application logs
├── config.json                  # Encrypted configuration
├── requirements.txt             # Python dependencies
├── LIPM.spec                   # PyInstaller build config
├── build.ps1                   # Build script (PowerShell)
├── build.bat                   # Build script (Batch)
└── README.md                   # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Playwright** - Browser automation framework
- **OpenAI** - AI commentary generation
- **python-telegram-bot** - Telegram bot framework
- **CustomTkinter** - Modern GUI framework
- **Cryptography** - Encryption library

---

## ⚠️ Disclaimer

This tool is for personal use and educational purposes. Please ensure you comply with:
- LinkedIn's Terms of Service
- Your company's social media policies
- OpenAI's usage policies
- Telegram's bot guidelines

Use responsibly and at your own risk.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/AlertX1978/LIPM/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AlertX1978/LIPM/discussions)

---

## 🚀 Roadmap

- [ ] Multi-company monitoring
- [ ] Post scheduling
- [ ] Analytics dashboard
- [ ] Custom AI models
- [ ] Browser extension
- [ ] Mobile app

---

**Made with ❤️ for LinkedIn automation**

### LinkedIn Login Issues
- Verify credentials in settings
- Check for 2FA notifications in Telegram
- Ensure Playwright browsers are installed

### No Telegram Messages
- Verify Bot Token is correct
- Ensure Chat ID is numeric (negative for groups)
- Check bot has permission to send messages

### OpenAI Errors
- Verify API key is valid
- Check account has available credits
- Ensure model name is correct (gpt-4o-mini)

## 📞 Support

For issues or questions, check the `prompt-requirement.md` file for detailed specifications.

## 📄 License

Private/Internal Use

---

**Built with Python 3.14, CustomTkinter, Playwright, and OpenAI GPT-4o-mini**
