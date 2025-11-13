"""
Export schedule in proper format: time_slots -> person assignments
"""
import sqlite3
import json
from datetime import datetime


def parse_time_for_sort(date_str, time_str):
    """Parse time for sorting."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M%p")
        return dt
    except:
        return datetime.min


def export_slot_schedule():
    """Export schedule organized by time slots."""
    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all unique time slots
    cursor.execute('''
        SELECT DISTINCT date, start_time, end_time
        FROM sessions
        WHERE date != '' AND start_time != ''
        ORDER BY date, start_time
    ''')

    time_slots = []
    people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell']

    for slot_row in cursor.fetchall():
        date = slot_row['date']
        start_time = slot_row['start_time']
        end_time = slot_row['end_time']

        # Get all sessions for this time slot
        cursor.execute('''
            SELECT session_id, title, location, assigned_to,
                   general_score, max_score, pavel_score, daphne_score
            FROM sessions
            WHERE date = ? AND start_time = ? AND end_time = ?
        ''', (date, start_time, end_time))

        sessions_at_slot = [dict(row) for row in cursor.fetchall()]

        # Build assignments for this slot
        slot_data = {
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'assignments': {},
            'available_sessions': []
        }

        # Check who's assigned to what
        assigned_people = set()
        for session in sessions_at_slot:
            if session['assigned_to']:
                person = session['assigned_to']
                assigned_people.add(person)

                # Only assign if person doesn't already have a session this slot
                if person not in slot_data['assignments']:
                    slot_data['assignments'][person] = {
                        'type': 'session',
                        'session_id': session['session_id'],
                        'title': session['title'],
                        'location': session['location'],
                        'general_score': session['general_score'] or 0,
                        'person_score': session.get(f"{person.split(' ')[0].lower()}_score", 0) or 0
                    }

        # Everyone not assigned to a session is at booth
        for person in people:
            if person not in slot_data['assignments']:
                slot_data['assignments'][person] = {
                    'type': 'booth',
                    'location': 'Exhibit Booth'
                }

        # Add top 5 available sessions for reference
        unassigned_sessions = [s for s in sessions_at_slot if not s['assigned_to']]
        unassigned_sessions.sort(key=lambda x: x['general_score'] or 0, reverse=True)

        for session in unassigned_sessions[:5]:
            slot_data['available_sessions'].append({
                'session_id': session['session_id'],
                'title': session['title'],
                'general_score': session['general_score'] or 0,
                'scores': {
                    'max': session['max_score'] or 0,
                    'pavel': session['pavel_score'] or 0,
                    'daphne': session['daphne_score'] or 0
                }
            })

        # Calculate booth coverage
        booth_count = sum(1 for a in slot_data['assignments'].values() if a['type'] == 'booth')
        slot_data['booth_coverage'] = {
            'count': booth_count,
            'people': [p for p, a in slot_data['assignments'].items() if a['type'] == 'booth']
        }

        time_slots.append(slot_data)

    # Sort chronologically
    time_slots.sort(key=lambda x: parse_time_for_sort(x['date'], x['start_time']))

    # Save to file
    with open('public/data/team_schedule.json', 'w') as f:
        json.dump(time_slots, f, indent=2)

    conn.close()

    # Print summary
    print("="*80)
    print("SLOT-BASED SCHEDULE EXPORT")
    print("="*80)
    print()

    for person in people:
        session_count = sum(1 for slot in time_slots
                           if slot['assignments'].get(person, {}).get('type') == 'session')
        booth_count = sum(1 for slot in time_slots
                         if slot['assignments'].get(person, {}).get('type') == 'booth')

        print(f"{person}:")
        print(f"  Sessions: {session_count}")
        print(f"  Booth shifts: {booth_count}")
        print()

    # Show slots with 0 or 3 people at booth
    print("Special booth coverage situations:")
    for slot in time_slots:
        booth_count = slot['booth_coverage']['count']
        if booth_count == 0:
            print(f"  ⚠️  {slot['date']} {slot['start_time']}: NO ONE at booth (all at sessions)")
        elif booth_count == 3:
            print(f"  ⚪ {slot['date']} {slot['start_time']}: ALL at booth (no valuable sessions)")

    print(f"\n✓ Exported to public/data/team_schedule.json")


if __name__ == '__main__':
    export_slot_schedule()
