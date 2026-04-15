import { Link, useParams } from 'react-router-dom';
import LogSheetCanvas from '../components/LogSheetCanvas';

function LogDetailPage({ result }) {
  const { date } = useParams();

  if (!result) {
    return (
      <section className="card">
        <header className="section-head">
          <h2>No Trip Plan Loaded</h2>
          <p>Generate a trip plan first to view detailed daily log sheets.</p>
        </header>
        <Link className="nav-link-btn" to="/">
          Go To Planner
        </Link>
      </section>
    );
  }

  const log = result.daily_logs.find((entry) => entry.date === date);
  if (!log) {
    return (
      <section className="card">
        <header className="section-head">
          <h2>Log Not Found</h2>
          <p>No daily log exists for date: {date}</p>
        </header>
        <Link className="nav-link-btn" to="/results">
          Back To Results
        </Link>
      </section>
    );
  }

  return (
    <section className="card">
      <header className="section-head">
        <h2>Daily Log Sheet Detail</h2>
        <p>Date: {log.date}</p>
      </header>
      <div className="log-metrics">
        <p>Driving: {log.driving_hours}h</p>
        <p>On Duty ND: {log.on_duty_not_driving_hours}h</p>
        <p>Off Duty: {log.off_duty_hours}h</p>
        <p>Sleeper: {log.sleeper_hours}h</p>
        <p>Total: {log.total_hours}h</p>
      </div>
      <LogSheetCanvas log={log} />
      <div className="route-actions">
        <Link className="nav-link-btn compact" to="/results">
          Back To Results
        </Link>
      </div>
    </section>
  );
}

export default LogDetailPage;
