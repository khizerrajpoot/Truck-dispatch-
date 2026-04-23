# HOS Trip Planner \- Assessment Presentation Guide

This document helps you present the project clearly to both technical and non-technical reviewers.

---

## 1\) Project Overview

The app is a full-stack **Hours of Service (HOS) Trip Planner** built with:

- **Backend:** Django \+ Django REST Framework  
- **Frontend:** React \+ Vite \+ React Router \+ Leaflet  
- **Routing/Map Data:** OpenStreetMap Nominatim (geocoding) \+ OSRM (route \+ instructions)

### Business goal

Given:

- Current location  
- Pickup location  
- Dropoff location  
- Current cycle used hours

The system returns:

- Route map and turn-by-turn instructions  
- Compliance-relevant stops/rests  
- Duty timeline  
- Daily ELD log sheets (auto-generated, including multi-day trips)

---

## 2\) Assumptions Implemented

The logic follows the assessment assumptions:

- Property-carrying driver  
- 70 hours / 8 days cycle  
- No adverse driving condition extension  
- Fuel stop at least once every 1,000 miles  
- 1 hour pickup and 1 hour dropoff on-duty not-driving

---

## 3\) Architecture

## Backend (`hos-backend`)

### Main API endpoint

- `POST /api/trips/plan`

### Key backend files

- `trip_planner/serializers.py`  
  - Validates request payload fields.  
- `trip_planner/views.py`  
  - Receives request, validates, calls planner service, returns JSON.  
- `trip_planner/services.py`  
  - Core engine for:  
    - Geocoding  
    - Route fetching  
    - HOS simulation  
    - Timeline creation  
    - Daily log data generation

### Core HOS rules enforced

- 11-hour driving limit  
- 14-hour duty window  
- 30-minute break after 8 cumulative driving hours  
- 70-hour/8-day cycle limit  
- 34-hour restart support when needed  
- Daily reset behavior

---

## Frontend (`hos-frontend`)

### Routes

- `/` \-\> Planner page (inputs)  
- `/results` \-\> Results dashboard  
- `/logs/:date` \-\> Detailed daily log sheet page

### Key frontend files

- `src/pages/PlannerPage.jsx`  
  - Input form and API submission.  
- `src/pages/ResultsPage.jsx`  
  - Map, instructions, stops/rests, and timeline.  
- `src/pages/LogDetailPage.jsx`  
  - Full detailed canvas log per day.  
- `src/components/LogSheetCanvas.jsx`  
  - Draws professional ELD-style sheets on HTML canvas.  
- `src/components/LocationSelect.jsx`  
  - Searchable location component with immediate options.

---

## 4\) End-to-End Flow (What happens on submit)

1. User enters current, pickup, dropoff, and cycle-used hours.  
2. Frontend sends request to Django API.  
3. Backend validates payload.  
4. Backend geocodes locations.  
5. Backend fetches route legs and instructions from OSRM.  
6. HOS engine simulates trip progression:  
   - Adds required breaks/resets/fuel stops  
   - Tracks duty and cycle limits  
7. Backend creates:  
   - Route summary \+ instructions  
   - Stops and rests list  
   - Duty timeline  
   - Per-day log-sheet data  
8. Frontend renders results and map.  
9. User opens each generated day log on `/logs/:date`, and can download PNG.

---

## 5\) Demo Script (3-5 minutes Loom)

Use this exact sequence for a clean presentation.

### 0:00 \- 0:30 Introduction

- Briefly explain the objective: automate route \+ HOS compliance \+ log creation.  
- Mention stack: Django \+ React.

### 0:30 \- 1:30 Planner Input

- Show planner form.  
- Enter a realistic long trip to trigger multi-day behavior.  
- Explain `current_cycle_used_hours` and why it matters.

### 1:30 \- 2:45 Results Dashboard

- Show route metrics (distance, duration, days).  
- Show map with route polyline and markers.  
- Show turn-by-turn instructions.  
- Show Stops & Rests and explain why each appears (break/reset/fuel/operations).  
- Show duty timeline.

### 2:45 \- 3:45 Daily Logs

- Open 1-2 daily logs.  
- Point out:  
  - Duty graph continuity  
  - Proper totals  
  - Driver/carrier/trip metadata  
  - Download image option

### 3:45 \- 4:30 Engineering Notes

- Show backend service file and explain rule enforcement.  
- Mention regression script and test coverage areas.

### 4:30 \- 5:00 Wrap-up

- Mention known constraints and next steps (production hardening, persistence, auth, hosted env vars).

---

## 6\) API Contract (Quick Reference)

### Request

{

  "current\_location": "Atlanta, GA",

  "pickup\_location": "Dallas, TX",

  "dropoff\_location": "Phoenix, AZ",

  "current\_cycle\_used\_hours": 52.5

}

### Response (high-level sections)

- `trip_inputs`  
- `assumptions`  
- `route`  
- `timeline`  
- `stops_and_rests`  
- `daily_logs`

---

## 7\) Testing and Validation

### Automated checks

- Backend unit tests in `hos-backend/trip_planner/tests.py`  
- Regression suite in `hos-backend/scripts/regression_api_tests.py`

### Regression highlights

- Happy path  
- 8-hour break trigger  
- 11h/14h reset trigger  
- 70h cycle limit behavior  
- Fuel stop behavior  
- Validation failures (bad cycle, missing fields, bad geocode)

---

## 8\) What to Emphasize to Evaluators

- This is not just UI rendering; it includes a rule-driven HOS simulation engine.  
- Output is actionable and traceable:  
  - Route \+ instructions  
  - Compliance events  
  - Duty timeline  
  - Daily logs  
- The app is modular:  
  - Clear backend service boundaries  
  - Reusable frontend components  
  - Route-based UX for clarity

---

## 9\) Known Gaps / Honest Notes

If asked about limitations, answer confidently:

- External map/routing APIs may vary in precision by location quality.  
- App currently assumes fixed rules from the assessment; no profile switching (passenger/adverse/split sleeper modes).  
- Data persistence across refresh for generated results can be improved (local storage/backend persistence).  
- Production deployment requires environment-specific API URLs and tighter CORS/security config.

---

## 10\) Quick Run Commands

### Backend

cd hos-backend

python3 \-m venv venv

source venv/bin/activate

pip install \-r requirements.txt

python manage.py migrate

python manage.py runserver

### Frontend

cd hos-frontend

npm install

npm run dev

---

## 11\) Final Presentation Checklist

- [ ] Backend server running  
- [ ] Frontend running  
- [ ] One demo trip prepared in notes  
- [ ] One long-distance trip prepared to show multi-day logs  
- [ ] Regression script output screenshot ready  
- [ ] GitHub repo link ready  
- [ ] Hosted frontend/backend links ready  
- [ ] Loom recorded and reviewed once before submission

