# APPAM Conference Scheduler

A web application for scheduling conference session attendance for the PolicyEngine team at APPAM 2025.

## Features

- **Web Scraping**: Automatically scrapes session data from the APPAM conference website
- **Relevance Scoring**: Scores sessions based on PolicyEngine's research focus areas:
  - Tax-benefit microsimulation
  - Health policy
  - Poverty and inequality
  - Policy modeling
  - And more
- **Smart Scheduling**: Assigns team members to sessions while ensuring booth coverage
- **Personalized Recommendations**: Adjusts scores based on individual team member interests
- **Static Web App**: React-based interface with PolicyEngine design system
- **Presenter Database**: Relational database of all presenters and their contact information

## Project Structure

```
appam-scheduler/
├── scraper.py              # Web scraper for APPAM conference data
├── relevance_scorer.py     # Session relevance scoring algorithm
├── scheduler.py            # Smart scheduling with constraints
├── export_to_json.py       # Export database to JSON for static site
├── tests/                  # Unit tests (pytest)
├── src/                    # React application source
├── public/                 # Static assets and data
└── .github/workflows/      # CI/CD for GitHub Pages
```

## Setup

### Python Requirements

```bash
# Install Python dependencies using uv
uv pip install -e ".[dev]"

# Install Playwright browsers
uv run playwright install
```

### Node.js Requirements

```bash
# Install Node dependencies
npm install
```

## Usage

### 1. Scrape Conference Data

The APPAM conference schedule requires login to view. You'll need to export your browser cookies after logging in.

**Step 1: Export Cookies**
1. Log into https://convention2.allacademic.com/one/appam/appam25/
2. Open browser DevTools (F12 or Cmd+Option+I)
3. Go to Console tab
4. Paste and run this code:
   ```javascript
   copy(JSON.stringify(document.cookie.split('; ').map(c => {
       const [name, value] = c.split('=');
       return { name, value, domain: '.allacademic.com', path: '/' };
   })))
   ```
5. Create `cookies.json` and paste the copied content

**Step 2: Run Scraper**
```bash
# Scrape all sessions (with authentication)
uv run python scraper.py --cookies cookies.json

# Without authentication (will only get public sessions)
uv run python scraper.py
```

This will create `appam_sessions.db` with all scraped data in a relational structure:
- `sessions` - Session details
- `presenters` - Presenter contact information
- `session_presenters` - Many-to-many relationships
- `papers` - Individual papers
- `locations` - Conference rooms
- `time_slots` - Time periods

### 2. Score Sessions

```bash
# Calculate relevance scores for all sessions
uv run python relevance_scorer.py
```

This updates the database with relevance scores based on PolicyEngine's focus areas.

### 3. Generate Schedule

```bash
# Create optimized schedule with booth coverage
uv run python scheduler.py
```

This assigns team members to sessions while ensuring:
- At least one person at the booth at all times
- High-value sessions are covered
- Workload is balanced

### 4. Export to JSON

```bash
# Export database to JSON for the web app
uv run python export_to_json.py
```

This creates JSON files in `public/data/`:
- `sessions.json` - All sessions with presenters
- `schedule.json` - Assigned schedule by person
- `presenters.json` - Presenter directory
- `stats.json` - Summary statistics

### 5. Run Web App Locally

```bash
# Start development server
npm start
```

Visit http://localhost:3000 to view the scheduler app.

### 6. Deploy to GitHub Pages

The app automatically deploys to GitHub Pages when you push to the main branch.

```bash
# Build for production
npm run build

# Or deploy manually
npm run deploy
```

## Testing

```bash
# Run Python tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html
```

## Team Members

- **Max Ghenis** (CEO) - Focus: Universal Basic Income, poverty reduction
- **Pavel Makarchuk** (Director of Growth) - Focus: Microsimulation, policy modeling
- **Daphne Hansell** (Health Policy Analyst) - Focus: Health policy, Medicaid/Medicare

## Relevance Scoring

Sessions are scored based on keyword matching with PolicyEngine's areas of focus:

### High-Value Keywords (weight 9-10):
- microsimulation, tax policy, tax reform
- benefit programs (SNAP, TANF, EITC, CTC)
- health policy, Medicaid, Medicare, ACA
- universal basic income, guaranteed income

### Medium-Value Keywords (weight 5-8):
- policy simulation, distributional analysis
- poverty, inequality, welfare
- administrative data, microdata

### Personalized Scoring:
- Max Ghenis: 2x multiplier for UBI/guaranteed income topics
- Daphne Hansell: 2x multiplier for health policy topics
- Pavel Makarchuk: 1.5x multiplier for microsimulation/modeling topics

## Database Schema

The application uses a relational SQLite database:

```sql
-- Core tables
sessions (session_id, title, date, time, location, ...)
presenters (id, name, email, affiliation, notes)
papers (id, title, abstract, session_id)
locations (id, name, building, capacity)
time_slots (id, date, start_time, end_time)

-- Junction tables
session_presenters (session_id, presenter_id, role)
paper_authors (paper_id, presenter_id, author_order)

-- Team management
people (name, role)
```

## Development

### Adding New Keywords

Edit `relevance_scorer.py` and add keywords to the `self.keywords` dictionary with appropriate weights.

### Modifying Scheduling Algorithm

Edit `scheduler.py` to adjust:
- Booth coverage rules
- Number of people per session
- Workload balancing

### Customizing UI

The app uses PolicyEngine's design system:
- Colors: See `src/index.css` CSS variables
- Components: Edit `src/App.js`
- Styling: Edit `src/App.css`

## Contributing

1. Write tests for new features
2. Follow PolicyEngine coding standards
3. Run tests before committing
4. Use descriptive commit messages

## License

Copyright © 2025 PolicyEngine

## Contact

For questions about this scheduler, contact the PolicyEngine team.
