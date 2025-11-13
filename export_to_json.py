"""
Export database to JSON for static site deployment.
"""
import sqlite3
import json
from pathlib import Path


def export_database(db_path='appam_sessions.db', output_dir='public/data'):
    """Export all database tables to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Export sessions with full details
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            s.session_id,
            s.title,
            s.date,
            s.start_time,
            s.end_time,
            s.location,
            s.description,
            s.chair,
            s.papers,
            s.relevance_score,
            s.assigned_to,
            s.general_score,
            s.max_score,
            s.pavel_score,
            s.daphne_score
        FROM sessions s
        ORDER BY s.date, s.start_time
    ''')

    sessions = []
    for row in cursor.fetchall():
        session = dict(row)

        # Parse papers JSON
        if session['papers']:
            try:
                session['papers'] = json.loads(session['papers'])
            except:
                session['papers'] = []

        # Add recommended attendees based on person scores
        recommended = []
        if session.get('max_score', 0) >= 85:
            recommended.append('Max Ghenis')
        if session.get('pavel_score', 0) >= 85:
            recommended.append('Pavel Makarchuk')
        if session.get('daphne_score', 0) >= 85:
            recommended.append('Daphne Hansell')
        session['recommended_for'] = recommended

        # Get presenters for this session
        cursor.execute('''
            SELECT p.id, p.name, p.email, p.affiliation
            FROM presenters p
            JOIN session_presenters sp ON p.id = sp.presenter_id
            WHERE sp.session_id = ?
            ORDER BY p.name
        ''', (session['session_id'],))

        session['presenters'] = [dict(p) for p in cursor.fetchall()]

        sessions.append(session)

    # Write sessions
    with open(output_path / 'sessions.json', 'w') as f:
        json.dump(sessions, f, indent=2)

    print(f"✓ Exported {len(sessions)} sessions to {output_path / 'sessions.json'}")

    # Export presenters
    cursor.execute('''
        SELECT id, name, email, affiliation, notes
        FROM presenters
        ORDER BY name
    ''')

    presenters = [dict(row) for row in cursor.fetchall()]

    # Add session count for each presenter
    for presenter in presenters:
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM session_presenters
            WHERE presenter_id = ?
        ''', (presenter['id'],))
        presenter['session_count'] = cursor.fetchone()[0]

    with open(output_path / 'presenters.json', 'w') as f:
        json.dump(presenters, f, indent=2)

    print(f"✓ Exported {len(presenters)} presenters to {output_path / 'presenters.json'}")

    # Export schedule (assigned sessions by person)
    cursor.execute('''
        SELECT DISTINCT assigned_to
        FROM sessions
        WHERE assigned_to IS NOT NULL
    ''')

    people = [row[0] for row in cursor.fetchall()]
    schedule = {}

    for person in people:
        cursor.execute('''
            SELECT
                session_id,
                title,
                date,
                start_time,
                end_time,
                location,
                relevance_score
            FROM sessions
            WHERE assigned_to = ?
            ORDER BY date, start_time
        ''', (person,))

        schedule[person] = [dict(row) for row in cursor.fetchall()]

    with open(output_path / 'schedule.json', 'w') as f:
        json.dump(schedule, f, indent=2)

    print(f"✓ Exported schedule for {len(people)} people to {output_path / 'schedule.json'}")

    # Export locations
    cursor.execute('''
        SELECT l.id, l.name, l.building, l.capacity,
               COUNT(s.session_id) as session_count
        FROM locations l
        LEFT JOIN sessions s ON s.location = l.name
        GROUP BY l.id, l.name
        ORDER BY l.name
    ''')

    locations = [dict(row) for row in cursor.fetchall()]

    with open(output_path / 'locations.json', 'w') as f:
        json.dump(locations, f, indent=2)

    print(f"✓ Exported {len(locations)} locations to {output_path / 'locations.json'}")

    # Export time slots
    cursor.execute('''
        SELECT DISTINCT date, start_time, end_time
        FROM sessions
        WHERE date != ''
        ORDER BY date, start_time
    ''')

    time_slots = [dict(row) for row in cursor.fetchall()]

    with open(output_path / 'time_slots.json', 'w') as f:
        json.dump(time_slots, f, indent=2)

    print(f"✓ Exported {len(time_slots)} time slots to {output_path / 'time_slots.json'}")

    # Export statistics
    cursor.execute('SELECT COUNT(*) as total FROM sessions')
    total_sessions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) as assigned FROM sessions WHERE assigned_to IS NOT NULL')
    assigned_sessions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) as high_value FROM sessions WHERE relevance_score >= 20')
    high_value_sessions = cursor.fetchone()[0]

    cursor.execute('''
        SELECT assigned_to, COUNT(*) as count
        FROM sessions
        WHERE assigned_to IS NOT NULL
        GROUP BY assigned_to
    ''')
    per_person = {row[0]: row[1] for row in cursor.fetchall()}

    stats = {
        'total_sessions': total_sessions,
        'assigned_sessions': assigned_sessions,
        'high_value_sessions': high_value_sessions,
        'per_person': per_person,
        'total_presenters': len(presenters),
        'total_locations': len(locations)
    }

    with open(output_path / 'stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"✓ Exported statistics to {output_path / 'stats.json'}")

    conn.close()

    print(f"\n✓ Export complete! All data exported to {output_path}")


if __name__ == '__main__':
    export_database()
