"""
Conference Scheduler
Assigns people to sessions while ensuring booth coverage.
"""
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from relevance_scorer import RelevanceScorer


class ConferenceScheduler:
    def __init__(self, db_path='appam_sessions.db'):
        self.db_path = db_path
        self.scorer = RelevanceScorer(db_path)
        self.people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell']

        # Arrival times (None means available from start)
        self.arrival_times = {
            'Max Ghenis': ('2025-11-13', '11:30am'),  # Arrives 11:30am Thursday
            'Pavel Makarchuk': None,  # Available from start
            'Daphne Hansell': None    # Available from start
        }

    def is_available(self, person, date, start_time):
        """Check if a person is available for a session at given date/time."""
        if self.arrival_times.get(person) is None:
            return True

        arrival_date, arrival_time = self.arrival_times[person]

        # Convert to datetime for comparison
        try:
            session_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %I:%M%p")
            arrival_dt = datetime.strptime(f"{arrival_date} {arrival_time}", "%Y-%m-%d %I:%M%p")
            return session_dt >= arrival_dt
        except:
            return True  # If parsing fails, assume available

    def parse_time(self, date_str, time_str):
        """Parse date and time strings into datetime object."""
        try:
            # Combine date and time
            datetime_str = f"{date_str} {time_str}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %I:%M %p")
        except Exception as e:
            print(f"Error parsing time: {date_str} {time_str} - {e}")
            return None

    def get_time_slots(self):
        """Get all unique time slots from sessions."""
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
        """Get all sessions for a specific time slot."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT *
            FROM sessions
            WHERE date = ? AND start_time = ? AND end_time = ?
            ORDER BY relevance_score DESC
        ''', (date, start_time, end_time))

        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return sessions

    def assign_sessions(self, strategy='greedy'):
        """
        Assign people to sessions using specified strategy.

        Strategies:
        - greedy: Assign highest-scoring sessions first, ensuring booth coverage
        - balanced: Try to balance workload across people
        - personalized: Assign based on person-specific relevance scores
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear previous assignments
        cursor.execute('UPDATE sessions SET assigned_to = NULL')
        conn.commit()

        # Get all time slots
        time_slots = self.get_time_slots()

        assignments = defaultdict(list)  # person -> list of sessions
        booth_coverage = {}  # time_slot -> person at booth

        for slot in time_slots:
            date = slot['date']
            start_time = slot['start_time']
            end_time = slot['end_time']
            slot_key = f"{date} {start_time}"

            sessions = self.get_sessions_for_slot(date, start_time, end_time)

            if not sessions:
                continue

            # Determine who attends which session
            # We need to ensure at least one person is at the booth
            session_assignments = {}  # session_id -> person

            if strategy == 'personalized':
                # Score each session for each person
                person_session_scores = {}
                for person in self.people:
                    person_session_scores[person] = []
                    for session in sessions:
                        score_result = self.scorer.score_for_person(session, person)
                        person_session_scores[person].append({
                            'session_id': session['session_id'],
                            'title': session['title'],
                            'score': score_result['score'],
                            'session': session
                        })
                    # Sort by score
                    person_session_scores[person].sort(key=lambda x: x['score'], reverse=True)

                # Assign top session for each person, ensuring booth coverage
                # With 3 people, we can send up to 2 to sessions (1 at booth)
                num_to_assign = min(len(sessions), 2)  # At most 2 people to sessions

                assigned_people = set()
                assigned_sessions = set()

                # Create a list of (person, session, score) tuples
                potential_assignments = []
                for person in self.people:
                    # Check if person is available for this time slot
                    if not self.is_available(person, date, start_time):
                        continue

                    if person_session_scores[person]:
                        top_session = person_session_scores[person][0]
                        potential_assignments.append((
                            person,
                            top_session['session'],
                            top_session['score']
                        ))

                # Sort by score and assign
                potential_assignments.sort(key=lambda x: x[2], reverse=True)

                for person, session, score in potential_assignments[:num_to_assign]:
                    if person not in assigned_people and session['session_id'] not in assigned_sessions:
                        if score >= 5:  # Only assign if reasonably relevant
                            session_assignments[session['session_id']] = person
                            assigned_people.add(person)
                            assigned_sessions.add(session['session_id'])
                            assignments[person].append(session)

                # Assign remaining person to booth
                booth_person = [p for p in self.people if p not in assigned_people][0]
                booth_coverage[slot_key] = booth_person

            elif strategy == 'greedy':
                # Simple greedy: assign top sessions to anyone available
                num_to_assign = min(len(sessions), 2)
                for i, session in enumerate(sessions[:num_to_assign]):
                    if session['relevance_score'] >= 5:
                        # Assign to least busy person
                        person_loads = {p: len(assignments[p]) for p in self.people}
                        least_busy = min(person_loads, key=person_loads.get)
                        session_assignments[session['session_id']] = least_busy
                        assignments[least_busy].append(session)

                # Booth coverage
                assigned = set(session_assignments.values())
                booth_person = [p for p in self.people if p not in assigned][0]
                booth_coverage[slot_key] = booth_person

            # Save assignments to database
            for session_id, person in session_assignments.items():
                cursor.execute('''
                    UPDATE sessions
                    SET assigned_to = ?
                    WHERE session_id = ?
                ''', (person, session_id))

        conn.commit()
        conn.close()

        return {
            'assignments': dict(assignments),
            'booth_coverage': booth_coverage
        }

    def generate_schedule_summary(self):
        """Generate a summary of the schedule."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all assigned sessions
        cursor.execute('''
            SELECT assigned_to, date, start_time, end_time, title, location, relevance_score
            FROM sessions
            WHERE assigned_to IS NOT NULL
            ORDER BY date, start_time, assigned_to
        ''')

        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Organize by person and date
        schedule = defaultdict(lambda: defaultdict(list))
        for session in sessions:
            person = session['assigned_to']
            date = session['date']
            schedule[person][date].append(session)

        return schedule

    def print_schedule(self):
        """Print a formatted schedule."""
        schedule = self.generate_schedule_summary()

        print("\n" + "=" * 80)
        print(" " * 25 + "APPAM CONFERENCE SCHEDULE")
        print("=" * 80)

        for person in self.people:
            print(f"\n{'=' * 80}")
            print(f"  {person}")
            print(f"{'=' * 80}")

            person_schedule = schedule.get(person, {})
            if not person_schedule:
                print("  No sessions assigned")
                continue

            for date in sorted(person_schedule.keys()):
                print(f"\n  {date}")
                print(f"  {'-' * 76}")

                sessions = sorted(person_schedule[date], key=lambda x: x['start_time'])
                for session in sessions:
                    print(f"  {session['start_time']:>10} - {session['end_time']:<10}  [{session['relevance_score']:>5.1f}]")
                    print(f"    {session['title']}")
                    print(f"    Location: {session['location']}")
                    print()

        # Print booth coverage
        print(f"\n{'=' * 80}")
        print("  BOOTH COVERAGE")
        print(f"{'=' * 80}")

        result = self.assign_sessions('personalized')
        booth_coverage = result['booth_coverage']

        for slot_key in sorted(booth_coverage.keys()):
            person = booth_coverage[slot_key]
            print(f"  {slot_key}: {person}")

        print("\n" + "=" * 80)


if __name__ == '__main__':
    scheduler = ConferenceScheduler()

    print("Assigning sessions with personalized strategy...")
    result = scheduler.assign_sessions(strategy='personalized')

    print("\nSchedule Summary:")
    print(f"  Total sessions assigned: {sum(len(sessions) for sessions in result['assignments'].values())}")
    for person, sessions in result['assignments'].items():
        print(f"  {person}: {len(sessions)} sessions")

    scheduler.print_schedule()
