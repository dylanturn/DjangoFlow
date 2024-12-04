# DjangoFlow Regressions

## Navigation Menu Regressions

### 2024-01-08: Monitoring Dropdown Alignment
- **Issue**: After implementing Flowbite's dropdown component for better usability, the monitoring menu item was not aligned with other navigation items
- **Fix**: Added `h-16` class to the dropdown button to match the height of other navigation items
- **Files Changed**: 
  - `templates/base.html`: Updated monitoring dropdown button styling
- **Impact**: Visual inconsistency in navigation menu
- **Resolution**: Alignment fixed by matching button height with other navigation items

## URL Pattern Naming Inconsistency in DAG Views

**Date**: Dec 4, 2024
**Status**: Fixed

### Problem
The DAG views had inconsistent URL pattern naming, causing "NoReverseMatch" errors when navigating between DAG-related pages. The URL pattern was named 'details' in some places and referenced as 'detail' in others.

### Impact
- Users couldn't navigate between DAG list, details, and runs views
- "View all runs" link was broken
- DAG list page failed to load
- Navigation back to DAG details from runs view failed

### Root Cause
Inconsistent naming of URL patterns in `urls.py` and templates. The URL pattern was defined as 'details' but templates were trying to reference it as 'detail' (or vice versa in some cases).

### Fix
1. Standardized URL pattern name to 'detail' in `urls.py`
2. Updated all template references to use 'dags:detail' consistently:
   - Updated `templates/dags/list.html`
   - Updated `templates/dags/runs.html`
   - Updated `templates/dags/details.html`
3. Updated view functions to use consistent parameter handling for `dag_id` and `cluster_id`

### Prevention
- Implement URL pattern name constants to prevent typos
- Add tests for URL pattern resolution
- Review URL pattern naming conventions in documentation