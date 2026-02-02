import psutil
import time

class ProcessMonitor:
    """
    Top Process Monitor.
    Tracks Top 3 processes by CPU.
    Handles 'priming' (first call to cpu_percent returns 0).
    """
    def __init__(self):
        # Cache Process objects to reuse and maintain cpu_percent state
        # Key: PID, Value: psutil.Process object
        self._process_cache = {}
        
    def get_top_processes(self, limit=3):
        """
        Get top resource-consuming processes.
        Primes CPU counters to ensure meaningful data.
        """
        process_stats = []
        current_pids = set()
        
        try:
            # Iterate over all running processes
            # Iterate over all running processes
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    pid = proc.info['pid']
                    
                    # 1. Filter Filtering (Skip Idle/System)
                    # Do this early to avoid processing
                    if proc.info['name'] == 'System Idle Process' or pid == 0:
                        continue
                        
                    current_pids.add(pid)
                    
                    # Manage Cache
                    if pid not in self._process_cache:
                        self._process_cache[pid] = proc
                        # Prime CPU counter (returns 0.0 first time)
                        try:
                            proc.cpu_percent(interval=None)
                        except:
                            pass
                    
                    cached_proc = self._process_cache[pid]
                    
                    # Get CPU (non-blocking, uses time since last call)
                    try:
                        cpu_percent = cached_proc.cpu_percent(interval=None)
                    except:
                        cpu_percent = 0.0
                        
                    # Normalize CPU Percentage (0-100% scale)
                    try:
                        cpu_count = psutil.cpu_count() or 1
                        cpu_percent = round(cpu_percent / cpu_count, 1)
                    except:
                        pass
                        
                    # Get Memory
                    try:
                        memory_mb = round(proc.info['memory_info'].rss / (1024 * 1024), 1)
                    except:
                        memory_mb = 0.0
                        
                    process_stats.append({
                        "pid": pid,
                        "name": proc.info['name'],
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            dead_pids = set(self._process_cache.keys()) - current_pids
            for pid in dead_pids:
                del self._process_cache[pid]
                
            # Sort: Primary = CPU desc, Secondary = Memory desc
            # Filter out 0.0 CPU to reduce noise (optional, but requested "Top Consumers")
            process_stats.sort(key=lambda x: (x['cpu_percent'], x['memory_mb']), reverse=True)
            
            return process_stats[:limit]
            
        except Exception:
            # Fail safe
            return []
