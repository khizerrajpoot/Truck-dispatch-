import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

const defaultLocationOptions = [
  'Atlanta, GA',
  'Nashville, TN',
  'Chicago, IL',
  'Dallas, TX',
  'Houston, TX',
  'Miami, FL',
  'New York, NY',
  'Los Angeles, CA',
  'Seattle, WA',
  'Denver, CO',
  'Phoenix, AZ',
  'Charlotte, NC',
];

function LocationSelect({ label, name, value, placeholder, onSelect }) {
  const [query, setQuery] = useState(value || '');
  const [options, setOptions] = useState(
    defaultLocationOptions.map((item, idx) => ({ id: `default-${idx}`, label: item })),
  );
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      const cleaned = query.trim();

      if (!cleaned) {
        setLoadingOptions(false);
        setOptions(defaultLocationOptions.map((item, idx) => ({ id: `default-${idx}`, label: item })));
        return;
      }

      const localFiltered = defaultLocationOptions
        .filter((item) => item.toLowerCase().includes(cleaned.toLowerCase()))
        .map((item, idx) => ({ id: `default-filter-${idx}`, label: item }));
      if (localFiltered.length > 0) {
        setOptions(localFiltered);
      }

      try {
        setLoadingOptions(true);
        const response = await axios.get(NOMINATIM_URL, {
          params: {
            q: cleaned,
            format: 'json',
            limit: 6,
          },
          signal: controller.signal,
          headers: {
            'Accept-Language': 'en',
          },
        });
        setOptions(
          (response.data || []).map((item) => ({
            id: item.place_id,
            label: item.display_name,
          })),
        );
      } catch (error) {
        if (error.name !== 'CanceledError' && error.name !== 'AbortError') {
          setOptions([]);
        }
      } finally {
        setLoadingOptions(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const selectOption = (selected) => {
    setQuery(selected);
    onSelect(name, selected);
    setIsOpen(false);
  };

  return (
    <label className="form-field location-label" ref={rootRef}>
      <span className="field-label">{label}</span>
      <div className="location-select">
        <input
          required
          value={query}
          onChange={(event) => {
            const nextValue = event.target.value;
            setQuery(nextValue);
            onSelect(name, nextValue);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="field-input"
        />
        {isOpen && (
          <div className="location-options">
            {loadingOptions && <div className="location-option muted">Searching...</div>}
            {!loadingOptions && options.length === 0 && query.trim().length > 0 && (
              <div className="location-option muted">No matches found.</div>
            )}
            {!loadingOptions && query.trim().length === 0 && (
              <div className="location-option muted">Choose a suggested location or start typing.</div>
            )}
            {!loadingOptions &&
              options.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className="location-option"
                  onClick={() => selectOption(option.label)}
                >
                  {option.label}
                </button>
              ))}
          </div>
        )}
      </div>
    </label>
  );
}

export default LocationSelect;
