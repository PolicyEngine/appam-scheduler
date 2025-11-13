"""
APPAM Conference Session Scraper
Scrapes session data from the APPAM conference website.
"""
import json
import sqlite3
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


class APPAMScraper:
    def __init__(self, db_path='appam_sessions.db', cookies_file=None):
        self.db_path = db_path
        self.base_url = "http://convention2.allacademic.com/one/appam/appam25/"
        self.session_ids = set()
        self.cookies_file = cookies_file

    def init_database(self):
        """Initialize the SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                description TEXT,
                chair TEXT,
                papers TEXT,
                relevance_score REAL DEFAULT 0,
                assigned_to TEXT,
                raw_html TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS people (
                name TEXT PRIMARY KEY,
                role TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presenters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT,
                affiliation TEXT,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_presenters (
                session_id TEXT NOT NULL,
                presenter_id INTEGER NOT NULL,
                role TEXT,
                PRIMARY KEY (session_id, presenter_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (presenter_id) REFERENCES presenters(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                abstract TEXT,
                session_id TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS paper_authors (
                paper_id INTEGER NOT NULL,
                presenter_id INTEGER NOT NULL,
                author_order INTEGER,
                PRIMARY KEY (paper_id, presenter_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id),
                FOREIGN KEY (presenter_id) REFERENCES presenters(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                building TEXT,
                capacity INTEGER,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                UNIQUE(date, start_time, end_time)
            )
        ''')

        # Insert the three people
        people = [
            ('Max Ghenis', 'CEO'),
            ('Pavel Makarchuk', 'Director of Growth'),
            ('Daphne Hansell', 'Health Policy Analyst')
        ]
        cursor.executemany('INSERT OR IGNORE INTO people (name, role) VALUES (?, ?)', people)

        conn.commit()
        conn.close()

    def scrape_calendar_page(self, date_str='2025-11-13'):
        """Scrape the calendar page to get all session IDs for a given date."""
        session_ids = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Load cookies if provided
            if self.cookies_file and os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)

            page = context.new_page()

            url = f"{self.base_url}index.php?cmd=Online+Program+Load+Focus&program_focus=program_calendar&selected_day={date_str}"
            print(f"Scraping calendar for {date_str}...")
            page.goto(url, wait_until='networkidle')

            # Get the page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Find all session links
            links = soup.find_all('a', href=re.compile(r'selected_session_id=\d+'))
            for link in links:
                match = re.search(r'selected_session_id=(\d+)', link['href'])
                if match:
                    session_id = match.group(1)
                    session_ids.append(session_id)
                    self.session_ids.add(session_id)

            browser.close()

        print(f"Found {len(session_ids)} sessions for {date_str}")
        return session_ids

    def scrape_all_calendar_dates(self):
        """Scrape all conference dates."""
        # APPAM 2025 dates (including pre-conference)
        dates = [
            '2025-11-12',  # Wednesday (pre-conference)
            '2025-11-13',  # Thursday
            '2025-11-14',  # Friday
            '2025-11-15',  # Saturday
        ]

        all_session_ids = []
        for date in dates:
            session_ids = self.scrape_calendar_page(date)
            all_session_ids.extend(session_ids)

        return list(self.session_ids)

    def scrape_session_detail(self, session_id):
        """Scrape detailed information for a specific session."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Load cookies if provided
            if self.cookies_file and os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)

            page = context.new_page()

            url = f"{self.base_url}index.php?program_focus=view_session&selected_session_id={session_id}&cmd=online_program_direct_link&sub_action=online_program"
            print(f"Scraping session {session_id}...")
            page.goto(url, wait_until='load')

            # Wait for the session title to load (h1 or h2 element)
            try:
                page.wait_for_selector('h2, h1', timeout=10000)
            except:
                pass  # If it times out, continue anyway

            # Additional wait to ensure all content is loaded
            page.wait_for_timeout(1000)

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Extract session information
            session_data = {
                'session_id': session_id,
                'title': '',
                'date': '',
                'start_time': '',
                'end_time': '',
                'location': '',
                'description': '',
                'chair': '',
                'papers': '',
                'presenters': '',
                'raw_html': content
            }

            # Extract title
            title_elem = soup.find('h2') or soup.find('h1')
            if title_elem:
                session_data['title'] = title_elem.get_text(strip=True)

            # Extract time and location information
            # Look for patterns like "Thursday, November 13, 2025: 10:00 AM-11:30 AM"
            text_content = soup.get_text()

            # Extract date and time
            date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+\s+\d+,\s+\d{4}):\s+(\d+:\d+\s+[AP]M)\s*-\s*(\d+:\d+\s+[AP]M)'
            date_match = re.search(date_pattern, text_content)
            if date_match:
                date_str = date_match.group(2)
                session_data['date'] = datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
                session_data['start_time'] = date_match.group(3)
                session_data['end_time'] = date_match.group(4)

            # Extract location
            location_pattern = r'Location:\s*([^\n]+)'
            location_match = re.search(location_pattern, text_content)
            if location_match:
                session_data['location'] = location_match.group(1).strip()

            # Extract chair
            chair_pattern = r'Chair:\s*([^\n]+)'
            chair_match = re.search(chair_pattern, text_content)
            if chair_match:
                session_data['chair'] = chair_match.group(1).strip()

            # Extract description and papers
            # Find all text in the main content area
            main_content = soup.find('div', class_='content') or soup.find('body')
            if main_content:
                paragraphs = main_content.find_all('p')
                description_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        description_parts.append(text)
                session_data['description'] = '\n\n'.join(description_parts)

            # Extract paper titles and authors
            papers = []
            paper_divs = soup.find_all('div', class_='paper') if soup.find_all('div', class_='paper') else []

            # Alternative: look for common patterns in session pages
            if not paper_divs:
                # Look for bullet points or numbered lists that might contain papers
                lists = soup.find_all(['ul', 'ol'])
                for lst in lists:
                    items = lst.find_all('li')
                    for item in items:
                        text = item.get_text(strip=True)
                        if text:
                            papers.append(text)
            else:
                for paper_div in paper_divs:
                    paper_text = paper_div.get_text(strip=True)
                    papers.append(paper_text)

            session_data['papers'] = json.dumps(papers)

            # Extract presenters/authors from the page
            presenters = set()  # Use set to avoid duplicates

            # Look for author names in various patterns
            # Common patterns: "Author:", "Presenter:", "Authors:", followed by names
            author_patterns = [
                r'Author[s]?:\s*([^\n]+)',
                r'Presenter[s]?:\s*([^\n]+)',
                r'Paper by:\s*([^\n]+)',
                r'By:\s*([^\n]+)'
            ]

            for pattern in author_patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    author_text = match.group(1).strip()
                    # Split by common delimiters
                    authors = re.split(r'[;,]|\band\b', author_text)
                    for author in authors:
                        author = author.strip()
                        if author and len(author) > 3:  # Filter out very short strings
                            # Remove common suffixes like (University of X)
                            author = re.sub(r'\([^)]+\)', '', author).strip()
                            if author:
                                presenters.add(author)

            # Also extract from paper strings if they follow "Name - Title" pattern
            for paper in papers:
                # Look for pattern: "Name(s) - Paper Title" or "Name(s): Paper Title"
                name_match = re.match(r'^([^-:]+)[-:]', paper)
                if name_match:
                    potential_names = name_match.group(1).strip()
                    # Check if it looks like names (has common name patterns)
                    if re.search(r'\b[A-Z][a-z]+\b', potential_names):
                        names = re.split(r'[;,]|\band\b', potential_names)
                        for name in names:
                            name = name.strip()
                            if name and len(name) > 3:
                                name = re.sub(r'\([^)]+\)', '', name).strip()
                                if name:
                                    presenters.add(name)

            # Look for specific HTML elements that might contain author info
            # Check for divs or spans with class names containing 'author', 'presenter', etc.
            author_elements = soup.find_all(class_=re.compile(r'author|presenter|speaker', re.IGNORECASE))
            for elem in author_elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 3 and len(text) < 100:  # Reasonable length for a name
                    text = re.sub(r'\([^)]+\)', '', text).strip()
                    if text:
                        presenters.add(text)

            session_data['presenters'] = json.dumps(sorted(list(presenters)))

            browser.close()

            return session_data

    def save_session(self, session_data):
        """Save session data to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Save session
        cursor.execute('''
            INSERT OR REPLACE INTO sessions
            (session_id, title, date, start_time, end_time, location, description, chair, papers, raw_html)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data['session_id'],
            session_data['title'],
            session_data['date'],
            session_data['start_time'],
            session_data['end_time'],
            session_data['location'],
            session_data['description'],
            session_data['chair'],
            session_data['papers'],
            session_data['raw_html']
        ))

        # Save location
        if session_data.get('location'):
            cursor.execute('''
                INSERT OR IGNORE INTO locations (name)
                VALUES (?)
            ''', (session_data['location'],))

        # Save time slot
        if session_data.get('date') and session_data.get('start_time') and session_data.get('end_time'):
            cursor.execute('''
                INSERT OR IGNORE INTO time_slots (date, start_time, end_time)
                VALUES (?, ?, ?)
            ''', (session_data['date'], session_data['start_time'], session_data['end_time']))

        # Save presenters and link to session
        if session_data.get('presenters'):
            try:
                presenters = json.loads(session_data['presenters']) if isinstance(session_data['presenters'], str) else session_data['presenters']

                # Delete existing presenter relationships for this session
                cursor.execute('DELETE FROM session_presenters WHERE session_id = ?', (session_data['session_id'],))

                for presenter_name in presenters:
                    # Insert presenter (or ignore if exists)
                    cursor.execute('''
                        INSERT OR IGNORE INTO presenters (name)
                        VALUES (?)
                    ''', (presenter_name,))

                    # Get presenter ID
                    cursor.execute('SELECT id FROM presenters WHERE name = ?', (presenter_name,))
                    presenter_id = cursor.fetchone()[0]

                    # Link presenter to session
                    cursor.execute('''
                        INSERT OR IGNORE INTO session_presenters (session_id, presenter_id)
                        VALUES (?, ?)
                    ''', (session_data['session_id'], presenter_id))
            except Exception as e:
                print(f"  Warning: Could not save presenters: {e}")

        # Save papers
        if session_data.get('papers'):
            try:
                papers_list = json.loads(session_data['papers']) if isinstance(session_data['papers'], str) else session_data['papers']

                # Delete existing papers for this session
                cursor.execute('DELETE FROM papers WHERE session_id = ?', (session_data['session_id'],))

                for paper_text in papers_list:
                    if paper_text and len(paper_text) > 3:
                        cursor.execute('''
                            INSERT INTO papers (title, session_id)
                            VALUES (?, ?)
                        ''', (paper_text, session_data['session_id']))
            except Exception as e:
                print(f"  Warning: Could not save papers: {e}")

        conn.commit()
        conn.close()

    def scrape_all(self):
        """Main method to scrape all sessions."""
        print("Initializing database...")
        self.init_database()

        print("Scraping calendar pages...")
        session_ids = self.scrape_all_calendar_dates()

        print(f"\nFound {len(session_ids)} total sessions. Scraping details...")
        for i, session_id in enumerate(session_ids, 1):
            try:
                print(f"[{i}/{len(session_ids)}] Scraping session {session_id}...")
                session_data = self.scrape_session_detail(session_id)
                self.save_session(session_data)
                print(f"  ✓ Saved: {session_data['title'][:60]}...")
            except Exception as e:
                print(f"  ✗ Error scraping session {session_id}: {e}")
                continue

        print("\n✓ Scraping complete!")


if __name__ == '__main__':
    import sys

    cookies_file = None
    if len(sys.argv) > 1 and sys.argv[1] == '--cookies':
        if len(sys.argv) > 2:
            cookies_file = sys.argv[2]
            print(f"Using cookies from: {cookies_file}")
        else:
            print("Error: --cookies requires a file path")
            print("Usage: python scraper.py --cookies cookies.json")
            sys.exit(1)

    scraper = APPAMScraper(cookies_file=cookies_file)
    scraper.scrape_all()
