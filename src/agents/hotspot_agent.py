# Pollution hotspot detection agent
# src/agents/hotspot_agent.py
from typing import Dict, Any, List, Optional
from .agent_base import AgentBase

class HotspotAgent(AgentBase):
    """Agent for identifying pollution hotspots"""
    
    def __init__(self, db_connection):
        super().__init__(name="HotspotAgent")
        self.db = db_connection
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find pollution hotspots
        Expected input:
        - region_code: Optional region to limit search
        - metric: 'pm25', 'aqi', etc.
        - threshold: Minimum value to consider as hotspot
        - limit: Max number of hotspots to return
        """
        region_code = input_data.get('region_code')
        metric = input_data.get('metric', 'pm25')
        threshold = input_data.get('threshold')
        limit = input_data.get('limit', 20)
        
        # Default thresholds based on metric
        if threshold is None:
            threshold = self._get_default_threshold(metric)
        
        self.log(f"Finding {metric} hotspots > {threshold}")
        
        try:
            result = await self.db.execute_query(
                "SELECT * FROM gis.find_hotspots($1, $2, $3, $4)",
                [region_code, metric, threshold, limit]
            )
            
            if not result:
                return {
                    "success": True,
                    "hotspots": [],
                    "message": "No hotspots found above threshold"
                }
            
            # Group by clusters
            clusters = self._group_by_clusters(result)
            
            # Calculate severity distribution
            severity_dist = self._calculate_severity_distribution(result)
            
            return {
                "success": True,
                "hotspots": result,
                "clusters": clusters,
                "statistics": {
                    "total_hotspots": len(result),
                    "clusters_found": len(clusters),
                    "avg_value": sum(h['metric_value'] for h in result) / len(result),
                    "max_value": max(h['metric_value'] for h in result),
                    "severity_distribution": severity_dist
                },
                "metadata": {
                    "metric": metric,
                    "threshold": threshold,
                    "region": region_code
                }
            }
            
        except Exception as e:
            return self.handle_error(e, input_data)
    
    def _get_default_threshold(self, metric: str) -> float:
        """Get default threshold for hotspot detection"""
        thresholds = {
            'pm25': 90,    # Poor category
            'pm10': 150,
            'aqi': 200,    # Unhealthy
            'no2': 80,
            'so2': 80,
            'co': 10,
            'o3': 168
        }
        return thresholds.get(metric, 100)
    
    def _group_by_clusters(self, hotspots: List[Dict]) -> List[Dict]:
        """Group hotspots by cluster ID"""
        clusters = {}
        
        for hotspot in hotspots:
            cluster_info = hotspot.get('cluster_info', {})
            cluster_id = cluster_info.get('cluster_id')
            
            if cluster_id not in clusters:
                clusters[cluster_id] = {
                    'cluster_id': cluster_id,
                    'hotspots': [],
                    'center_lat': 0,
                    'center_lon': 0,
                    'max_value': 0,
                    'avg_value': 0
                }
            
            clusters[cluster_id]['hotspots'].append(hotspot)
        
        # Calculate cluster statistics
        for cluster in clusters.values():
            hotspots = cluster['hotspots']
            cluster['center_lat'] = sum(h['latitude'] for h in hotspots) / len(hotspots)
            cluster['center_lon'] = sum(h['longitude'] for h in hotspots) / len(hotspots)
            cluster['max_value'] = max(h['metric_value'] for h in hotspots)
            cluster['avg_value'] = sum(h['metric_value'] for h in hotspots) / len(hotspots)
            cluster['size'] = len(hotspots)
        
        return list(clusters.values())
    
    def _calculate_severity_distribution(self, hotspots: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of severity levels"""
        distribution = {
            'severe': 0,
            'very_poor': 0,
            'poor': 0,
            'moderate': 0
        }
        
        for hotspot in hotspots:
            severity = hotspot.get('severity', 'moderate')
            if severity in distribution:
                distribution[severity] += 1
        
        return distribution