import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import LocationSelect from '../components/LocationSelect';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

function PlannerPage({ formData, setFormData, setResult, loading, setLoading, error, setError }) {
  const navigate = useNavigate();

  const handleFieldChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/trips/plan`, {
        ...formData,
        current_cycle_used_hours: Number(formData.current_cycle_used_hours),
      });
      setResult(response.data);
      navigate('/results');
    } catch (submitError) {
      const message =
        submitError?.response?.data?.detail ||
        'Request failed. Confirm Django server is running on port 8000.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Django + React Assessment</p>
          <h1>HOS Trip Planning Platform</h1>
          <p className="subtitle">
            Plan routes, track compliance events, and generate FMCSA-style daily log sheets with
            downloadable output.
          </p>
        </div>
      </section>

      <section className="card form-card">
        <header className="section-head">
          <h2>Trip Inputs</h2>
          <p>Select locations from search and define current cycle usage.</p>
        </header>

        <form className="form-grid" onSubmit={handleSubmit}>
          <LocationSelect
            label="Current Location"
            name="current_location"
            value={formData.current_location}
            placeholder="Search current location"
            onSelect={handleFieldChange}
          />

          <LocationSelect
            label="Pickup Location"
            name="pickup_location"
            value={formData.pickup_location}
            placeholder="Search pickup location"
            onSelect={handleFieldChange}
          />

          <LocationSelect
            label="Dropoff Location"
            name="dropoff_location"
            value={formData.dropoff_location}
            placeholder="Search dropoff location"
            onSelect={handleFieldChange}
          />

          <label className="form-field">
            <span className="field-label">Current Cycle Used (Hours out of 70)</span>
            <input
              required
              min="0"
              max="70"
              step="0.25"
              type="number"
              name="current_cycle_used_hours"
              value={formData.current_cycle_used_hours}
              onChange={(event) => handleFieldChange(event.target.name, event.target.value)}
              placeholder="20"
              className="field-input"
            />
          </label>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Planning Trip...' : 'Generate Plan'}
          </button>
        </form>

        {error && <p className="error-banner">{error}</p>}
      </section>
    </>
  );
}

export default PlannerPage;
