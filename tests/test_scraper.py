"""
Tests for APPAM scraper module.
"""
import pytest
import sqlite3
import json
import os
import tempfile
from scraper import APPAMScraper


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def scraper(temp_db):
    """Create a scraper instance with temporary database."""
    return APPAMScraper(db_path=temp_db)


def test_init_database(scraper):
    """Test database initialization creates all tables."""
    scraper.init_database()

    conn = sqlite3.connect(scraper.db_path)
    cursor = conn.cursor()

    # Check that all tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]

    expected_tables = [
        'locations',
        'paper_authors',
        'papers',
        'people',
        'presenters',
        'session_presenters',
        'sessions',
        'time_slots'
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} not created"

    # Check that people were inserted
    cursor.execute("SELECT COUNT(*) FROM people")
    assert cursor.fetchone()[0] == 3

    conn.close()


def test_save_session_basic(scraper):
    """Test saving a basic session."""
    scraper.init_database()

    session_data = {
        'session_id': 'TEST001',
        'title': 'Test Session on Tax Policy',
        'date': '2025-11-13',
        'start_time': '10:00 AM',
        'end_time': '11:30 AM',
        'location': 'Room 101',
        'description': 'A test session about tax policy',
        'chair': 'John Doe',
        'papers': json.dumps(['Paper 1: Tax Reform', 'Paper 2: Income Distribution']),
        'presenters': json.dumps(['Alice Smith', 'Bob Jones']),
        'raw_html': '<html>test</html>'
    }

    scraper.save_session(session_data)

    # Verify session was saved
    conn = sqlite3.connect(scraper.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', ('TEST001',))
    session = dict(cursor.fetchone())

    assert session['title'] == 'Test Session on Tax Policy'
    assert session['date'] == '2025-11-13'
    assert session['start_time'] == '10:00 AM'

    # Verify location was saved
    cursor.execute('SELECT * FROM locations WHERE name = ?', ('Room 101',))
    assert cursor.fetchone() is not None

    # Verify time slot was saved
    cursor.execute('SELECT * FROM time_slots WHERE date = ? AND start_time = ?',
                   ('2025-11-13', '10:00 AM'))
    assert cursor.fetchone() is not None

    # Verify presenters were saved
    cursor.execute('SELECT COUNT(*) FROM presenters')
    assert cursor.fetchone()[0] >= 2

    # Verify presenter relationships
    cursor.execute('''
        SELECT p.name
        FROM presenters p
        JOIN session_presenters sp ON p.id = sp.presenter_id
        WHERE sp.session_id = ?
    ''', ('TEST001',))
    presenter_names = [row[0] for row in cursor.fetchall()]
    assert 'Alice Smith' in presenter_names
    assert 'Bob Jones' in presenter_names

    # Verify papers were saved
    cursor.execute('SELECT COUNT(*) FROM papers WHERE session_id = ?', ('TEST001',))
    assert cursor.fetchone()[0] == 2

    conn.close()


def test_save_session_without_optional_fields(scraper):
    """Test saving a session with minimal data."""
    scraper.init_database()

    session_data = {
        'session_id': 'TEST002',
        'title': 'Minimal Session',
        'date': '2025-11-13',
        'start_time': '2:00 PM',
        'end_time': '3:30 PM',
        'location': '',
        'description': '',
        'chair': '',
        'papers': '',
        'presenters': '',
        'raw_html': ''
    }

    scraper.save_session(session_data)

    conn = sqlite3.connect(scraper.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', ('TEST002',))
    assert cursor.fetchone() is not None
    conn.close()


def test_update_existing_session(scraper):
    """Test that saving a session with same ID updates it."""
    scraper.init_database()

    session_data_v1 = {
        'session_id': 'TEST003',
        'title': 'Original Title',
        'date': '2025-11-13',
        'start_time': '10:00 AM',
        'end_time': '11:30 AM',
        'location': 'Room A',
        'description': 'Original description',
        'chair': 'Jane Doe',
        'papers': json.dumps(['Paper 1']),
        'presenters': json.dumps(['Presenter 1']),
        'raw_html': '<html>v1</html>'
    }

    scraper.save_session(session_data_v1)

    session_data_v2 = session_data_v1.copy()
    session_data_v2['title'] = 'Updated Title'
    session_data_v2['presenters'] = json.dumps(['Presenter 1', 'Presenter 2'])

    scraper.save_session(session_data_v2)

    conn = sqlite3.connect(scraper.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', ('TEST003',))
    session = dict(cursor.fetchone())
    assert session['title'] == 'Updated Title'

    # Verify both presenters are linked
    cursor.execute('''
        SELECT COUNT(*)
        FROM session_presenters
        WHERE session_id = ?
    ''', ('TEST003',))
    assert cursor.fetchone()[0] == 2

    conn.close()


def test_presenter_deduplication(scraper):
    """Test that the same presenter isn't duplicated across sessions."""
    scraper.init_database()

    session1 = {
        'session_id': 'TEST004',
        'title': 'Session 1',
        'date': '2025-11-13',
        'start_time': '10:00 AM',
        'end_time': '11:30 AM',
        'location': 'Room A',
        'description': '',
        'chair': '',
        'papers': '',
        'presenters': json.dumps(['Dr. Smith']),
        'raw_html': ''
    }

    session2 = {
        'session_id': 'TEST005',
        'title': 'Session 2',
        'date': '2025-11-13',
        'start_time': '2:00 PM',
        'end_time': '3:30 PM',
        'location': 'Room B',
        'description': '',
        'chair': '',
        'papers': '',
        'presenters': json.dumps(['Dr. Smith']),
        'raw_html': ''
    }

    scraper.save_session(session1)
    scraper.save_session(session2)

    conn = sqlite3.connect(scraper.db_path)
    cursor = conn.cursor()

    # There should only be one Dr. Smith in presenters table
    cursor.execute('SELECT COUNT(*) FROM presenters WHERE name = ?', ('Dr. Smith',))
    assert cursor.fetchone()[0] == 1

    # But Dr. Smith should be linked to both sessions
    cursor.execute('''
        SELECT COUNT(*)
        FROM session_presenters sp
        JOIN presenters p ON p.id = sp.presenter_id
        WHERE p.name = ?
    ''', ('Dr. Smith',))
    assert cursor.fetchone()[0] == 2

    conn.close()


def test_location_deduplication(scraper):
    """Test that the same location isn't duplicated."""
    scraper.init_database()

    session1 = {
        'session_id': 'TEST006',
        'title': 'Session 1',
        'date': '2025-11-13',
        'start_time': '10:00 AM',
        'end_time': '11:30 AM',
        'location': 'Grand Ballroom',
        'description': '',
        'chair': '',
        'papers': '',
        'presenters': '',
        'raw_html': ''
    }

    session2 = {
        'session_id': 'TEST007',
        'title': 'Session 2',
        'date': '2025-11-13',
        'start_time': '2:00 PM',
        'end_time': '3:30 PM',
        'location': 'Grand Ballroom',
        'description': '',
        'chair': '',
        'papers': '',
        'presenters': '',
        'raw_html': ''
    }

    scraper.save_session(session1)
    scraper.save_session(session2)

    conn = sqlite3.connect(scraper.db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM locations WHERE name = ?', ('Grand Ballroom',))
    assert cursor.fetchone()[0] == 1

    conn.close()
