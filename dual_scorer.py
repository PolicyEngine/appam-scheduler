"""
Dual scoring system:
1. General score - how relevant is this to PolicyEngine overall?
2. Person-specific scores - how relevant for each team member?
"""
import sqlite3
import json


def add_score_columns():
    """Add new scoring columns to database."""
    conn = sqlite3.connect('appam_sessions.db')
    cursor = conn.cursor()

    # Check if columns exist
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]

    new_columns = {
        'general_score': 'REAL DEFAULT 0',
        'max_score': 'REAL DEFAULT 0',
        'pavel_score': 'REAL DEFAULT 0',
        'daphne_score': 'REAL DEFAULT 0'
    }

    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            cursor.execute(f'ALTER TABLE sessions ADD COLUMN {col_name} {col_type}')
            print(f"Added column: {col_name}")

    conn.commit()
    conn.close()


def score_session_for_policyengine(session):
    """
    Score session for overall PolicyEngine relevance (0-100).

    Returns: (score, rationale)
    """
    title = session['title'].lower()
    desc = (session.get('description') or '').lower()[:2000]
    text = f"{title} {desc}"

    # MUST ATTEND (90-100)
    if 'microsimulation' in text:
        return (100, "Microsimulation methodology - core PolicyEngine work")

    if ('ctc' in text or 'child tax credit' in text) and ('poverty' in text or 'eitc' in text):
        return (95, "CTC/EITC analysis - PolicyEngine's primary policy area")

    if 'poverty' in text and 'measurement' in text:
        return (95, "Poverty measurement - critical for impact calculations")

    # HIGHLY RELEVANT (75-89)
    if 'snap' in text and ('work requirement' in text or 'eligibility' in text or 'take-up' in text):
        return (85, "SNAP policy analysis - directly modeled in PolicyEngine")

    if 'medicaid' in text and ('expansion' in text or 'eligibility' in text):
        return (80, "Medicaid policy - modeled in PolicyEngine")

    if 'universal basic income' in text or 'guaranteed income' in text:
        return (85, "UBI/guaranteed income - Max's research focus")

    if ('tax credit' in text or 'eitc' in text) and 'state' in text:
        return (80, "State tax credits - PolicyEngine models these")

    # RELEVANT (60-74)
    if 'tax policy' in text or 'tax reform' in text:
        return (70, "Tax policy - core PolicyEngine domain")

    if ('snap' in text or 'wic' in text or 'tanf' in text):
        return (70, "Benefit program analysis")

    if 'medicaid' in text or 'medicare' in text:
        return (65, "Health policy - PolicyEngine models health programs")

    if 'distributional' in text or ('inequality' in text and 'income' in text):
        return (65, "Distributional analysis - PolicyEngine's output focus")

    # MODERATELY RELEVANT (40-59)
    if 'administrative data' in text and ('benefit' in text or 'policy' in text):
        return (55, "Administrative data for policy - useful methodology")

    if 'poverty' in text:
        return (50, "Poverty focus - relevant to PolicyEngine impact")

    if 'housing' in text and ('subsidy' in text or 'voucher' in text):
        return (50, "Housing assistance - adjacent policy")

    if 'tax' in text:
        return (45, "Tax-related topic")

    # LOW RELEVANCE (0-39)
    if 'policy' in text:
        return (30, "General policy - tangentially relevant")

    return (20, "Low PolicyEngine relevance")


def score_for_person(session, person_name):
    """
    Score session for specific person (0-100).

    Returns: (score, rationale)
    """
    general_score, _ = score_session_for_policyengine(session)
    title = session['title'].lower()
    desc = (session.get('description') or '').lower()[:2000]
    text = f"{title} {desc}"

    if person_name == 'Max Ghenis':
        # Max: CEO, UBI focus, poverty reduction
        if 'universal basic income' in text or 'guaranteed income' in text or 'cash transfer' in text:
            return (100, "UBI/cash transfers - Max's research specialty")
        if 'poverty' in text and ('measurement' in text or 'reduction' in text):
            return (95, "Poverty measurement/reduction - critical for Max")
        if 'ctc' in text or 'child tax credit' in text:
            return (90, "CTC policy - highly relevant to Max")
        if 'child allowance' in text:
            return (90, "Child allowance - Max's research area")
        # Otherwise base on general score with slight boost for tax/poverty
        if 'tax' in text or 'poverty' in text:
            return (min(100, general_score + 10), "Tax/poverty policy - relevant to CEO perspective")
        return (general_score, "Standard relevance")

    elif person_name == 'Pavel Makarchuk':
        # Pavel: Director of Growth, microsimulation expert, tax-benefit modeling
        if 'microsimulation' in text:
            return (100, "Microsimulation - Pavel's core expertise")
        if 'ctc' in text or 'eitc' in text or 'tax credit' in text:
            return (95, "Tax credits - Pavel's modeling expertise")
        if 'tax policy' in text and ('distributional' in text or 'reform' in text):
            return (90, "Tax policy analysis - Pavel's expertise")
        if 'policy modeling' in text or 'simulation' in text:
            return (85, "Policy modeling - Pavel's domain")
        if 'behavioral response' in text or 'labor supply' in text:
            return (80, "Behavioral effects - key for microsimulation")
        if 'data visualization' in text:
            return (75, "Data viz - relevant to Pavel's growth role")
        # Tax and benefit programs
        if 'tax' in text:
            return (min(100, general_score + 15), "Tax policy - Pavel's expertise")
        return (general_score, "Standard relevance")

    elif person_name == 'Daphne Hansell':
        # Daphne: Health Policy Analyst
        if 'medicaid' in text or 'medicare' in text:
            return (95, "Medicaid/Medicare - Daphne's core focus")
        if 'health policy' in text or 'health reform' in text or 'aca' in text:
            return (95, "Health policy - Daphne's specialty")
        if 'health insurance' in text or 'health coverage' in text:
            return (90, "Health insurance - Daphne's expertise")
        if 'health' in text and ('access' in text or 'equity' in text):
            return (85, "Health access/equity - relevant to Daphne")
        if 'housing policy' in text:
            return (70, "Housing policy - Daphne's secondary interest")
        # Health-adjacent
        if 'health' in text:
            return (min(100, general_score + 10), "Health topic - relevant to Daphne")
        return (general_score, "Standard relevance")

    return (general_score, "Standard relevance")


def score_all_sessions():
    """Score all sessions with dual system."""
    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    add_score_columns()

    cursor.execute('SELECT * FROM sessions')
    sessions = cursor.fetchall()

    print(f"Scoring {len(sessions)} sessions with dual system...\n")

    people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell']

    for session in sessions:
        session_dict = dict(session)

        # General score
        gen_score, gen_rationale = score_session_for_policyengine(session_dict)

        # Person-specific scores
        max_score, _ = score_for_person(session_dict, 'Max Ghenis')
        pavel_score, _ = score_for_person(session_dict, 'Pavel Makarchuk')
        daphne_score, _ = score_for_person(session_dict, 'Daphne Hansell')

        # Update database
        cursor.execute('''
            UPDATE sessions
            SET general_score = ?, max_score = ?, pavel_score = ?, daphne_score = ?
            WHERE session_id = ?
        ''', (gen_score, max_score, pavel_score, daphne_score, session['session_id']))

        if gen_score >= 80:
            print(f"[{gen_score:3d}] {session['title'][:60]}")
            print(f"      Max: {max_score:3d} | Pavel: {pavel_score:3d} | Daphne: {daphne_score:3d}")
            print()

    conn.commit()
    conn.close()

    print("✓ Dual scoring complete!")


if __name__ == '__main__':
    score_all_sessions()

    # Show top sessions by person
    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    people = [
        ('Max Ghenis', 'max_score'),
        ('Pavel Makarchuk', 'pavel_score'),
        ('Daphne Hansell', 'daphne_score')
    ]

    for person_name, score_col in people:
        print(f"\n{'='*80}")
        print(f"Top 10 sessions for {person_name}")
        print(f"{'='*80}")

        cursor.execute(f'''
            SELECT title, date, start_time, general_score, {score_col} as person_score
            FROM sessions
            WHERE {score_col} >= 60
            ORDER BY {score_col} DESC, general_score DESC
            LIMIT 10
        ''')

        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"{i}. [{row['person_score']:.0f}] {row['title'][:70]}")
            print(f"   {row['date']} {row['start_time']} (General: {row['general_score']:.0f})")

    conn.close()
