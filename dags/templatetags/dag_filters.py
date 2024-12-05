from django import template
from django.utils.timesince import timesince
from datetime import timedelta
from django.utils import timezone

register = template.Library()

def get_dag_run_color(state):
    """
    Returns a color based on the DAG run state.
    
    :param state: The state of the DAG run
    :return: Color string for the run state
    """
    color_map = {
        'success': 'green',
        'running': 'blue',
        'retry': 'yellow',
        'failed': 'red',
        'queued': 'gray',
        'skipped': 'purple'
    }
    return color_map.get(str(state).lower(), 'lightgray')

@register.filter(name='dag_run_color')
def dag_run_color(state):
    """
    Django template filter for getting DAG run color
    """
    return get_dag_run_color(state)

@register.filter(name='format_duration')
def format_duration(start_date, end_date=None):
    """
    Format the duration between start and end dates.
    
    :param start_date: Start datetime
    :param end_date: End datetime (optional, defaults to current time)
    :return: Formatted duration string
    """
    if not start_date:
        return 'N/A'
    
    if not end_date:
        end_date = timezone.now()
    
    duration = end_date - start_date
    
    # Convert to human-readable format
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

@register.filter(name='dag_status_badge')
def dag_status_badge(dag):
    """
    Generate a status badge for a DAG with multiple states.
    
    :param dag: DAG object
    :return: HTML string for status badge
    """
    if not dag:
        return ''
    
    badge_classes = {
        'active': 'bg-green-100 text-green-800',
        'inactive': 'bg-red-100 text-red-800',
        'paused': 'bg-yellow-100 text-yellow-800'
    }
    
    badges = []
    
    # Active/Inactive status
    status_class = badge_classes['active'] if dag.is_active else badge_classes['inactive']
    status_text = 'Active' if dag.is_active else 'Inactive'
    badges.append(f'<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {status_class}">{status_text}</span>')
    
    # Paused status
    if getattr(dag, 'is_paused', False):
        badges.append(f'<span class="ml-1 px-2 inline-flex text-xs leading-5 font-semibold rounded-full {badge_classes["paused"]}">Paused</span>')
    
    return ' '.join(badges)

@register.filter(name='recent_runs_summary')
def recent_runs_summary(dag_runs):
    """
    Provide a summary of recent DAG runs.
    
    :param dag_runs: Queryset of DAG runs
    :return: Dictionary with run statistics
    """
    if not dag_runs:
        return {
            'total_runs': 0,
            'success_rate': 0,
            'last_run_state': 'No runs'
        }
    
    total_runs = dag_runs.count()
    successful_runs = dag_runs.filter(state='success').count()
    
    return {
        'total_runs': total_runs,
        'success_rate': round((successful_runs / total_runs) * 100, 2),
        'last_run_state': dag_runs.first().state if dag_runs else 'No runs'
    }
