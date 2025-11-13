"""
Tests for relevance scoring module.
"""
import pytest
import sqlite3
import json
import os
import tempfile
from scraper import APPAMScraper
from relevance_scorer import RelevanceScorer


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def scorer(temp_db):
    """Create a scorer instance with temporary database."""
    scraper = APPAMScraper(db_path=temp_db)
    scraper.init_database()
    return RelevanceScorer(db_path=temp_db)


def test_score_session_with_high_relevance_keywords(scorer):
    """Test that sessions with high-relevance keywords get high scores."""
    session_data = {
        'title': 'Microsimulation Analysis of Tax Policy Reform',
        'description': 'This session explores tax-benefit microsimulation models for policy analysis.',
        'chair': 'Dr. Smith',
        'papers': json.dumps([
            'Impact of Universal Basic Income on Poverty Reduction',
            'Medicaid Expansion and Health Coverage'
        ])
    }

    result = scorer.score_session(session_data)
    assert result['score'] > 20, "Session with multiple high-value keywords should score high"
    assert len(result['matched_keywords']) > 0


def test_score_session_with_low_relevance(scorer):
    """Test that sessions with low relevance get low scores."""
    session_data = {
        'title': 'Urban Planning in the 21st Century',
        'description': 'Discussion of modern urban planning approaches.',
        'chair': 'Dr. Jones',
        'papers': json.dumps([
            'Traffic Management Systems',
            'Green Spaces in Cities'
        ])
    }

    result = scorer.score_session(session_data)
    assert result['score'] < 5, "Session without relevant keywords should score low"


def test_score_session_health_policy(scorer):
    """Test scoring for health policy sessions."""
    session_data = {
        'title': 'Health Insurance Coverage Under the Affordable Care Act',
        'description': 'Analysis of Medicaid expansion and health care reform impacts.',
        'chair': 'Dr. Health',
        'papers': json.dumps([
            'Medicare Eligibility and Coverage Gaps',
            'Health Equity in Insurance Markets'
        ])
    }

    result = scorer.score_session(session_data)
    assert result['score'] > 30, "Health policy session should score very high"


def test_score_session_title_bonus(scorer):
    """Test that keywords in title get bonus points."""
    session_with_title_keyword = {
        'title': 'Microsimulation Models and Tax Policy',
        'description': '',
        'chair': '',
        'papers': ''
    }

    session_with_description_keyword = {
        'title': 'Conference Session',
        'description': 'Using microsimulation models for tax policy analysis.',
        'chair': '',
        'papers': ''
    }

    result1 = scorer.score_session(session_with_title_keyword)
    result2 = scorer.score_session(session_with_description_keyword)

    # Title appearance should give higher score (due to title bonus)
    assert result1['score'] > result2['score']


def test_score_for_person_max_ghenis(scorer):
    """Test personalized scoring for Max Ghenis (UBI focus)."""
    session_data = {
        'title': 'Universal Basic Income and Poverty Reduction',
        'description': 'Examining guaranteed income programs and their effects.',
        'chair': '',
        'papers': ''
    }

    result = scorer.score_for_person(session_data, 'Max Ghenis')
    base_result = scorer.score_session(session_data)

    # Max's score should be higher due to UBI interest
    assert result['score'] > base_result['score']
    assert result['modifier'] > 1.0


def test_score_for_person_daphne_hansell(scorer):
    """Test personalized scoring for Daphne Hansell (health policy focus)."""
    session_data = {
        'title': 'Health Policy Reform and Insurance Coverage',
        'description': 'Analysis of Medicare and Medicaid programs.',
        'chair': '',
        'papers': ''
    }

    result = scorer.score_for_person(session_data, 'Daphne Hansell')
    base_result = scorer.score_session(session_data)

    # Daphne's score should be significantly higher for health policy
    assert result['score'] > base_result['score']
    assert result['modifier'] >= 1.8


def test_score_for_person_pavel_makarchuk(scorer):
    """Test personalized scoring for Pavel Makarchuk (microsim/modeling focus)."""
    session_data = {
        'title': 'Microsimulation Modeling Techniques',
        'description': 'Advanced policy modeling and behavioral responses.',
        'chair': '',
        'papers': ''
    }

    result = scorer.score_for_person(session_data, 'Pavel Makarchuk')
    base_result = scorer.score_session(session_data)

    # Pavel's score should be higher for microsimulation topics
    assert result['score'] > base_result['score']
    assert result['modifier'] >= 1.3


def test_score_all_sessions(scorer, temp_db):
    """Test scoring all sessions in database."""
    # Add test sessions
    scraper = APPAMScraper(db_path=temp_db)

    sessions = [
        {
            'session_id': 'TEST001',
            'title': 'Tax Policy and Microsimulation',
            'date': '2025-11-13',
            'start_time': '10:00 AM',
            'end_time': '11:30 AM',
            'location': 'Room A',
            'description': 'Using microsimulation for tax reform analysis.',
            'chair': '',
            'papers': '',
            'presenters': '',
            'raw_html': ''
        },
        {
            'session_id': 'TEST002',
            'title': 'Urban Planning Methods',
            'date': '2025-11-13',
            'start_time': '2:00 PM',
            'end_time': '3:30 PM',
            'location': 'Room B',
            'description': 'Modern approaches to urban development.',
            'chair': '',
            'papers': '',
            'presenters': '',
            'raw_html': ''
        }
    ]

    for session in sessions:
        scraper.save_session(session)

    scorer.score_all_sessions()

    # Check that scores were saved
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT session_id, title, relevance_score FROM sessions ORDER BY relevance_score DESC')
    results = [dict(row) for row in cursor.fetchall()]

    # First session should have higher score
    assert results[0]['session_id'] == 'TEST001'
    assert results[0]['relevance_score'] > results[1]['relevance_score']

    conn.close()


def test_get_top_sessions(scorer, temp_db):
    """Test retrieving top-scored sessions."""
    # Add test sessions with various scores
    scraper = APPAMScraper(db_path=temp_db)

    sessions = [
        ('TEST001', 'High Score Session', 'Tax microsimulation and poverty analysis'),
        ('TEST002', 'Medium Score Session', 'Social policy and welfare programs'),
        ('TEST003', 'Low Score Session', 'Traffic management systems'),
    ]

    for session_id, title, description in sessions:
        session_data = {
            'session_id': session_id,
            'title': title,
            'date': '2025-11-13',
            'start_time': '10:00 AM',
            'end_time': '11:30 AM',
            'location': 'Room A',
            'description': description,
            'chair': '',
            'papers': '',
            'presenters': '',
            'raw_html': ''
        }
        scraper.save_session(session_data)

    scorer.score_all_sessions()
    top_sessions = scorer.get_top_sessions(limit=2)

    assert len(top_sessions) == 2
    assert top_sessions[0]['session_id'] == 'TEST001'
    assert top_sessions[1]['session_id'] == 'TEST002'


def test_keyword_matching_case_insensitive(scorer):
    """Test that keyword matching is case-insensitive."""
    session_upper = {
        'title': 'TAX POLICY AND MICROSIMULATION',
        'description': 'ANALYSIS OF UNIVERSAL BASIC INCOME',
        'chair': '',
        'papers': ''
    }

    session_lower = {
        'title': 'tax policy and microsimulation',
        'description': 'analysis of universal basic income',
        'chair': '',
        'papers': ''
    }

    result_upper = scorer.score_session(session_upper)
    result_lower = scorer.score_session(session_lower)

    # Scores should be equal regardless of case
    assert result_upper['score'] == result_lower['score']


def test_diminishing_returns_for_repeated_keywords(scorer):
    """Test that repeated keywords have diminishing returns."""
    session_once = {
        'title': 'Tax Policy Analysis',
        'description': '',
        'chair': '',
        'papers': ''
    }

    session_repeated = {
        'title': 'Tax Policy, Tax Policy, Tax Policy Analysis',
        'description': 'Tax policy discussion. Tax policy review. Tax policy.',
        'chair': '',
        'papers': ''
    }

    result_once = scorer.score_session(session_once)
    result_repeated = scorer.score_session(session_repeated)

    # Repeated keywords should increase score but not linearly
    score_increase = result_repeated['score'] - result_once['score']
    # The increase should be less than if each repetition counted fully
    expected_max_increase = result_once['score'] * 2  # If it counted fully 3x more
    assert result_repeated['score'] > result_once['score']
    assert score_increase < expected_max_increase
