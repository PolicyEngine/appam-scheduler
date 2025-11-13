"""Working scraper using page title."""
import json
import re
import sqlite3
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def extract_session_data(page, session_id):
    """Extract session data from loaded page."""
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

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
        'raw_html': html
    }

    # Get title from page title tag or og:title meta
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        # Remove "APPAM Fall Research Conference: " prefix
        title_text = re.sub(r'^APPAM Fall Research Conference:\s*', '', title_text)
        session_data['title'] = title_text.strip()

    # Fallback to og:title
    if not session_data['title']:
        og_title = soup.find('meta', property='og:title')
        if og_title:
            session_data['title'] = og_title.get('content', '')

    text_content = soup.get_text()

    # Date/time
    date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+\s+\d+),\s+(\d+:\d+)\s*to\s*(\d+:\d+)(am|pm)'
    date_match = re.search(date_pattern, text_content, re.IGNORECASE)
    if date_match:
        day_name = date_match.group(1)
        date_str = date_match.group(2)
        start = date_match.group(3)
        end = date_match.group(4)
        period = date_match.group(5)

        # Convert to full date (assume 2025)
        try:
            date_obj = datetime.strptime(f"{date_str}, 2025", '%B %d, %Y')
            session_data['date'] = date_obj.strftime('%Y-%m-%d')
        except:
            pass

        session_data['start_time'] = f"{start}{period}"
        session_data['end_time'] = f"{end}{period}"

    # Location - look for "Property: ... Floor: ... Room: ..."
    location_pattern = r'Property:\s*([^,]+),\s*Floor:\s*([^,]+),\s*Room:\s*([^\n]+)'
    location_match = re.search(location_pattern, text_content)
    if location_match:
        property_name = location_match.group(1).strip()
        floor = location_match.group(2).strip()
        room = location_match.group(3).strip()
        session_data['location'] = f"{property_name}, {floor}, {room}"

    # Extract presenters - look for names with affiliations
    presenters = set()
    # Pattern: Name (University/Institution)
    name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*\(([^)]+)\)'
    for match in re.finditer(name_pattern, text_content):
        name = match.group(1).strip()
        affiliation = match.group(2).strip()
        if len(name) > 5 and 'University' in affiliation or 'Institute' in affiliation or 'College' in affiliation:
            presenters.add(name)

    session_data['presenters'] = json.dumps(sorted(list(presenters)))

    # Description - get Abstract section
    abstract_match = re.search(r'Abstract\s+(.*?)(?=\n\n[A-Z]|\Z)', text_content, re.DOTALL)
    if abstract_match:
        session_data['description'] = abstract_match.group(1).strip()[:1000]  # Limit length

    return session_data


def save_to_db(session_data, conn):
    """Save to database."""
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO sessions
        (session_id, title, date, start_time, end_time, location, description, chair, papers, raw_html)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_data['session_id'], session_data['title'], session_data['date'],
        session_data['start_time'], session_data['end_time'], session_data['location'],
        session_data['description'], session_data['chair'], session_data['papers'],
        session_data['raw_html']
    ))

    # Save location
    if session_data['location']:
        cursor.execute('INSERT OR IGNORE INTO locations (name) VALUES (?)', (session_data['location'],))

    # Save presenters
    if session_data['presenters']:
        presenters = json.loads(session_data['presenters'])
        cursor.execute('DELETE FROM session_presenters WHERE session_id = ?', (session_data['session_id'],))
        for presenter_name in presenters:
            cursor.execute('INSERT OR IGNORE INTO presenters (name) VALUES (?)', (presenter_name,))
            cursor.execute('SELECT id FROM presenters WHERE name = ?', (presenter_name,))
            result = cursor.fetchone()
            if result:
                presenter_id = result[0]
                cursor.execute('''
                    INSERT OR IGNORE INTO session_presenters (session_id, presenter_id)
                    VALUES (?, ?)
                ''', (session_data['session_id'], presenter_id))

    conn.commit()


def main():
    # Load session IDs
    with open('session_ids_all.txt', 'r') as f:
        session_ids = [line.strip() for line in f if line.strip()]

    # Load cookies
    with open('cookies.json', 'r') as f:
        cookies = json.load(f)

    print(f"Scraping {len(session_ids)} sessions...\n", flush=True)

    # Init DB
    conn = sqlite3.connect('appam_sessions.db')
    from scraper import APPAMScraper
    scraper = APPAMScraper()
    scraper.init_database()

    found = 0
    errors = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        for i, session_id in enumerate(session_ids, 1):
            try:
                url = f"http://convention2.allacademic.com/one/appam/appam25/index.php?program_focus=view_session&selected_session_id={session_id}&cmd=online_program_direct_link&sub_action=online_program"

                page.goto(url, timeout=30000)
                page.wait_for_function("document.body.innerText.length > 500", timeout=10000)

                session_data = extract_session_data(page, session_id)

                if session_data['title'] and len(session_data['title']) > 10:
                    save_to_db(session_data, conn)
                    found += 1
                    if found <= 30 or found % 50 == 0:
                        print(f"[{i}/{len(session_ids)}] ✓ {session_data['title'][:70]}", flush=True)
                    elif i % 20 == 0:
                        print(f"[{i}/{len(session_ids)}] Progress: {found} found", flush=True)
                else:
                    errors += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    print(f"[{i}/{len(session_ids)}] ✗ {str(e)[:80]}", flush=True)

        browser.close()

    conn.close()

    print(f"\n✓ Complete! Scraped {found} sessions ({errors} errors)", flush=True)

    # Stats
    conn = sqlite3.connect('appam_sessions.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE length(title) > 10")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM presenters")
    presenters_count = cursor.fetchone()[0]
    conn.close()

    print(f"\nDatabase: {total} sessions, {presenters_count} presenters")


if __name__ == '__main__':
    main()
