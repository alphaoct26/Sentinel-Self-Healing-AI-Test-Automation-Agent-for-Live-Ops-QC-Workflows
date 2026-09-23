# Feature Spec: Live Leaderboard & Match Stats Export

## App Overview
Target Application URL: `http://localhost:3001`
Description: Live-service game web dashboard displaying real-time player rankings, top rank tier status, and match performance report exports.

## Functional Requirements & Test Scenarios

### Scenario 1: Refresh Leaderboard & Rank Tier Verification
- **Given** the user navigates to `http://localhost:3001`
- **When** the user clicks the refresh leaderboard button `#refresh-btn`
- **Then** the results section `#results-section` becomes visible
- **And** element `#rank-badge` displays exact text `"Top Rank: Elite"`

### Scenario 2: Export Match Report
- **Given** the live leaderboard results section is displayed
- **When** the user clicks the export match report button `#export-btn`
- **Then** the application triggers the match report export request `/api/export-pdf`
- **And** no error message `#error-display` is displayed
