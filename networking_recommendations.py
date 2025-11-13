"""
Generate networking recommendations - presenters to email/connect with.
Based on relevance to PolicyEngine work.
"""
import sqlite3
import json


def get_networking_recommendations(db_path='appam_sessions.db'):
    """Get presenters worth connecting with, separate from session attendance."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get presenters from high-value sessions
    cursor.execute('''
        SELECT DISTINCT
            p.name,
            p.email,
            p.affiliation,
            s.title as session_title,
            s.general_score,
            s.max_score,
            s.pavel_score,
            s.daphne_score,
            s.date,
            s.start_time
        FROM presenters p
        JOIN session_presenters sp ON p.id = sp.presenter_id
        JOIN sessions s ON sp.session_id = s.session_id
        WHERE s.general_score >= 70
        ORDER BY s.general_score DESC, p.name
    ''')

    presenters_data = {}
    for row in cursor.fetchall():
        name = row['name']
        if name not in presenters_data:
            presenters_data[name] = {
                'name': name,
                'email': row['email'],
                'affiliation': row['affiliation'],
                'sessions': [],
                'max_session_score': 0,
                'topics': set()
            }

        session_info = {
            'title': row['session_title'],
            'date': row['date'],
            'time': row['start_time'],
            'general_score': row['general_score'],
            'max_score': row['max_score'],
            'pavel_score': row['pavel_score'],
            'daphne_score': row['daphne_score']
        }

        presenters_data[name]['sessions'].append(session_info)
        presenters_data[name]['max_session_score'] = max(
            presenters_data[name]['max_session_score'],
            row['general_score']
        )

        # Extract topics from title
        title_lower = row['session_title'].lower()
        if 'tax' in title_lower or 'ctc' in title_lower or 'eitc' in title_lower:
            presenters_data[name]['topics'].add('Tax Policy')
        if 'poverty' in title_lower:
            presenters_data[name]['topics'].add('Poverty')
        if 'snap' in title_lower or 'wic' in title_lower:
            presenters_data[name]['topics'].add('Benefit Programs')
        if 'medicaid' in title_lower or 'medicare' in title_lower:
            presenters_data[name]['topics'].add('Health Policy')
        if 'microsimulation' in title_lower or 'modeling' in title_lower:
            presenters_data[name]['topics'].add('Microsimulation')
        if 'housing' in title_lower:
            presenters_data[name]['topics'].add('Housing')

    conn.close()

    # Convert to list and sort by relevance
    presenters_list = list(presenters_data.values())
    for p in presenters_list:
        p['topics'] = list(p['topics'])

    presenters_list.sort(key=lambda x: x['max_session_score'], reverse=True)

    return presenters_list


def generate_networking_report():
    """Generate networking recommendations by person."""
    presenters = get_networking_recommendations()

    # Categorize by person
    for person_name, score_key in [
        ('Max Ghenis', 'max_score'),
        ('Pavel Makarchuk', 'pavel_score'),
        ('Daphne Hansell', 'daphne_score')
    ]:
        print(f"\n{'='*80}")
        print(f"NETWORKING RECOMMENDATIONS FOR {person_name.upper()}")
        print(f"{'='*80}\n")

        # Get presenters from sessions highly relevant to this person
        relevant_presenters = []
        for presenter in presenters:
            max_person_score = max([s[score_key] for s in presenter['sessions']])
            if max_person_score >= 75:
                presenter['person_score'] = max_person_score
                relevant_presenters.append(presenter)

        relevant_presenters.sort(key=lambda x: x['person_score'], reverse=True)

        print(f"Top {min(20, len(relevant_presenters))} presenters to connect with:\n")

        for i, presenter in enumerate(relevant_presenters[:20], 1):
            print(f"{i}. {presenter['name']}")
            if presenter['affiliation']:
                print(f"   Affiliation: {presenter['affiliation']}")
            if presenter['email']:
                print(f"   Email: {presenter['email']}")
            print(f"   Topics: {', '.join(presenter['topics'])}")
            print(f"   Relevance score: {presenter['person_score']:.0f}")
            print(f"   Sessions:")
            for session in presenter['sessions'][:2]:  # Show top 2 sessions
                print(f"     - {session['title'][:60]}...")
                print(f"       {session['date']} {session['time']}")
            print()

    # Export to JSON
    with open('public/data/networking.json', 'w') as f:
        json.dump(presenters, f, indent=2)

    print(f"\n✓ Exported networking recommendations to public/data/networking.json")


if __name__ == '__main__':
    generate_networking_report()
