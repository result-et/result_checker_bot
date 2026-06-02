# Ethiopian Airlines Results Scraper Telegram Bot & Dashboard

A premium Python-based Flask web application designed for Render's free tier that scrapes the official Ethiopian Airlines careers results page. It checks for new results related to **AMT (Aircraft Maintenance Technician)** and **Pilot** positions and alerts subscribed users immediately via a Telegram Bot. It also hosts a modern, responsive web dashboard to track stats and parsed announcements.

## System Architecture for Render Free Tier

Since Render's free tier puts web services to sleep after 15 minutes of inactivity and wipes local SQLite files on restarts:
1. **Database:** We use **Neon.tech** (a free Postgres provider) to store subscribed users and announcement hashes persistently.
2. **Webhooks:** The Telegram bot runs on webhooks. Incoming Telegram interactions wake up the dyno, respond, and sleep.
3. **Automated Scraping:** An external free cron service (like [cron-job.org](https://cron-job.org)) calls the `/api/check-results` endpoint every 10 minutes. This pulls results, sends Telegram notifications, and keeps the Render service awake permanently!

---

## Local Setup & Testing

### 1. Prerequisites
- Python 3.10+
- A Telegram Bot token (from [@BotFather](https://t.me/BotFather))
- A Neon.tech PostgreSQL connection string (provided by you)

### 2. Installation
Clone the project or copy files to a directory and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (based on `.env.example`):
```ini
TELEGRAM_BOT_TOKEN=8781730368:AAH9CsnaAzqx2KXdHnSILXA_Vdzd-LC_2hg
DATABASE_URL=postgresql://neondb_owner:npg_aiBYGMoX52yL@ep-gentle-morning-aqyskt1h.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require
PORT=5000
```
*(Leave `WEBHOOK_URL` blank for local development to trigger background polling).*

### 4. Running Locally
Start the Flask server:
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser to view the dashboard. Send `/start` to your Telegram bot, and click the **Check Page Now** button on the dashboard to test the scraping logic.

---

## Render Deployment Guide

### Step 1: Create a Web Service on Render
1. Sign in to [Render](https://render.com).
2. Click **New** > **Web Service**.
3. Connect your GitHub repository or use a public Git URL.
4. Set the following fields:
   - **Name:** `et-airlines-results-bot` (or your preferred name)
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** `Free`

### Step 2: Configure Environment Variables
In the **Environment** tab on Render, add the following variables:
- `TELEGRAM_BOT_TOKEN`: `8781730368:AAH9CsnaAzqx2KXdHnSILXA_Vdzd-LC_2hg`
- `DATABASE_URL`: `postgresql://neondb_owner:npg_aiBYGMoX52yL@ep-gentle-morning-aqyskt1h.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require`
- `WEBHOOK_URL`: `https://your-app-name.onrender.com` *(Replace with the URL Render assigns to your service)*

Once saved, Render will redeploy your service. On startup, the web application will automatically register itself as the webhook receiver with Telegram!

---

## Setting up Automated Checks (cron-job.org)

To trigger the scraper periodically and prevent your Render web service from spinning down, schedule a free cron trigger:
1. Go to [cron-job.org](https://cron-job.org) and create a free account.
2. Click **Create Cronjob**.
3. Provide the following details:
   - **Title:** `ET Career Scraper Check`
   - **Address:** `https://your-app-name.onrender.com/api/check-results` *(Replace with your Render URL)*
   - **Request Method:** `GET` (or `POST`)
   - **Schedule:** `Every 10 minutes` (under Custom scheduling)
4. Click **Create**.

Your setup is now fully automated! The bot will query Ethiopian Airlines every 10 minutes, record announcements in your Neon database, and message you immediately when a Pilot or AMT post appears.
