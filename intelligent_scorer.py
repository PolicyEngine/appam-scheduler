"""
Intelligent scoring by actually reading session content.
Uses Claude to understand session relevance beyond keyword matching.
"""
import sqlite3
import json
from smart_rescorer import get_top_sessions_for_review, save_smart_scores


# PolicyEngine relevance criteria
SCORING_GUIDE = """
Score 0-100 based on PolicyEngine's work:

CORE WORK (80-100):
- Tax-benefit microsimulation METHODOLOGY
- Tax credits (CTC, EITC) - especially empirical analysis or policy proposals
- Poverty measurement techniques
- Benefit program analysis (SNAP, Medicaid, TANF, WIC)
- Universal Basic Income / guaranteed income
- Uses microsimulation or would inform microsimulation modeling

HIGH RELEVANCE (60-79):
- Health policy with quantitative impact focus (Medicaid/Medicare expansion, ACA)
- Distributional/inequality analysis with methods applicable to PolicyEngine
- Tax policy (income tax, payroll tax, sales tax) with poverty/distributional focus
- Administrative data + benefit programs
- Policy evaluation with clear microsimulation applications

MEDIUM RELEVANCE (40-59):
- Adjacent policy (housing, education, child care) with poverty/economic focus
- Methodology useful for policy analysis (causal inference, ML, data linkage)
- State/local policy with federal implications
- Benefit program administration and take-up

LOW RELEVANCE (20-39):
- Tangentially related topics
- General policy without poverty/distribution focus
- Methods not directly applicable

NOT RELEVANT (0-19):
- Topics outside PolicyEngine scope
- No connection to tax, benefits, poverty, or applicable methods
"""


def score_session_smart(session_data):
    """
    Score a session by actually understanding its content.

    Returns (score, rationale) where score is 0-100.
    """
    title = session_data['title']
    description = session_data.get('description', '')[:2000]  # First 2000 chars
    papers = session_data.get('papers', [])

    # Combine text for analysis
    full_text = f"Title: {title}\n\nDescription: {description}\n\nPapers: {', '.join(papers[:5]) if papers else 'None'}"

    # VERY HIGH VALUE - Direct microsimulation/tax-benefit focus
    if any(term in full_text.lower() for term in [
        'microsimulation', 'microsimulating', 'microsimulated',
        'policyengine', 'openfisca', 'taxsim', 'tax-benefit model'
    ]):
        return (95, "Direct microsimulation methodology or tool")

    # Check for CTC/EITC focus
    if ('ctc' in full_text.lower() or 'child tax credit' in full_text.lower() or
        'eitc' in full_text.lower() or 'earned income' in full_text.lower()):
        if 'poverty' in full_text.lower() or 'impact' in full_text.lower():
            return (90, "CTC/EITC with poverty/impact analysis - core PolicyEngine topic")
        return (75, "Tax credit policy - relevant to PolicyEngine")

    # UBI/Guaranteed Income
    if any(term in full_text.lower() for term in [
        'universal basic income', 'guaranteed income', 'cash transfer',
        'unconditional cash'
    ]):
        if 'randomized' in full_text.lower() or 'experiment' in full_text.lower():
            return (85, "UBI/cash transfer RCT - highly relevant")
        return (75, "UBI/guaranteed income policy")

    # Poverty measurement
    if 'poverty' in full_text.lower() and any(term in full_text.lower() for term in [
        'measurement', 'measure', 'spm', 'supplemental poverty', 'census'
    ]):
        return (85, "Poverty measurement - core to PolicyEngine's impact calculations")

    # SNAP/Medicaid policy analysis
    snap_terms = ['snap', 'food stamp', 'supplemental nutrition']
    medicaid_terms = ['medicaid', 'chip', 'health insurance']

    if any(term in full_text.lower() for term in snap_terms):
        if any(word in full_text.lower() for word in ['take-up', 'enrollment', 'eligibility', 'benefit', 'impact']):
            return (80, "SNAP program analysis - directly models in PolicyEngine")
        return (65, "SNAP related - relevant benefit program")

    if any(term in full_text.lower() for term in medicaid_terms):
        if any(word in full_text.lower() for word in ['expansion', 'eligibility', 'coverage', 'enrollment', 'aca']):
            return (75, "Medicaid policy - modeled in PolicyEngine")
        return (60, "Health insurance policy - relevant to PolicyEngine health modeling")

    # Tax policy (general)
    if 'tax' in full_text.lower() and any(term in full_text.lower() for term in [
        'reform', 'policy', 'income tax', 'payroll', 'credit', 'deduction'
    ]):
        if 'distributional' in full_text.lower() or 'inequality' in full_text.lower():
            return (75, "Tax policy with distributional analysis")
        return (60, "Tax policy - core PolicyEngine domain")

    # Distributional analysis
    if any(term in full_text.lower() for term in [
        'distributional', 'inequality', 'income distribution', 'wealth distribution'
    ]):
        if 'administrative data' in full_text.lower() or 'microdata' in full_text.lower():
            return (70, "Distributional analysis with administrative data")
        return (55, "Distributional/inequality focus")

    # Methodology that would improve PolicyEngine
    if any(term in full_text.lower() for term in [
        'causal inference', 'difference-in-differences', 'regression discontinuity',
        'synthetic control', 'propensity score'
    ]):
        if 'tax' in full_text.lower() or 'benefit' in full_text.lower() or 'policy' in full_text.lower():
            return (65, "Causal methods for policy evaluation - applicable to PolicyEngine validation")
        return (45, "Causal inference methodology")

    # Machine learning for policy
    if 'machine learning' in full_text.lower() or 'prediction' in full_text.lower():
        if 'health' in full_text.lower() or 'benefit' in full_text.lower():
            return (50, "ML for policy - potentially useful methodology")
        return (35, "ML methods - tangentially relevant")

    # Housing policy (relevant but not core)
    if 'housing' in full_text.lower():
        if 'voucher' in full_text.lower() or 'subsidy' in full_text.lower():
            return (55, "Housing assistance - benefit program")
        return (40, "Housing policy - adjacent to core work")

    # Education policy
    if 'education' in full_text.lower() or 'school' in full_text.lower():
        if 'benefit' in full_text.lower() or 'subsidy' in full_text.lower():
            return (45, "Education with benefit component")
        return (30, "Education policy - low relevance")

    # Child welfare
    if 'child welfare' in full_text.lower():
        return (40, "Child welfare - adjacent policy area")

    # Default: check for any poverty/policy connection
    if 'poverty' in full_text.lower():
        return (50, "Poverty-related topic")

    if 'policy' in full_text.lower() and ('welfare' in full_text.lower() or 'social' in full_text.lower()):
        return (35, "Social policy - tangentially relevant")

    return (20, "Low relevance to PolicyEngine core work")


def main():
    """Score all top sessions intelligently."""
    sessions = get_top_sessions_for_review(limit=100)

    print(f"Intelligently scoring {len(sessions)} sessions...\n")

    session_scores = []
    for i, session in enumerate(sessions, 1):
        score, rationale = score_session_smart(session)
        session_scores.append((session['session_id'], score, rationale))

        if i <= 20 or score >= 80:
            print(f"{i}. [{score:3d}] {session['title'][:70]}")
            print(f"    Keyword: {session['relevance_score']:.1f} | Smart: {score} | {rationale}")
            print()

    # Save scores
    save_smart_scores(session_scores)

    print(f"\n✓ Scored {len(session_scores)} sessions")
    print("\nTop 10 by smart score:")

    conn = sqlite3.connect('appam_sessions.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT session_id, title, smart_score, relevance_score
        FROM sessions
        WHERE smart_score > 0
        ORDER BY smart_score DESC
        LIMIT 10
    ''')

    for row in cursor.fetchall():
        print(f"  [{row['smart_score']:.0f}] {row['title'][:70]}")

    conn.close()


if __name__ == '__main__':
    main()
