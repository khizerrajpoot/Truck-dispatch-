import { useState } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import PlannerPage from './pages/PlannerPage';
import ResultsPage from './pages/ResultsPage';
import LogDetailPage from './pages/LogDetailPage';
import './App.css';

const initialForm = {
  current_location: '',
  pickup_location: '',
  dropoff_location: '',
  current_cycle_used_hours: '',
};

function App() {
  const [formData, setFormData] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  return (
    <BrowserRouter>
      <main className="app-shell">
        <header className="route-nav">
          <NavLink to="/" end className={({ isActive }) => `route-link ${isActive ? 'active' : ''}`}>
            Planner
          </NavLink>
          <NavLink to="/results" className={({ isActive }) => `route-link ${isActive ? 'active' : ''}`}>
            Results
          </NavLink>
        </header>

        <Routes>
          <Route
            path="/"
            element={
              <PlannerPage
                formData={formData}
                setFormData={setFormData}
                setResult={setResult}
                loading={loading}
                setLoading={setLoading}
                error={error}
                setError={setError}
              />
            }
          />
          <Route path="/results" element={<ResultsPage result={result} />} />
          <Route path="/logs/:date" element={<LogDetailPage result={result} />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
