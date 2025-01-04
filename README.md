# Waitlist Signup Bot for Abstract

## Requirements

- Python 3.10+
- pip
- Email provider (Gmail recommended)
- Domain with catchall turned on

You need your own domain with catchall turned on. I recommend purchasing a `.com` domain from [Namecheap](https://www.namecheap.com) for less than $10. Then enabling a wildcard/catchall to your email provider.

Please note that uncommond domain extensions do not work as Abstract block them out therefore `.com` domains are recommended as they are cheap and come with free privacy registration when purchasing from Namecheap.

## Installation & Usage

1. Install:

```
pip install -r requirements.txt
```

2. Edit config.json with your email, password, and imap server

For gmail:

```
"imap_server": "imap.gmail.com",
"imap_port": 993,
"imap_username": "your_email@gmail.com",
"imap_password": "your_password",
"email_suffix": "your_domain.com"
```

For outlook:

```
"imap_server": "outlook.office365.com",
"imap_port": 993,
"imap_username": "your_email@outlook.com",
"imap_password": "your_password",
"email_suffix": "your_domain.com"
```

3. Run:

```
python main.py
```

When running, the bot asks for the number of threads you want to run and how many signups each thread should do. The bot is harcoded to have 5 verification workers running at a time. This means the bot runs the threads to signup and runs the verification workers in parallel.

You need to have a computer that can handle at least 6 threads running at a time, or you can edit the `verification_worker` function to have less threads running at a time on `line 267` in the `main()` function.

### Notice

This code is not intended to be harmful. This is for education purposes only. I liked the website and wanted to stress test it. The waitlist feature will probably be useless and return no value. I created this in under 30 minutes and spent 5 minutes formatting/linting it, so the nesting and formatting is terrible lol.