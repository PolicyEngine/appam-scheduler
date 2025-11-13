"""
Smart re-scoring using LLM to read and understand session content.
Takes top sessions from keyword scoring and re-scores based on actual relevance.
"""
import sqlite3
import json


def get_top_sessions_for_review(db_path='appam_sessions.db', limit=100):
    """Get top sessions from keyword scoring for manual review."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT session_id, title, description, date, start_time, end_time,
               location, chair, papers, relevance_score
        FROM sessions
        WHERE relevance_score > 5
        ORDER BY relevance_score DESC
        LIMIT ?
    ''', (limit,))

    sessions = []
    for row in cursor.fetchall():
        session = dict(row)
        if session['papers']:
            try:
                session['papers'] = json.loads(session['papers'])
            except:
                session['papers'] = []
        sessions.append(session)

    conn.close()
    return sessions


def save_smart_scores(session_scores, db_path='appam_sessions.db'):
    """Save the manually reviewed scores."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add a smart_score column if it doesn't exist
    cursor.execute('''
        SELECT COUNT(*) FROM pragma_table_info('sessions')
        WHERE name='smart_score'
    ''')

    if cursor.fetchone()[0] == 0:
        cursor.execute('ALTER TABLE sessions ADD COLUMN smart_score REAL DEFAULT 0')

    # Update scores
    for session_id, score, rationale in session_scores:
        cursor.execute('''
            UPDATE sessions
            SET smart_score = ?
            WHERE session_id = ?
        ''', (score, session_id))

    conn.commit()
    conn.close()


if __name__ == '__main__':
    sessions = get_top_sessions_for_review(limit=100)

    print(f"Found {len(sessions)} sessions for smart re-scoring")
    print("\nSample sessions to review:")
    for i, s in enumerate(sessions[:10], 1):
        print(f"{i}. [{s['relevance_score']}] {s['title'][:80]}")

    print("\n" + "="*80)
    print("INSTRUCTIONS FOR CLAUDE:")
    print("="*80)
    print("""
For each session, rate 0-100 based on PolicyEngine relevance:

HIGH RELEVANCE (70-100):
- Tax-benefit microsimulation methodology
- Tax policy reform (especially credits: CTC, EITC)
- Health policy (Medicaid, Medicare, ACA)
- Poverty measurement and analysis
- Benefit programs (SNAP, WIC, TANF, SSI)
- Universal basic income / guaranteed income
- Distributional analysis / inequality

MEDIUM RELEVANCE (40-69):
- Related but not core (housing, education, labor)
- Data/methodology useful for microsimulation
- Adjacent policy areas with poverty impacts

LOW RELEVANCE (0-39):
- Tangentially related or not relevant to PolicyEngine

Consider:
- Are the methods/data applicable to microsimulation?
- Would PolicyEngine team learn useful techniques?
- Are there networking opportunities with relevant researchers?
- Does it inform current PolicyEngine work?
    """)

    print("\nReady for Claude to score these sessions...")
