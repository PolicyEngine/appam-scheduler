"""
Create final curated schedule - one session per person per time slot.
Manual curation of must-attend sessions.
"""
import sqlite3
import json


def create_final_schedule():
    """Create the final team schedule."""
    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Clear all assignments
    cursor.execute('UPDATE sessions SET assigned_to = NULL')

    # Define the schedule
    # Format: (session_id_or_title, person, priority)
    schedule_assignments = [
        # THURSDAY Nov 13
        ('2268355', 'Pavel Makarchuk'),  # Tax Policy 10:15am
        ('2268242', 'Daphne Hansell'),   # Big Data Health 10:15am
        # Max at booth 10:15am (not arrived yet)

        ('2258530', 'Max Ghenis'),       # CTC/EITC 1:45pm - BOTH Max & Pavel
        ('2258530', 'Pavel Makarchuk'),  # CTC/EITC 1:45pm
        ('2257840', 'Daphne Hansell'),   # Medicaid School 1:45pm
        # Max at booth (actually Max at CTC/EITC)

        ('2260802', 'Daphne Hansell'),   # Medicaid Dental 8:30am
        # Pavel & Max at booth

        # FRIDAY Nov 14
        ('2259458', 'Pavel Makarchuk'),  # SNAP/WIC Access 8:30am
        ('2258250', 'Daphne Hansell'),   # Housing Ed Inequality 8:30am
        # Max at booth

        ('2258670', 'Daphne Hansell'),   # Access to Health Care 10:15am
        # Max & Pavel at booth

        ('2257105', 'Max Ghenis'),       # Tax Credits & Transfers 1:45pm
        ('2257105', 'Pavel Makarchuk'),  # Tax Credits & Transfers 1:45pm - BOTH
        # Daphne at booth

        ('2268961', 'Max Ghenis'),       # SNAP Work Requirements 3:30pm
        ('2309265', 'Daphne Hansell'),   # Health Policy Lightning 3:30pm
        # Pavel at booth

        # SATURDAY Nov 15
        ('2259416', 'Max Ghenis'),       # Understanding SNAP 8:30am
        # Pavel & Daphne at booth

        ('2260094', 'Max Ghenis'),       # Poverty Measurement 10:15am - ALL THREE
        ('2260094', 'Pavel Makarchuk'),  # Poverty Measurement 10:15am
        ('2260094', 'Daphne Hansell'),   # Poverty Measurement 10:15am
        # All at session - booth empty for this critical session

        ('2304571', 'Daphne Hansell'),   # State SNAP/Medicaid 1:45pm
        ('2258296', 'Pavel Makarchuk'),  # Housing Tax Credit 1:45pm
        # Max at booth

        ('2257650', 'Max Ghenis'),       # Transforming WIC 3:30pm
        ('2260757', 'Daphne Hansell'),   # Health Policy Tracking 3:30pm
        # Pavel at booth
    ]

    # Track what we've assigned
    assigned_count = {}

    for item in schedule_assignments:
        if len(item) == 2:
            session_id, person = item

            # Find the session
            cursor.execute('SELECT session_id, title FROM sessions WHERE session_id = ?', (session_id,))
            session = cursor.fetchone()

            if session:
                # Since assigned_to can only hold one person, we'll use a marker
                # For multi-person sessions, we'll just assign to first person
                # and track separately
                current_assigned = cursor.execute(
                    'SELECT assigned_to FROM sessions WHERE session_id = ?',
                    (session_id,)
                ).fetchone()

                if current_assigned and current_assigned[0]:
                    # Already assigned - this is a multi-person session
                    # Mark it somehow
                    pass
                else:
                    cursor.execute(
                        'UPDATE sessions SET assigned_to = ? WHERE session_id = ?',
                        (person, session_id)
                    )

                # Track for reporting
                key = f"{person}_{session_id}"
                if key not in assigned_count:
                    assigned_count[key] = 1

    conn.commit()

    # Generate summary
    print("="*80)
    print("FINAL CURATED SCHEDULE")
    print("="*80)
    print()

    for person in ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell']:
        cursor.execute('''
            SELECT DISTINCT s.date, s.start_time, s.title, s.general_score
            FROM sessions s
            WHERE s.assigned_to = ? OR s.session_id IN (
                SELECT session_id FROM sessions WHERE assigned_to = ?
            )
            ORDER BY s.date, s.start_time
        ''', (person, person))

        sessions = cursor.fetchall()

        # Count unique time slots
        time_slots = set((s['date'], s['start_time']) for s in sessions)

        print(f"{person}: {len(time_slots)} time slots")

    conn.close()

    # Also check multi-person sessions
    cursor = conn.cursor()
    multi_sessions = [
        '2258530',  # CTC/EITC - Max & Pavel
        '2257105',  # Tax Credits - Max & Pavel
        '2260094',  # Poverty Measurement - ALL THREE
    ]

    print("\nMulti-person sessions:")
    for sid in multi_sessions:
        cursor.execute('SELECT title FROM sessions WHERE session_id = ?', (sid,))
        result = cursor.fetchone()
        if result:
            print(f"  - {result[0]}")

    print("\n✓ Schedule created. Run export_to_json.py to save.")


if __name__ == '__main__':
    create_final_schedule()
