"""
Extract presenter names and affiliations from raw HTML.
"""
import sqlite3
import re
from bs4 import BeautifulSoup


def extract_presenters_from_html():
    """Extract presenters from raw HTML in database."""
    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get high-value sessions with raw HTML
    cursor.execute('''
        SELECT session_id, title, raw_html, general_score
        FROM sessions
        WHERE general_score >= 60 AND raw_html IS NOT NULL AND raw_html != ''
        ORDER BY general_score DESC
    ''')

    presenters_found = []

    for row in cursor.fetchall():
        session_id = row['session_id']
        title = row['title']
        html = row['raw_html']
        score = row['general_score']

        if not html or len(html) < 100:
            continue

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        # Extract presenters
        # Common patterns:
        # "Presenting Author: Name, Affiliation"
        # "Author: Name, Affiliation"
        # "Name (Affiliation)"
        # "Name, Affiliation"

        presenter_matches = []

        # Pattern 1: "Presenting Author: Name, Affiliation"
        for match in re.finditer(r'Presenting Author:\s*([^,\n]+),\s*([^\n]+)', text):
            name = match.group(1).strip()
            affiliation = match.group(2).strip()
            presenter_matches.append((name, affiliation))

        # Pattern 2: "Name (University/Institute)"
        for match in re.finditer(r'([A-Z][a-z]+\s+[A-Z]\.?\s*[A-Z][a-z]+)\s*\(([^)]+(?:University|Institute|College)[^)]*)\)', text):
            name = match.group(1).strip()
            affiliation = match.group(2).strip()
            if len(name) > 5:
                presenter_matches.append((name, affiliation))

        # Pattern 3: Chair/Organizer/Moderator
        for pattern in [r'Chair:\s*([^,\n]+),\s*([^\n]+)',
                       r'Organizer:\s*([^,\n]+),\s*([^\n]+)',
                       r'Moderator:\s*([^,\n]+),\s*([^\n]+)']:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                affiliation = match.group(2).strip()
                if len(name) > 5:
                    presenter_matches.append((name, affiliation))

        if presenter_matches:
            presenters_found.append({
                'session_id': session_id,
                'session_title': title,
                'session_score': score,
                'presenters': presenter_matches
            })

    conn.close()

    # Aggregate by presenter
    presenter_profiles = {}

    for session_data in presenters_found:
        for name, affiliation in session_data['presenters']:
            if name not in presenter_profiles:
                presenter_profiles[name] = {
                    'name': name,
                    'affiliation': affiliation,
                    'sessions': [],
                    'max_score': 0,
                    'topics': set()
                }

            presenter_profiles[name]['sessions'].append({
                'title': session_data['session_title'],
                'score': session_data['session_score']
            })

            presenter_profiles[name]['max_score'] = max(
                presenter_profiles[name]['max_score'],
                session_data['session_score']
            )

            # Extract topics
            title_lower = session_data['session_title'].lower()
            if 'tax' in title_lower or 'ctc' in title_lower or 'eitc' in title_lower:
                presenter_profiles[name]['topics'].add('Tax Policy')
            if 'poverty' in title_lower or 'income' in title_lower:
                presenter_profiles[name]['topics'].add('Poverty')
            if 'snap' in title_lower or 'medicaid' in title_lower or 'benefit' in title_lower:
                presenter_profiles[name]['topics'].add('Benefit Programs')
            if 'health' in title_lower:
                presenter_profiles[name]['topics'].add('Health Policy')
            if 'housing' in title_lower:
                presenter_profiles[name]['topics'].add('Housing')

    # Convert to list for export
    for presenter in presenter_profiles.values():
        presenter['topics'] = list(presenter['topics'])

    presenters_list = list(presenter_profiles.values())
    presenters_list.sort(key=lambda x: x['max_score'], reverse=True)

    return presenters_list


def main():
    print("Extracting presenters from session HTML...\n")
    presenters = extract_presenters_from_html()

    print(f"Found {len(presenters)} unique presenters in high-value sessions\n")

    print("="*80)
    print("TOP 30 PEOPLE TO EMAIL/CONNECT WITH")
    print("="*80)
    print()

    for i, presenter in enumerate(presenters[:30], 1):
        print(f"{i}. {presenter['name']}")
        print(f"   {presenter['affiliation']}")
        print(f"   Topics: {', '.join(presenter['topics'])}")
        print(f"   Relevance: {presenter['max_score']:.0f}/100")
        print(f"   Sessions: {len(presenter['sessions'])}")
        for session in presenter['sessions'][:2]:
            print(f"     - {session['title'][:55]}...")
        print()

    # Save to file
    import json
    with open('public/data/networking_contacts.json', 'w') as f:
        json.dump(presenters[:50], f, indent=2)

    print(f"✓ Exported to public/data/networking_contacts.json")

    # Also create an email list for each person
    print("\n" + "="*80)
    print("PRIORITY CONTACTS BY TEAM MEMBER")
    print("="*80)

    for person_name, topics in [
        ('Max Ghenis', ['Tax Policy', 'Poverty', 'Benefit Programs']),
        ('Pavel Makarchuk', ['Tax Policy', 'Microsimulation', 'Benefit Programs']),
        ('Daphne Hansell', ['Health Policy', 'Benefit Programs'])
    ]:
        print(f"\n{person_name}:")
        relevant = [p for p in presenters if any(t in p['topics'] for t in topics)][:10]
        for presenter in relevant:
            print(f"  - {presenter['name']} ({presenter['affiliation'][:40] if len(presenter['affiliation']) > 40 else presenter['affiliation']})")


if __name__ == '__main__':
    main()
