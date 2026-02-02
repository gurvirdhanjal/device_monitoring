from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from statistics import mean
from .normalizer import Metric

def get_cutoff_time(time_range: str) -> datetime:
    """
    Calculate the cutoff datetime based on the time range string.
    
    Args:
        time_range: String indicating range (e.g., 'last_1h', 'last_24h', 'last_7d')
        
    Returns:
        datetime object for the cutoff time
    """
    now = datetime.now()
    if time_range == "last_1h":
        return now - timedelta(hours=1)
    elif time_range == "last_24h":
        return now - timedelta(hours=24)
    elif time_range == "last_7d":
        return now - timedelta(days=7)
    elif time_range == "last_30d":
        return now - timedelta(days=30)
    
    # Default to 24h if unknown
    return now - timedelta(hours=24)

def aggregate_metrics(metrics: List[Metric]) -> Dict[str, Any]:
    """
    Aggregate a list of metrics into summary statistics.
    
    Args:
        metrics: List of Metric objects
        
    Returns:
        Dictionary containing summary stats (min, max, avg) and data points
    """
    if not metrics:
        return {
            "summary": {"min": 0, "max": 0, "avg": 0},
            "data": []
        }
    
    # Extract values
    values = [m.value for m in metrics]
    
    # Calculate stats
    # Check for empty values to avoid errors (though check above handles empty list)
    summary = {
        "min": min(values),
        "max": max(values),
        "avg": mean(values)
    }
    
    # Serialize data points for the graph
    data_points = [
        {
            "timestamp": m.timestamp.isoformat(),
            "value": m.value
        }
        for m in metrics
    ]
    
    return {
        "summary": summary,
        "data": data_points
    }
