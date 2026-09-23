# Feature Spec: ATS Resume Tailor & PDF Export

## App Overview
Target Application URL: `http://localhost:3001`
Description: Web interface allowing users to upload a resume, view an automated ATS match score analysis, and export an optimized PDF report.

## Functional Requirements & Test Scenarios

### Scenario 1: Resume Upload & ATS Match Score Analysis
- **Given** the user navigates to `http://localhost:3001`
- **When** the user selects a resume file using file input `#resume-file`
- **And** clicks the analyze button `#analyze-btn`
- **Then** the results section `#results-section` becomes visible
- **And** element `#ats-score` displays exact text `"Match Score: 85%"`

### Scenario 2: Export Optimized PDF Report
- **Given** the ATS match score results section is displayed
- **When** the user clicks the export button `#export-pdf-btn`
- **Then** the application triggers the PDF export request `/api/export-pdf`
- **And** no error message `#error-display` is displayed
