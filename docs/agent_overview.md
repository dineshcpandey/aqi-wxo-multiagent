graph TB
    User[User Query] --> Parser[QueryParser/InstructLabParser]
    Parser --> Router[AgentRouter]
    
    Router --> LocationResolver[LocationResolverAgent]
    LocationResolver --> Disambiguation[DisambiguationAgent]
    
    Router --> PMData[PMDataAgent]
    Router --> Trend[TrendAgent]
    Router --> Compare[ComparisonAgent]
    Router --> Hotspot[HotspotAgent]
    Router --> Forecast[ForecastAgent]
    Router --> Advisory[HealthAdvisoryAgent]
    Router --> Aggregate[AggregateAgent]
    
    PMData --> DB[(PostgreSQL)]
    Trend --> DB
    Compare --> DB
    Hotspot --> DB
    Forecast --> DB
    Advisory --> DB
    Aggregate --> DB
    
    DB --> Response[ResponseFormatter]
    Response --> User