# Quick Start Guide

## Setup (First Time Only)

1. **Install dependencies:**
   ```bash
   make install
   ```

2. **Run the pipeline:**
   ```bash
   ./run_pipeline.sh
   # Or use make:
   make pipeline
   ```

3. **View the app:**
   ```bash
   make debug
   # Or:
   npm start
   ```

## What the Pipeline Does

1. **Scrapes** conference sessions from APPAM website → `appam_sessions.db`
2. **Scores** sessions based on PolicyEngine's research focus → updates database
3. **Schedules** team members to sessions ensuring booth coverage → updates database
4. **Exports** database to JSON files → `public/data/*.json`

## The Web App

After running the pipeline, you can view the scheduler at http://localhost:3000

Features:
- **Home Page**: Overview with team schedules
- **Person Schedules**: Click on a team member to see their assigned sessions
- **All Sessions**: Browse and filter all conference sessions
- **Presenters**: Searchable directory of all presenters with contact info

## Deploying

### Option 1: Push to GitHub
```bash
git add .
git commit -m "Initial APPAM scheduler"
git push origin main
```

GitHub Actions will automatically build and deploy to GitHub Pages.

### Option 2: Manual Deploy
```bash
npm run deploy
```

## Making Changes

### Add/Update Sessions
Re-run the scraper:
```bash
make scrape score schedule export
```

### Adjust Relevance Scoring
Edit `relevance_scorer.py` to modify keywords and weights, then:
```bash
make score schedule export
```

### Modify Schedule Logic
Edit `scheduler.py` to change assignment rules, then:
```bash
make schedule export
```

### Update UI
Edit files in `src/` directory, then:
```bash
npm start  # For development
npm run build  # For production
```

## Database Schema

The SQLite database has these tables:
- `sessions` - Conference sessions
- `presenters` - Presenter info (name, email, affiliation)
- `session_presenters` - Links sessions to presenters
- `papers` - Individual paper titles
- `locations` - Conference rooms
- `time_slots` - Time periods
- `people` - PolicyEngine team members

Query examples:
```bash
sqlite3 appam_sessions.db
```

```sql
-- Find all sessions by a presenter
SELECT s.title, s.date, s.start_time
FROM sessions s
JOIN session_presenters sp ON s.session_id = sp.session_id
JOIN presenters p ON sp.presenter_id = p.id
WHERE p.name LIKE '%Smith%';

-- Find all high-value unassigned sessions
SELECT title, relevance_score, date, start_time
FROM sessions
WHERE relevance_score >= 20 AND assigned_to IS NULL
ORDER BY relevance_score DESC;

-- Get presenter contact information
SELECT p.name, p.email, COUNT(sp.session_id) as session_count
FROM presenters p
LEFT JOIN session_presenters sp ON p.id = sp.presenter_id
GROUP BY p.id
ORDER BY session_count DESC;
```

## Troubleshooting

### Scraper fails
- Check internet connection
- APPAM website might have changed structure
- Try adding `headless=False` in scraper to see what's happening

### No sessions in database
- Run `make scrape` first
- Check `appam_sessions.db` exists
- Run SQL query: `SELECT COUNT(*) FROM sessions;`

### Web app shows no data
- Run `make export` to regenerate JSON files
- Check `public/data/` directory has JSON files
- Clear browser cache

### GitHub Pages not deploying
- Check repository settings → Pages → Source is set to "GitHub Actions"
- Check Actions tab for build errors
- Make sure `.github/workflows/deploy.yml` is in repository

## Contact

Questions? Ask Max, Pavel, or Daphne!
