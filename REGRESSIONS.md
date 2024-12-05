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

## DAG Run View Primary Key vs Identifier Mismatch

**Date**: Dec 4, 2024
**Status**: Fixed

### Problem
The DAG run views were using primary keys (id) for lookups instead of business identifiers (dag_id, run_id), causing 404 errors when trying to view DAG runs or individual run details.

### Impact
- Users couldn't view the list of DAG runs
- Run detail links were broken
- "View all runs" functionality was inaccessible

### Root Cause
The views and templates were inconsistently using primary keys (`id`) and business identifiers (`dag_id`, `run_id`):
- Templates were generating URLs with `dag.id` instead of `dag.dag_id`
- Run detail links used `run.id` instead of `run.run_id`
- Cluster context was lost in navigation

### Fix
1. Updated templates to use business identifiers:
   - Changed `dag.id` to `dag.dag_id` in "View all runs" link
   - Updated run detail links to use `run.run_id`
   - Added cluster parameter to maintain context

2. Modified views to handle identifiers consistently:
   - Updated `run_detail` view to use `dag_id` and `run_id`
   - Added proper cluster filtering
   - Improved error handling for missing DAGs

### Prevention
- Establish conventions for using business identifiers vs primary keys
- Add type hints and documentation for identifier usage
- Create integration tests for DAG navigation flows
- Review similar patterns in other views for consistency

## URL Routing Regression - DAG Run Detail View

### Description
A `NoReverseMatch` error occurred when attempting to view DAG run details due to a missing URL pattern.

### Symptoms
- Error: `NoReverseMatch at /dags/example_dag_1/`
- Exception: `Reverse for 'run_detail' not found`
- Request URL: `http://localhost:8000/dags/example_dag_1/?cluster=1`

### Root Cause
The `run_detail` view was not included in the `urlpatterns` in `dags/urls.py`.

### Resolution
Added URL pattern in `dags/urls.py`:
```python
path('<str:dag_id>/runs/<str:run_id>/', views.run_detail, name='run_detail')
```

### Impact
- Prevents accessing detailed DAG run information
- Breaks navigation in the DAG management interface

### Date Identified
December 5, 2024

### Status
Resolved