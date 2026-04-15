import { useMemo } from 'react';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet';

const mapMarkerIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const statusClassMap = {
  DRIVING: 'status-driving',
  OFF_DUTY: 'status-off-duty',
  ON_DUTY_NOT_DRIVING: 'status-on-duty',
  SLEEPER: 'status-sleeper',
};

function StatCard({ label, value, helper }) {
  return (
    <article className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {helper ? <small className="stat-helper">{helper}</small> : null}
    </article>
  );
}

function ResultsPage({ result }) {
  const routeCoordinates = useMemo(() => {
    if (!result?.route?.legs) return [];
    const coords = [];
    result.route.legs.forEach((leg, legIndex) => {
      if (!Array.isArray(leg.geometry)) return;
      leg.geometry.forEach((point, pointIndex) => {
        const [lng, lat] = point;
        if (legIndex > 0 && pointIndex === 0) return;
        coords.push([lat, lng]);
      });
    });
    return coords;
  }, [result]);

  if (!result) {
    return (
      <section className="card">
        <header className="section-head">
          <h2>No Trip Plan Yet</h2>
          <p>Create a trip first to view results and generated logs.</p>
        </header>
        <Link className="nav-link-btn" to="/">
          Go To Planner
        </Link>
      </section>
    );
  }

  const mapCenter = routeCoordinates.length > 0 ? routeCoordinates[0] : [39.8283, -98.5795];

  return (
    <>
      <section className="metrics-grid">
        <StatCard
          label="Total Miles"
          value={result.route.total_distance_miles}
          helper="Route distance across all legs"
        />
        <StatCard
          label="Drive Hours"
          value={result.route.total_drive_hours}
          helper="Total planned driving time"
        />
        <StatCard
          label="Cycle After Trip"
          value={result.summary.cycle_hours_used_after_trip}
          helper="Estimated 70/8 usage after completion"
        />
        <StatCard
          label="Daily Logs"
          value={result.daily_logs.length}
          helper="Generated sheets for this trip"
        />
      </section>

      <section className="content-grid">
        <article className="card map-card">
          <header className="section-head">
            <h2>Route Map</h2>
            <p>Polyline path with trip start and destination markers.</p>
          </header>
          <MapContainer center={mapCenter} zoom={5} scrollWheelZoom={false} className="map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {routeCoordinates.length > 0 && <Polyline positions={routeCoordinates} />}
            {routeCoordinates.length > 0 && (
              <Marker position={routeCoordinates[0]} icon={mapMarkerIcon}>
                <Popup>Current Location</Popup>
              </Marker>
            )}
            {routeCoordinates.length > 2 && (
              <Marker position={routeCoordinates[routeCoordinates.length - 1]} icon={mapMarkerIcon}>
                <Popup>Dropoff Location</Popup>
              </Marker>
            )}
          </MapContainer>
        </article>

        <article className="card side-stack">
          <div>
            <header className="section-head">
              <h2>Route Instructions</h2>
              <p>Turn-by-turn guidance generated from map API.</p>
            </header>
            <ol className="scroll-list ordered">
              {(result.route.instructions || []).slice(0, 40).map((item, idx) => (
                <li key={`${idx}-${item.slice(0, 24)}`}>{item}</li>
              ))}
            </ol>
          </div>

          <div>
            <header className="section-head">
              <h2>Stops & Rests</h2>
              <p>Detected compliance-relevant trip events.</p>
            </header>
            <ul className="scroll-list stops-list">
              {(result.stops_and_rests || []).map((stop, idx) => (
                <li key={`${stop.time}-${idx}`}>
                  <span className={`status-pill ${statusClassMap[stop.status] || ''}`}>{stop.status}</span>
                  <div className="stop-details">
                    <strong>{stop.location}</strong>
                    <p>{stop.notes}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </article>
      </section>

      <section className="card">
        <header className="section-head">
          <h2>Duty Timeline</h2>
          <p>Chronological status transitions generated by the HOS engine.</p>
        </header>
        <div className="timeline-table">
          <div className="table-head">
            <span>Status</span>
            <span>Duration</span>
            <span>Location</span>
            <span>Notes</span>
          </div>
          {result.timeline.map((event, index) => (
            <div className="table-row" key={`${event.start}-${index}`}>
              <span>
                <span className={`status-pill ${statusClassMap[event.status] || ''}`}>{event.status}</span>
              </span>
              <span>{event.duration_hours}h</span>
              <span>{event.location}</span>
              <span>{event.notes}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <header className="section-head">
          <h2>Daily Log Sheets</h2>
          <p>Open a dedicated page for each generated daily log.</p>
        </header>
        <div className="logs-grid">
          {result.daily_logs.map((log) => (
            <article className="log-card" key={log.date}>
              <div className="log-head">
                <h3>{log.date}</h3>
                <span className="total-chip">{log.total_hours}h total</span>
              </div>
              <div className="log-metrics">
                <p>Driving: {log.driving_hours}h</p>
                <p>On Duty ND: {log.on_duty_not_driving_hours}h</p>
                <p>Off Duty: {log.off_duty_hours}h</p>
                <p>Sleeper: {log.sleeper_hours}h</p>
              </div>
              <Link className="nav-link-btn compact" to={`/logs/${log.date}`}>
                Open Full Log Sheet
              </Link>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

export default ResultsPage;
