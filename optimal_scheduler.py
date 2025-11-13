"""
Optimal scheduler with booth value scoring.

Maximizes total value considering:
1. Value of attending sessions (based on person scores)
2. Value of booth coverage (with diminishing returns)
"""
import sqlite3
from collections import defaultdict


class OptimalScheduler:
    def __init__(self, db_path='appam_sessions.db'):
        self.db_path = db_path
        self.people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell']

        # Arrival constraints
        self.arrival_times = {
            'Max Ghenis': ('2025-11-13', '11:30am'),
            'Pavel Makarchuk': None,
            'Daphne Hansell': None
        }

        # Lunch break times (prefer at least one person free for lunch)
        # 12:00pm-1:30pm each day
        self.lunch_times = [
            ('2025-11-13', '12:00pm', '1:30pm'),
            ('2025-11-14', '12:00pm', '1:30pm'),
            ('2025-11-15', '12:00pm', '1:30pm'),
        ]

        # Booth value by number of people staffing it
        # 0 people = -100 (unacceptable)
        # 1 person = 0 (baseline - requirement met)
        # 2 people = +20 (some networking value, but could be at sessions)
        # 3 people = +25 (minimal additional value)
        self.booth_value = {
            0: -1000,  # NEVER allow empty booth
            1: 0,      # Baseline - requirement met
            2: 20,     # Some value (can engage visitors better)
            3: 25      # Minimal additional value (overkill)
        }

    def is_available(self, person, date, start_time):
        """Check if person is available."""
        if self.arrival_times.get(person) is None:
            return True

        from datetime import datetime
        arrival_date, arrival_time = self.arrival_times[person]

        try:
            session_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %I:%M%p")
            arrival_dt = datetime.strptime(f"{arrival_date} {arrival_time}", "%Y-%m-%d %I:%M%p")
            return session_dt >= arrival_dt
        except:
            return True

    def get_time_slots(self):
        """Get all unique time slots."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT date, start_time, end_time
            FROM sessions
            WHERE date != '' AND start_time != ''
            ORDER BY date, start_time
        ''')

        slots = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return slots

    def get_sessions_for_slot(self, date, start_time, end_time):
        """Get all sessions for a time slot with scores."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT session_id, title, date, start_time, end_time, location,
                   general_score, max_score, pavel_score, daphne_score
            FROM sessions
            WHERE date = ? AND start_time = ? AND end_time = ?
            ORDER BY general_score DESC
        ''', (date, start_time, end_time))

        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions

    def calculate_slot_value(self, slot_assignment):
        """
        Calculate total value for a time slot assignment.

        slot_assignment = {
            'Max Ghenis': session_dict or None,
            'Pavel Makarchuk': session_dict or None,
            'Daphne Hansell': session_dict or None
        }
        """
        # Count people at booth vs sessions
        people_at_sessions = sum(1 for s in slot_assignment.values() if s is not None)
        people_at_booth = 3 - people_at_sessions

        # Booth value
        booth_val = self.booth_value[people_at_booth]

        # Session attendance value
        session_val = 0
        for person, session in slot_assignment.items():
            if session:
                # Use person-specific score
                person_key = f"{person.split(' ')[0].lower()}_score"
                person_score = session.get(person_key, session.get('general_score', 0))
                session_val += person_score

        total_value = booth_val + session_val

        return {
            'total': total_value,
            'booth_value': booth_val,
            'session_value': session_val,
            'people_at_booth': people_at_booth,
            'people_at_sessions': people_at_sessions
        }

    def assign_slot_optimal(self, date, start_time, end_time, sessions):
        """
        Find optimal assignment for one time slot.

        Returns best assignment and its value score.
        """
        # Get available people for this slot
        available_people = [p for p in self.people if self.is_available(p, date, start_time)]

        if not available_people:
            # No one available - skip
            return {}, {'total': -1000}

        # Try all possible assignments
        best_assignment = {}
        best_value = {'total': -1000}

        # Generate all possible assignments
        # For 3 people and N sessions, we try:
        # - 0 people at sessions (all at booth)
        # - 1 person at sessions (2 at booth)
        # - 2 people at sessions (1 at booth)

        from itertools import combinations

        # Option 1: Everyone at booth (valid but low value if good sessions exist)
        assignment = {p: None for p in self.people}
        value = self.calculate_slot_value(assignment)
        if value['total'] > best_value['total']:
            best_assignment = assignment.copy()
            best_value = value

        # Option 2: Send 1 person to best session
        if sessions:
            for person in available_people:
                # Find best session for this person
                person_key = f"{person.split(' ')[0].lower()}_score"
                best_session = max(sessions, key=lambda s: s.get(person_key, s.get('general_score', 0)))

                assignment = {p: None for p in self.people}
                assignment[person] = best_session

                value = self.calculate_slot_value(assignment)
                if value['total'] > best_value['total']:
                    best_assignment = assignment.copy()
                    best_value = value

        # Option 3: Send 2 people to different sessions (if multiple good sessions)
        if len(sessions) >= 2 and len(available_people) >= 2:
            for person_pair in combinations(available_people, 2):
                # Assign each person to their best session
                assignment = {p: None for p in self.people}

                for i, person in enumerate(person_pair):
                    person_key = f"{person.split(' ')[0].lower()}_score"

                    # Find best unassigned session
                    assigned_sessions = [assignment[person_pair[j]] for j in range(i) if assignment.get(person_pair[j])]
                    available_sessions = [s for s in sessions if s not in assigned_sessions]

                    if available_sessions:
                        best_session = max(available_sessions,
                                         key=lambda s: s.get(person_key, s.get('general_score', 0)))
                        assignment[person] = best_session

                value = self.calculate_slot_value(assignment)
                if value['total'] > best_value['total']:
                    best_assignment = assignment.copy()
                    best_value = value

        return best_assignment, best_value

    def optimize_schedule(self):
        """Create optimal schedule for all time slots."""
        # Clear assignments first
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET assigned_to = NULL')
        conn.commit()
        conn.close()

        time_slots = self.get_time_slots()

        all_assignments = []
        total_value = 0

        print("="*80)
        print("OPTIMIZING SCHEDULE WITH BOOTH VALUE")
        print("="*80)
        print(f"\nBooth value scoring:")
        print(f"  0 people: {self.booth_value[0]} (UNACCEPTABLE)")
        print(f"  1 person: {self.booth_value[1]} (baseline)")
        print(f"  2 people: +{self.booth_value[2]} bonus")
        print(f"  3 people: +{self.booth_value[3]} bonus\n")

        for slot in time_slots:
            date = slot['date']
            start_time = slot['start_time']
            end_time = slot['end_time']

            sessions = self.get_sessions_for_slot(date, start_time, end_time)

            if not sessions:
                continue

            # Find optimal assignment
            assignment, value = self.assign_slot_optimal(date, start_time, end_time, sessions)

            all_assignments.append({
                'slot': f"{date} {start_time}",
                'assignment': assignment,
                'value': value
            })

            total_value += value['total']

            # Print high-value slots
            if value['session_value'] > 150 or value['people_at_sessions'] >= 2:
                print(f"{date} {start_time}-{end_time}")
                print(f"  Value: {value['total']:.0f} (Booth: {value['booth_value']:+.0f}, Sessions: {value['session_value']:.0f})")
                print(f"  Booth: {value['people_at_booth']} person(s), Sessions: {value['people_at_sessions']}")
                for person, session in assignment.items():
                    if session:
                        person_key = f"{person.split(' ')[0].lower()}_score"
                        score = session.get(person_key, 0)
                        print(f"    {person.split(' ')[0]}: {session['title'][:50]}... (score: {score:.0f})")
                print()

        # Save all assignments to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for slot_data in all_assignments:
            for person, session in slot_data['assignment'].items():
                if session:
                    cursor.execute('''
                        UPDATE sessions
                        SET assigned_to = ?
                        WHERE session_id = ?
                    ''', (person, session['session_id']))

        conn.commit()
        conn.close()

        print(f"\nTotal schedule value: {total_value:.0f}")

        # Summary
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for person in self.people:
            cursor.execute('SELECT COUNT(*) FROM sessions WHERE assigned_to = ?', (person,))
            count = cursor.fetchone()[0]
            print(f"  {person}: {count} sessions")

        conn.close()

        return all_assignments


if __name__ == '__main__':
    scheduler = OptimalScheduler()
    assignments = scheduler.optimize_schedule()

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print("\nRun: uv run python export_to_json.py")
    print("Then: npm run build && git add -A && git commit && git push")
