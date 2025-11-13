import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import './App.css';

// Main App Component
function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/team-schedule" element={<TeamSchedule />} />
            <Route path="/schedule/:person" element={<PersonSchedule />} />
            <Route path="/sessions" element={<AllSessions />} />
            <Route path="/presenters" element={<Presenters />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

// Header Component
function Header() {
  return (
    <header className="header">
      <div className="container">
        <h1>APPAM 2025 Conference</h1>
        <p>PolicyEngine Team Schedule</p>
        <nav className="nav mt-2">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/team-schedule" className="nav-link">Team Schedule</Link>
          <Link to="/sessions" className="nav-link">All Sessions</Link>
          <Link to="/presenters" className="nav-link">Presenters</Link>
        </nav>
      </div>
    </header>
  );
}

// Home Page - Overview and Team Schedules
function HomePage() {
  const [stats, setStats] = useState(null);
  const [schedule, setSchedule] = useState({});
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      fetch(`${process.env.PUBLIC_URL}/data/stats.json`).then(r => r.json()),
      fetch(`${process.env.PUBLIC_URL}/data/schedule.json`).then(r => r.json())
    ]).then(([statsData, scheduleData]) => {
      setStats(statsData);
      setSchedule(scheduleData);
      setLoading(false);
    }).catch(err => {
      console.error('Error loading data:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  const people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell'];

  return (
    <div className="container">
      {/* Stats Overview */}
      <section className="stats-grid grid grid-3 mb-4">
        <div className="card text-center">
          <h3>{stats?.total_sessions || 0}</h3>
          <p>Total Sessions</p>
        </div>
        <div className="card text-center">
          <h3>{stats?.high_value_sessions || 0}</h3>
          <p>High-Value Sessions</p>
        </div>
        <div className="card text-center">
          <h3>{stats?.total_presenters || 0}</h3>
          <p>Presenters</p>
        </div>
      </section>

      {/* Team Schedules */}
      <section>
        <h2 className="mb-3">Team Schedules</h2>
        <div className="grid grid-3">
          {people.map(person => (
            <div key={person} className="card person-card" onClick={() => navigate(`/schedule/${encodeURIComponent(person)}`)}>
              <h3>{person}</h3>
              <p className="sessions-count">
                {schedule[person]?.length || 0} sessions assigned
              </p>
              <button className="btn-primary mt-2">View Schedule →</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// Team Schedule Page - Side by Side View
function TeamSchedule() {
  const [timeSlots, setTimeSlots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.PUBLIC_URL}/data/team_schedule.json`)
      .then(r => r.json())
      .then(data => {
        setTimeSlots(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading data:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  const people = ['Max Ghenis', 'Pavel Makarchuk', 'Daphne Hansell'];

  // Group by date
  const slotsByDate = {};
  timeSlots.forEach(slot => {
    if (!slotsByDate[slot.date]) {
      slotsByDate[slot.date] = [];
    }
    slotsByDate[slot.date].push(slot);
  });

  // Sort slots within each date chronologically
  const parseTime = (timeStr) => {
    const match = timeStr.match(/(\d+):(\d+)(am|pm)/i);
    if (!match) return 0;
    let hours = parseInt(match[1]);
    let minutes = parseInt(match[2]);
    const period = match[3];
    if (period.toLowerCase() === 'pm' && hours !== 12) hours += 12;
    if (period.toLowerCase() === 'am' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  };

  Object.keys(slotsByDate).forEach(date => {
    slotsByDate[date].sort((a, b) => parseTime(a.start_time) - parseTime(b.start_time));
  });

  return (
    <div className="container">
      <h2 className="mb-3">Team Schedule - Booth Coverage View</h2>
      <p className="mb-3">
        Sessions shown in <span className="badge badge-success">green</span> indicate attendance.
        <span className="badge badge-warning ml-2">BOOTH</span> indicates booth coverage.
      </p>

      {Object.entries(slotsByDate).sort().map(([date, slots]) => (
        <div key={date} className="date-section mb-4">
          <h3 className="date-header">{formatDate(date)}</h3>

          <div className="team-schedule-table">
            {slots.map((slot, idx) => {
              return (
                <div key={idx} className="time-slot-row">
                  <div className="time-slot-time">
                    <strong>{slot.start_time} - {slot.end_time}</strong>
                  </div>
                  <div className="time-slot-people">
                    {people.map(person => {
                      const assignment = slot.assignments?.[person];

                      return (
                        <div key={person} className="person-slot">
                          <div className="person-name">{person.split(' ')[0]}</div>
                          {assignment?.type === 'session' ? (
                            <div className="assigned-session">
                              <span className="session-title">{assignment.title.substring(0, 55)}...</span>
                              <div className="scores mt-1">
                                {assignment.general_score > 0 && (
                                  <span className="badge badge-info">Overall: {assignment.general_score.toFixed(0)}</span>
                                )}
                                {assignment.person_score > 0 && (
                                  <span className="badge badge-success ml-1">
                                    You: {assignment.person_score.toFixed(0)}
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : assignment?.type === 'absent' ? (
                            <div className="absent-assignment">
                              <span className="badge badge-secondary">ABSENT</span>
                            </div>
                          ) : assignment?.type === 'free' ? (
                            <div className="free-assignment">
                              <span className="badge badge-info">FREE</span>
                              {assignment.note && <div className="text-sm text-muted mt-1">{assignment.note}</div>}
                            </div>
                          ) : (
                            <div className="booth-assignment">
                              <span className="badge badge-warning">BOOTH</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// Person Schedule Page
function PersonSchedule() {
  const location = useLocation();
  const personParam = location.pathname.split('/').pop();
  const person = decodeURIComponent(personParam);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.PUBLIC_URL}/data/schedule.json`)
      .then(r => r.json())
      .then(data => {
        setSessions(data[person] || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading schedule:', err);
        setLoading(false);
      });
  }, [person]);

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  // Group sessions by date
  const sessionsByDate = sessions.reduce((acc, session) => {
    const date = session.date;
    if (!acc[date]) acc[date] = [];
    acc[date].push(session);
    return acc;
  }, {});

  return (
    <div className="container">
      <h2 className="mb-3">{person}'s Schedule</h2>

      {Object.keys(sessionsByDate).length === 0 ? (
        <div className="card">
          <p>No sessions assigned yet.</p>
        </div>
      ) : (
        Object.entries(sessionsByDate).sort().map(([date, dateSessions]) => (
          <div key={date} className="date-section mb-4">
            <h3 className="date-header">{formatDate(date)}</h3>
            <div className="sessions-list">
              {dateSessions.sort((a, b) => a.start_time.localeCompare(b.start_time)).map(session => (
                <SessionCard key={session.session_id} session={session} showAssignee={false} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// All Sessions Page
function AllSessions() {
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [minScore, setMinScore] = useState(0);
  const [selectedDate, setSelectedDate] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.PUBLIC_URL}/data/sessions.json`)
      .then(r => r.json())
      .then(data => {
        setSessions(data);
        setFilteredSessions(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading sessions:', err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let filtered = sessions;

    // Filter by score
    if (minScore > 0) {
      filtered = filtered.filter(s => s.relevance_score >= minScore);
    }

    // Filter by date
    if (selectedDate !== 'all') {
      filtered = filtered.filter(s => s.date === selectedDate);
    }

    setFilteredSessions(filtered);
  }, [minScore, selectedDate, sessions]);

  const dates = [...new Set(sessions.map(s => s.date))].sort();

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  return (
    <div className="container">
      <h2 className="mb-3">All Sessions</h2>

      {/* Filters */}
      <div className="card filters mb-3">
        <div className="filter-group">
          <label>
            Minimum Relevance Score:
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(parseInt(e.target.value))}
            />
            <span className="badge badge-primary ml-2">{minScore}+</span>
          </label>

          <label className="ml-3">
            Date:
            <select value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}>
              <option value="all">All Dates</option>
              {dates.map(date => (
                <option key={date} value={date}>{formatDate(date)}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* Sessions List */}
      <p className="mb-2">{filteredSessions.length} sessions</p>
      <div className="sessions-list">
        {filteredSessions.map(session => (
          <SessionCard key={session.session_id} session={session} showAssignee={true} />
        ))}
      </div>
    </div>
  );
}

// Presenters Page
function Presenters() {
  const [presenters, setPresenters] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.PUBLIC_URL}/data/presenters.json`)
      .then(r => r.json())
      .then(data => {
        setPresenters(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading presenters:', err);
        setLoading(false);
      });
  }, []);

  const filteredPresenters = presenters.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  return (
    <div className="container">
      <h2 className="mb-3">Presenters ({presenters.length})</h2>

      {/* Search */}
      <div className="card mb-3">
        <input
          type="text"
          placeholder="Search presenters..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: '100%' }}
        />
      </div>

      {/* Presenters List */}
      <div className="grid grid-2">
        {filteredPresenters.map(presenter => (
          <div key={presenter.id} className="card">
            <h4>{presenter.name}</h4>
            {presenter.email && <p className="text-muted">{presenter.email}</p>}
            {presenter.affiliation && <p className="text-muted">{presenter.affiliation}</p>}
            <p className="mt-2">
              <span className="badge badge-primary">{presenter.session_count} session{presenter.session_count !== 1 ? 's' : ''}</span>
            </p>
            {presenter.notes && <p className="mt-2 text-sm">{presenter.notes}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

// Session Card Component
function SessionCard({ session, showAssignee }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card session-card">
      <div className="session-header">
        <div>
          <h4>{session.title}</h4>
          <div className="session-meta">
            <span className="badge badge-info">{session.date}</span>
            <span className="badge badge-info">{session.start_time} - {session.end_time}</span>
            {session.location && <span className="badge badge-primary">{session.location}</span>}
            {session.relevance_score > 0 && (
              <span className="badge badge-success">Score: {session.relevance_score.toFixed(1)}</span>
            )}
            {showAssignee && session.assigned_to && (
              <span className="badge badge-warning">{session.assigned_to}</span>
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="session-details mt-2">
          {session.chair && <p><strong>Chair:</strong> {session.chair}</p>}
          {session.description && <p className="mt-2">{session.description}</p>}
          {session.presenters && session.presenters.length > 0 && (
            <div className="mt-2">
              <strong>Presenters:</strong>
              <ul className="presenters-list">
                {session.presenters.map((p, i) => (
                  <li key={i}>{p.name}{p.email && ` (${p.email})`}</li>
                ))}
              </ul>
            </div>
          )}
          {session.papers && session.papers.length > 0 && (
            <div className="mt-2">
              <strong>Papers:</strong>
              <ul className="papers-list">
                {session.papers.map((paper, i) => (
                  <li key={i}>{paper}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <button
        className="btn-outline mt-2"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? 'Show Less' : 'Show More'}
      </button>
    </div>
  );
}

// Utility Functions
function formatDate(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

export default App;
