"""
Session Relevance Scoring
Scores conference sessions based on relevance to PolicyEngine's work.
"""
import sqlite3
import json
import re


class RelevanceScorer:
    def __init__(self, db_path='appam_sessions.db'):
        self.db_path = db_path

        # Keywords and their weights for PolicyEngine's core work areas
        self.keywords = {
            # Core tax-benefit microsimulation terms (high weight)
            'microsimulation': 10,
            'tax policy': 10,
            'tax reform': 10,
            'benefit': 9,
            'welfare': 9,
            'social security': 9,
            'medicare': 9,
            'medicaid': 9,
            'snap': 9,
            'tanf': 9,
            'eitc': 9,
            'earned income tax credit': 9,
            'child tax credit': 9,
            'universal basic income': 9,
            'ubi': 9,
            'guaranteed income': 9,
            'tax credit': 8,
            'means-tested': 8,
            'poverty': 8,
            'inequality': 8,
            'redistribution': 8,
            'income distribution': 8,

            # Health policy (high weight for Daphne)
            'health policy': 10,
            'health insurance': 9,
            'health care': 9,
            'affordable care act': 9,
            'aca': 9,
            'health reform': 9,
            'health coverage': 8,
            'health equity': 8,
            'health economics': 8,
            'health outcomes': 7,

            # Policy analysis and modeling (medium-high weight)
            'policy simulation': 8,
            'policy analysis': 7,
            'policy modeling': 8,
            'behavioral response': 7,
            'distributional analysis': 8,
            'impact evaluation': 7,
            'cost-benefit': 6,

            # Data and methodology (medium weight)
            'administrative data': 6,
            'survey data': 5,
            'microdata': 7,
            'data linkage': 5,
            'machine learning': 4,
            'causal inference': 5,

            # Broader policy areas (medium-low weight)
            'education policy': 5,
            'housing policy': 5,
            'labor market': 5,
            'employment': 4,
            'family policy': 6,
            'child care': 6,
            'social policy': 6,
            'public assistance': 7,

            # Technology and tools (low-medium weight)
            'open source': 5,
            'data visualization': 4,
            'web application': 3,
            'policy tool': 6,
            'calculator': 5,

            # Related organizations/programs
            'congress': 4,
            'congressional budget office': 6,
            'cbo': 6,
            'treasury': 5,
            'irs': 5,
            'tax foundation': 4,
            'urban institute': 4,
        }

        # Person-specific interest modifiers
        self.person_interests = {
            'Max Ghenis': {
                'universal basic income': 2.0,
                'ubi': 2.0,
                'guaranteed income': 2.0,
                'poverty': 1.5,
                'child allowance': 1.8,
                'tax reform': 1.3,
            },
            'Pavel Makarchuk': {
                'microsimulation': 1.5,
                'tax policy': 1.3,
                'policy modeling': 1.4,
                'data visualization': 1.5,
                'behavioral response': 1.3,
            },
            'Daphne Hansell': {
                'health policy': 2.0,
                'health insurance': 2.0,
                'health care': 2.0,
                'medicaid': 1.8,
                'medicare': 1.8,
                'affordable care act': 1.8,
                'health reform': 1.8,
                'health equity': 1.7,
                'housing policy': 1.8,
                'housing': 1.5,
                'transportation policy': 1.5,
                'land use': 1.5,
                'zoning': 1.5,
            }
        }

    def score_session(self, session_data):
        """Calculate relevance score for a session."""
        # Combine all text fields
        text_fields = [
            session_data.get('title', ''),
            session_data.get('description', ''),
            session_data.get('chair', ''),
        ]

        # Add papers if they exist
        papers = session_data.get('papers', '')
        if papers:
            try:
                paper_list = json.loads(papers) if isinstance(papers, str) else papers
                text_fields.extend(paper_list)
            except:
                text_fields.append(str(papers))

        # Combine and lowercase all text
        full_text = ' '.join(text_fields).lower()

        # Calculate base score
        score = 0
        matched_keywords = []

        for keyword, weight in self.keywords.items():
            # Count occurrences (with diminishing returns)
            count = len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', full_text))
            if count > 0:
                # Diminishing returns: 1st occurrence full weight, 2nd half, 3rd third, etc.
                keyword_score = sum(weight / (i + 1) for i in range(min(count, 3)))
                score += keyword_score
                matched_keywords.append((keyword, count, keyword_score))

        # Bonus for title matches (title is more important)
        title = session_data.get('title', '').lower()
        for keyword, weight in self.keywords.items():
            if keyword.lower() in title:
                score += weight * 0.5  # 50% bonus for title appearance

        return {
            'score': round(score, 2),
            'matched_keywords': matched_keywords
        }

    def score_for_person(self, session_data, person_name):
        """Calculate personalized relevance score for a specific person."""
        base_result = self.score_session(session_data)
        base_score = base_result['score']

        # Apply person-specific modifiers
        if person_name not in self.person_interests:
            return base_result

        full_text = ' '.join([
            session_data.get('title', ''),
            session_data.get('description', ''),
        ]).lower()

        modifier = 1.0
        for keyword, multiplier in self.person_interests[person_name].items():
            if keyword.lower() in full_text:
                modifier = max(modifier, multiplier)

        personalized_score = base_score * modifier

        return {
            'score': round(personalized_score, 2),
            'base_score': base_score,
            'modifier': modifier,
            'matched_keywords': base_result['matched_keywords']
        }

    def score_all_sessions(self):
        """Score all sessions in the database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sessions')
        sessions = cursor.fetchall()

        print(f"Scoring {len(sessions)} sessions...")

        for session in sessions:
            session_dict = dict(session)
            result = self.score_session(session_dict)

            cursor.execute('''
                UPDATE sessions
                SET relevance_score = ?
                WHERE session_id = ?
            ''', (result['score'], session['session_id']))

            if result['score'] > 10:  # Show high-scoring sessions
                print(f"  High score ({result['score']}): {session['title'][:60]}...")

        conn.commit()
        conn.close()
        print("✓ Scoring complete!")

    def get_top_sessions(self, limit=20, person=None):
        """Get top-scored sessions, optionally filtered by person."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT session_id, title, date, start_time, end_time, location, relevance_score
            FROM sessions
            WHERE relevance_score > 0
            ORDER BY relevance_score DESC
            LIMIT ?
        ''', (limit,))

        sessions = cursor.fetchall()
        conn.close()

        return [dict(s) for s in sessions]


if __name__ == '__main__':
    scorer = RelevanceScorer()
    scorer.score_all_sessions()

    print("\n=== Top 20 Most Relevant Sessions ===")
    top_sessions = scorer.get_top_sessions(20)
    for i, session in enumerate(top_sessions, 1):
        print(f"{i}. [{session['relevance_score']}] {session['title']}")
        print(f"   {session['date']} {session['start_time']}-{session['end_time']} @ {session['location']}")
        print()
