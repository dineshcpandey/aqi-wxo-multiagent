from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PMQueryState:
    """State object for PM2.5 query workflow"""
    
    # Input
    raw_query: str = ""
    
    # Parsing stage
    parsed_intent: str = ""
    parsed_entities: Dict[str, Any] = field(default_factory=dict)
    parse_confidence: float = 0.0
    parse_error: Optional[str] = None
    
    # Location resolution stage
    location_query: str = ""
    resolved_locations: List[Dict[str, Any]] = field(default_factory=list)
    needs_disambiguation: bool = False
    selected_location: Optional[Dict[str, Any]] = None
    location_error: Optional[str] = None
    
    # Data retrieval stage
    pm25_value: Optional[float] = None
    pm25_timestamp: Optional[datetime] = None
    station_count: Optional[int] = None
    measurement_type: Optional[str] = None
    data_error: Optional[str] = None
    
    # Response stage
    formatted_response: str = ""
    health_category: str = ""
    response_error: Optional[str] = None
    
    # Workflow metadata
    current_step: str = "initialized"
    workflow_complete: bool = False
    workflow_error: Optional[str] = None
    processing_time_ms: int = 0
    
    def set_error(self, step: str, error: str):
        """Set error for a specific step"""
        setattr(self, f"{step}_error", error)
        self.workflow_error = f"Error in {step}: {error}"
        self.current_step = f"{step}_error"
    
    def is_successful(self) -> bool:
        """Check if workflow completed successfully"""
        return (
            self.workflow_complete and 
            not self.workflow_error and
            self.pm25_value is not None
        )