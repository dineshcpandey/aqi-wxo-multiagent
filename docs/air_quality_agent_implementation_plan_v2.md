# Air Quality Q&A Agent Implementation Plan

## Executive Summary
Build a production-ready Q&A agent system for the Air Quality Monitoring Database using LangGraph orchestration, with progressive enhancement from rule-based patterns to LLM-powered queries, collecting data for future SLM training.

**Timeline:** 8 weeks to production  
**Approach:** Agent-first, SLM later  
**Technology:** LangGraph + LangChain + PostgreSQL/TimescaleDB  
**Cost:** ~$100-200/month initially, dropping to $20-30/month with optimization

---

## Phase 1: Foundation (Week 1-2)
### Goal: Basic working system with core query patterns

#### Week 1: Infrastructure Setup

**Day 1-2: Environment & Dependencies**
```bash
# Create project structure
air-quality-agent/
├── src/
│   ├── agents/
│   ├── tools/
│   ├── graphs/
│   └── utils/
├── config/
├── tests/
├── logs/
└── requirements.txt
```

```python
# requirements.txt
langgraph==0.0.32
langchain==0.1.0
langchain-openai==0.0.5
asyncpg==0.29.0
pydantic==2.5.0
python-dotenv==1.0.0
fastapi==0.108.0
pytest==7.4.0
```

**Day 3-4: Database Connection Layer**
```python
# src/utils/database.py
import asyncpg
from typing import List, Dict, Any

class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(self.connection_string)
    
    async def execute_query(self, sql: str, params: List = None) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *(params or []))
            return [dict(row) for row in rows]
    
    async def get_data_sources(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT code, name, source_type, readings_table_name 
        FROM master.data_sources 
        WHERE is_active = true
        """
        return await self.execute_query(sql)
```

**Day 5: Core Tool Implementation**
```python
# src/tools/basic_tools.py
from langchain.tools import Tool
from typing import Optional

class CurrentReadingsTool(Tool):
    name = "get_current_readings"
    description = "Fetch latest sensor readings for specified locations and metrics"
    
    def _run(self, source: str, location: Optional[str] = None, metric: Optional[str] = None):
        sql = f"""
        SELECT *
        FROM aq.current_readings_{source}
        WHERE 1=1
        """
        if location:
            sql += f" AND (district = '{location}' OR location_name LIKE '%{location}%')"
        if metric:
            sql = sql.replace("*", metric)
        sql += " ORDER BY timestamp DESC LIMIT 10"
        
        return self.db.execute_query(sql)
```

#### Week 2: LangGraph Integration

**Day 1-2: Basic Graph Structure**
```python
# src/graphs/query_graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class QueryState(TypedDict):
    user_query: str
    intent: str
    entities: dict
    sql: str
    results: List[dict]
    error: str
    formatted_response: str

class QueryGraph:
    def __init__(self, db_connection):
        self.db = db_connection
        self.workflow = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(QueryState)
        
        # Add nodes
        workflow.add_node("classify", self.classify_intent)
        workflow.add_node("extract", self.extract_entities)
        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute", self.execute_query)
        workflow.add_node("format", self.format_response)
        
        # Set flow
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "extract")
        workflow.add_edge("extract", "generate_sql")
        workflow.add_edge("generate_sql", "execute")
        workflow.add_edge("execute", "format")
        workflow.add_edge("format", END)
        
        return workflow.compile()
```

**Day 3-4: Pattern Matching System**
```python
# src/agents/pattern_matcher.py
import re
from typing import Dict, Tuple, Optional

class QueryPatternMatcher:
    def __init__(self):
        self.patterns = {
            'current_reading': [
                (r"what(?:'s| is) the (?:current )?(\w+) in (\w+)", ["metric", "location"]),
                (r"show me (?:current )?(\w+) for (\w+)", ["metric", "location"])
            ],
            'time_series': [
                (r"(\w+) trend for (?:the )?last (\d+) (\w+)", ["metric", "duration", "unit"]),
            ],
            'hotspot': [
                (r"(?:show |find )?hotspots in (\w+)", ["location"]),
            ]
        }
    
    def match(self, query: str) -> Tuple[str, Dict[str, str]]:
        query_lower = query.lower()
        
        for intent, patterns in self.patterns.items():
            for pattern, param_names in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    params = dict(zip(param_names, match.groups()))
                    return intent, params
        
        return "unknown", {}
```

**Day 5: SQL Template Engine**
```python
# src/utils/sql_templates.py
class SQLTemplateEngine:
    def __init__(self):
        self.templates = {
            'current_reading': """
                SELECT {columns}
                FROM aq.current_readings_{source}
                WHERE {conditions}
                ORDER BY timestamp DESC
                LIMIT 1
            """,
            'time_series': """
                SELECT 
                    date_trunc('{interval}', timestamp) as period,
                    AVG({metric}) as avg_{metric},
                    MAX({metric}) as max_{metric},
                    MIN({metric}) as min_{metric},
                    COUNT(*) as reading_count
                FROM aq.readings_{source}
                WHERE timestamp >= NOW() - INTERVAL '{duration}'
                GROUP BY period
                ORDER BY period DESC
            """,
            'hotspot': """
                SELECT 
                    latitude, longitude,
                    pm25_value,
                    severity,
                    cluster_size,
                    locality_name
                FROM aq.hotspots_hotspot_xgb
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    {location_filter}
                ORDER BY pm25_value DESC
                LIMIT 20
            """
        }
```

### Checkpoint: End of Week 2
- [ ] Basic query patterns working (5-10 patterns)
- [ ] Database connection established
- [ ] Simple API endpoint functional
- [ ] Can answer: "What is the current PM2.5 in Delhi?"
- [ ] Logging system capturing all queries

---

## Phase 2: Intelligence Layer (Week 3-4)
### Goal: Add LLM fallback and complex query handling

#### Week 3: LLM Integration

**Day 1-2: OpenAI Integration**
```python
# src/agents/llm_handler.py
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class LLMQueryHandler:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            max_tokens=500
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert for an air quality database.
            Available tables: {tables}
            Available columns: {columns}
            Generate SQL for the user's query."""),
            ("user", "{query}")
        ])
    
    async def generate_sql(self, query: str, context: dict) -> str:
        response = await self.llm.ainvoke(
            self.prompt.format_messages(
                query=query,
                tables=context['tables'],
                columns=context['columns']
            )
        )
        return self.extract_sql(response.content)
```

**Day 3-4: Hybrid Router**
```python
# src/agents/hybrid_router.py
class HybridQueryRouter:
    def __init__(self, pattern_matcher, llm_handler):
        self.pattern_matcher = pattern_matcher
        self.llm_handler = llm_handler
        self.confidence_threshold = 0.85
    
    async def route_query(self, query: str) -> Dict:
        # Try pattern matching first (fast, free)
        intent, params = self.pattern_matcher.match(query)
        
        if intent != "unknown":
            return {
                "method": "pattern",
                "intent": intent,
                "params": params,
                "confidence": 1.0
            }
        
        # Fall back to LLM (slower, costs money)
        return await self.llm_handler.process(query)
```

**Day 5: Complex Query Support**
```python
# src/graphs/complex_query_graph.py
class ComplexQueryGraph(QueryGraph):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        
    async def handle_comparison_query(self, state: QueryState):
        """Handle queries like: Compare PM2.5 between Delhi and Mumbai"""
        # Extract locations
        locations = state['entities']['locations']
        metric = state['entities']['metric']
        
        # Generate multiple SQLs
        sqls = []
        for location in locations:
            sql = f"""
            SELECT 
                '{location}' as location,
                AVG({metric}) as avg_value,
                MAX({metric}) as max_value
            FROM aq.current_readings_aqcn
            WHERE district = '{location}'
                AND timestamp >= NOW() - INTERVAL '24 hours'
            """
            sqls.append(sql)
        
        state['sql'] = " UNION ALL ".join(sqls)
        return state
```

#### Week 4: Advanced Features

**Day 1-2: Caching Layer**
```python
# src/utils/cache.py
import hashlib
import json
from datetime import datetime, timedelta

class QueryCache:
    def __init__(self, ttl_minutes=60):
        self.ttl = timedelta(minutes=ttl_minutes)
        
    async def get_cached_result(self, query: str) -> Optional[Dict]:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        sql = """
        SELECT result, created_at
        FROM cache.query_results
        WHERE query_hash = $1
            AND created_at > NOW() - INTERVAL '{} minutes'
        """.format(self.ttl.total_seconds() / 60)
        
        result = await self.db.execute_query(sql, [query_hash])
        if result:
            return json.loads(result[0]['result'])
        return None
    
    async def cache_result(self, query: str, result: Dict):
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        sql = """
        INSERT INTO cache.query_results (query_hash, query_text, result, ttl_minutes)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (query_hash) 
        DO UPDATE SET result = $3, created_at = NOW()
        """
        
        await self.db.execute_query(
            sql, 
            [query_hash, query, json.dumps(result), self.ttl.total_seconds() / 60]
        )
```

**Day 3-4: Error Handling & Recovery**
```python
# src/utils/error_handler.py
class QueryErrorHandler:
    def __init__(self):
        self.error_patterns = {
            "column .* does not exist": "The metric '{metric}' is not available",
            "relation .* does not exist": "Data source '{source}' not found",
            "syntax error": "Query could not be understood"
        }
    
    def handle_error(self, error: Exception, context: Dict) -> Dict:
        error_msg = str(error)
        
        for pattern, user_message in self.error_patterns.items():
            if re.search(pattern, error_msg, re.IGNORECASE):
                return {
                    "success": False,
                    "message": user_message.format(**context),
                    "suggestion": self.get_suggestion(pattern, context)
                }
        
        return {
            "success": False,
            "message": "An unexpected error occurred",
            "technical_details": error_msg
        }
```

**Day 5: Testing & Documentation**
```python
# tests/test_query_patterns.py
import pytest

test_cases = [
    ("What is the current PM2.5 in Delhi?", "current_reading", {"metric": "pm25", "location": "delhi"}),
    ("Show me hourly trends for last 24 hours", "time_series", {"duration": "24", "unit": "hours"}),
    ("Find hotspots in Mumbai", "hotspot", {"location": "mumbai"}),
]

@pytest.mark.parametrize("query,expected_intent,expected_params", test_cases)
def test_pattern_matching(query, expected_intent, expected_params):
    matcher = QueryPatternMatcher()
    intent, params = matcher.match(query)
    assert intent == expected_intent
    assert params == expected_params
```

### Checkpoint: End of Week 4
- [ ] LLM fallback working for unknown patterns
- [ ] Complex queries (comparisons, aggregations) supported
- [ ] Caching reducing database load by 30-40%
- [ ] Error messages user-friendly
- [ ] 90% of common queries handled successfully

---

## Phase 3: Production Readiness (Week 5-6)
### Goal: API, monitoring, and performance optimization

#### Week 5: API & Integration

**Day 1-2: FastAPI Implementation**
```python
# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Air Quality Q&A Agent")

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    cache: bool = True

class QueryResponse(BaseModel):
    success: bool
    data: Optional[dict]
    message: Optional[str]
    query_metadata: dict

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # Check cache if enabled
        if request.cache:
            cached = await cache.get_cached_result(request.query)
            if cached:
                return QueryResponse(
                    success=True,
                    data=cached,
                    query_metadata={"source": "cache"}
                )
        
        # Process query
        result = await query_graph.process(request.query)
        
        # Cache result
        if request.cache:
            await cache.cache_result(request.query, result)
        
        # Log for future SLM training
        await logger.log_query(request.query, result)
        
        return QueryResponse(
            success=True,
            data=result,
            query_metadata={"source": "computed"}
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            message=str(e),
            query_metadata={"error": True}
        )
```

**Day 3-4: Monitoring & Logging**
```python
# src/utils/monitoring.py
import time
from dataclasses import dataclass
from datetime import datetime

@dataclass
class QueryMetrics:
    query: str
    intent: str
    execution_time_ms: float
    sql_generated: str
    row_count: int
    cache_hit: bool
    llm_used: bool
    error: Optional[str]

class QueryMonitor:
    def __init__(self):
        self.metrics_table = "logs.query_metrics"
    
    async def log_query(self, metrics: QueryMetrics):
        sql = """
        INSERT INTO logs.query_metrics 
        (query, intent, execution_time_ms, sql_generated, 
         row_count, cache_hit, llm_used, error, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        """
        
        await self.db.execute_query(sql, [
            metrics.query,
            metrics.intent,
            metrics.execution_time_ms,
            metrics.sql_generated,
            metrics.row_count,
            metrics.cache_hit,
            metrics.llm_used,
            metrics.error
        ])
    
    async def get_performance_stats(self):
        sql = """
        SELECT 
            COUNT(*) as total_queries,
            AVG(execution_time_ms) as avg_time_ms,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*) as cache_hit_rate,
            SUM(CASE WHEN llm_used THEN 1 ELSE 0 END)::float / COUNT(*) as llm_usage_rate,
            SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END)::float / COUNT(*) as error_rate
        FROM logs.query_metrics
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """
        
        return await self.db.execute_query(sql)
```

**Day 5: Performance Optimization**
```python
# src/utils/optimizer.py
class QueryOptimizer:
    def __init__(self):
        self.common_queries = {}
        self.load_common_patterns()
    
    async def load_common_patterns(self):
        """Load frequently used queries for optimization"""
        sql = """
        SELECT 
            query,
            COUNT(*) as frequency,
            AVG(execution_time_ms) as avg_time
        FROM logs.query_metrics
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY query
        HAVING COUNT(*) > 5
        ORDER BY COUNT(*) DESC
        """
        
        results = await self.db.execute_query(sql)
        for row in results:
            self.common_queries[row['query']] = {
                'frequency': row['frequency'],
                'avg_time': row['avg_time']
            }
    
    def should_create_materialized_view(self, pattern: str) -> bool:
        """Determine if a pattern warrants a materialized view"""
        if pattern in self.common_queries:
            freq = self.common_queries[pattern]['frequency']
            avg_time = self.common_queries[pattern]['avg_time']
            
            # If used >20 times/day and takes >500ms
            if freq > 140 and avg_time > 500:
                return True
        return False
```

#### Week 6: Data Collection for SLM

**Day 1-2: Training Data Collection**
```python
# src/training/data_collector.py
class TrainingDataCollector:
    def __init__(self):
        self.min_confidence_for_training = 4  # User rating 4-5
    
    async def collect_successful_queries(self):
        """Collect queries that users marked as successful"""
        sql = """
        SELECT 
            user_query,
            intent,
            entities,
            generated_sql,
            result_count,
            user_rating,
            corrected_sql
        FROM training.query_logs
        WHERE user_rating >= $1
            OR corrected_sql IS NOT NULL
        """
        
        return await self.db.execute_query(sql, [self.min_confidence_for_training])
    
    async def generate_training_dataset(self):
        """Generate dataset for future SLM training"""
        queries = await self.collect_successful_queries()
        
        dataset = []
        for query in queries:
            # Use corrected SQL if available, otherwise generated
            sql = query['corrected_sql'] or query['generated_sql']
            
            dataset.append({
                "input": query['user_query'],
                "intent": query['intent'],
                "entities": query['entities'],
                "output_sql": sql,
                "metadata": {
                    "user_rating": query['user_rating'],
                    "result_count": query['result_count']
                }
            })
        
        # Save to file for future training
        with open('training_data.jsonl', 'w') as f:
            for item in dataset:
                f.write(json.dumps(item) + '\n')
        
        return len(dataset)
```

**Day 3-4: Feedback Loop**
```python
# src/api/feedback.py
@app.post("/feedback")
async def submit_feedback(
    query_id: str,
    rating: int,
    corrected_sql: Optional[str] = None,
    comments: Optional[str] = None
):
    """Collect user feedback for improving the system"""
    
    sql = """
    UPDATE training.query_logs
    SET 
        user_rating = $2,
        corrected_sql = $3,
        user_comments = $4,
        feedback_timestamp = NOW()
    WHERE query_id = $1
    """
    
    await db.execute_query(sql, [query_id, rating, corrected_sql, comments])
    
    # If rating is low, flag for review
    if rating <= 2:
        await alert_admin(f"Low rating for query {query_id}: {comments}")
    
    return {"status": "feedback_received"}
```

**Day 5: Documentation & Handover**
```markdown
# API Documentation

## Endpoints

### POST /query
Process a natural language query

**Request:**
```json
{
    "query": "What is the current PM2.5 in Delhi?",
    "cache": true
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "results": [...],
        "query_type": "current_reading",
        "execution_time_ms": 45
    }
}
```

### GET /health
System health check

### GET /metrics
Performance metrics

### POST /feedback
Submit query feedback
```

### Checkpoint: End of Week 6
- [ ] API deployed and accessible
- [ ] Monitoring dashboard showing key metrics
- [ ] 1000+ queries collected for future SLM training
- [ ] Performance optimized (avg response <200ms)
- [ ] Documentation complete

---

## Phase 4: Optimization & Scaling (Week 7-8)
### Goal: Optimize costs and prepare for SLM integration

#### Week 7: Cost Optimization

**Implement Tiered Query Processing:**
1. Pattern matching (free, <50ms)
2. Cached results (free, <10ms)
3. Template-based SQL (free, <100ms)
4. LLM generation ($0.002/query, <500ms)

**Expected Cost Reduction:**
- 60% queries handled by patterns → $0
- 20% served from cache → $0
- 15% template-based → $0
- 5% require LLM → ~$50/month

#### Week 8: Future SLM Preparation

**Prepare Training Pipeline:**
```python
# src/training/prepare_slm.py
class SLMPreparation:
    def analyze_readiness(self):
        """Check if we have enough data for SLM training"""
        
        metrics = {
            "total_queries": self.get_query_count(),
            "unique_patterns": self.get_unique_patterns(),
            "success_rate": self.get_success_rate(),
            "coverage": self.get_pattern_coverage()
        }
        
        # Need at least 10K successful queries
        if metrics["total_queries"] > 10000 and metrics["success_rate"] > 0.9:
            return "Ready for SLM training"
        else:
            return f"Need more data: {metrics}"
```

---

## Multi-Agent Architecture (Advanced Implementation)

### Overview: Specialized Agent Decomposition

Instead of a monolithic query handler, implement specialized agents that work together. This approach provides better scalability, maintainability, and accuracy.

### Why Multi-Agent Architecture?

**Benefits:**
1. **Single Responsibility** - Each agent masters ONE domain
2. **Parallel Development** - Teams can work independently
3. **Better Testing** - Test each agent in isolation
4. **Reusability** - Agents can be used across workflows
5. **Progressive Enhancement** - Start with 2 agents, add more as needed
6. **Cleaner SLM Training** - Specialized patterns per agent

### Core Agent Topology

```
User Query
    ↓
[Orchestrator Agent]
    ├→ [Location Resolver Agent]
    ├→ [Temporal Parser Agent]
    ├→ [Metric Identifier Agent]
    └→ [Intent Classifier Agent]
         ↓
[Query Planner Agent]
    ├→ [Current Data Agent]
    ├→ [Historical Data Agent]
    ├→ [Forecast Data Agent]
    └→ [Comparison Agent]
         ↓
[Result Aggregator Agent]
    ↓
[Response Formatter Agent]
    ↓
Final Answer
```

### Specialized Agent Responsibilities

#### 1. Location Resolver Agent
**Single Job:** Convert any location reference to standardized coordinates/IDs

**Capabilities:**
- City names → District IDs
- Landmarks → Coordinates
- Aliases (NCR → Delhi regions)
- Partial matches
- Nearest sensor mapping
- Spatial hierarchies

**Output Format:**
```json
{
  "resolved_locations": ["sensor_id_1", "district_id_2"],
  "resolution_type": "district",
  "confidence": 0.95,
  "bbox": [lat1, lon1, lat2, lon2]
}
```

#### 2. Temporal Parser Agent
**Single Job:** Convert time references to exact timestamps

**Capabilities:**
- Relative times ("last week")
- Named periods ("monsoon season")
- Ranges ("from Jan to March")
- Ambiguous references ("recently")

**Output Format:**
```json
{
  "start_time": "2024-01-15T00:00:00Z",
  "end_time": "2024-01-22T00:00:00Z",
  "granularity": "day",
  "period_type": "historical"
}
```

#### 3. Data Fetcher Agents (Specialized by Type)

**Current Data Agent:**
- Knows current_readings tables
- Handles sensor status checks
- Implements freshness validation

**Historical Data Agent:**
- Knows materialized views
- Decides aggregation level
- Optimizes for large time ranges

**Forecast Data Agent:**
- Knows model output schemas
- Handles multiple model versions
- Manages confidence intervals

### Query Processing Strategies

#### Temporal Query Strategy

**Three-Layer Temporal Model:**
- **Present Layer:** Current/latest readings (snapshot)
- **Future Layer:** Forecasted/predicted values
- **Past Layer:** Historical data (time-series)

**Query Type Handlers:**

1. **Current Queries (e.g., "What's the PM2.5 now?"):**
   - Primary: `current_readings_*` tables
   - Cache: 5-15 minutes max
   - Freshness check: Data <2 hours old
   - Enrichment: Add trend indicators

2. **Forecast Queries (e.g., "Next 24 hours forecast"):**
   - Primary: Model output tables
   - Validity: Check forecast age
   - Confidence: Include uncertainty bands
   - Multiple models: Ensemble or selection

3. **Historical Queries (e.g., "Last month's average"):**
   - Aggregation levels: Hour, Day, Week, Month
   - Materialized views: For common periods
   - Pre-computation: Nightly/weekly jobs
   - TimescaleDB: Use continuous aggregates

### Agent Communication Patterns

#### Sequential Pattern (Simple Queries)
```
"What's the PM2.5 in Delhi?"
    ↓
Location Agent: Delhi → [district_id: 'delhi_central']
    ↓
Current Data Agent: Fetch from current_readings_aqcn
    ↓
Response: "PM2.5 in Delhi Central is 145 µg/m³"
```

#### Parallel Pattern (Complex Queries)
```
"Compare this week's AQI in Delhi vs Mumbai"
    ↓
    ├→ Location Agent: Resolve both cities
    └→ Temporal Agent: Resolve "this week"
         ↓ (synchronize)
    ├→ Historical Agent (Delhi)
    └→ Historical Agent (Mumbai)
         ↓ (synchronize)
    Comparison Agent: Statistical analysis
         ↓
Response: Formatted comparison
```

### LangGraph Implementation with Multi-Agent

```python
# Multi-agent workflow structure
class MultiAgentQueryGraph:
    def __init__(self):
        self.workflow = StateGraph(QueryState)
        
        # Specialized agents as nodes
        self.workflow.add_node("location_resolver", LocationResolverAgent())
        self.workflow.add_node("temporal_parser", TemporalParserAgent())
        self.workflow.add_node("query_planner", QueryPlannerAgent())
        self.workflow.add_node("current_data", CurrentDataAgent())
        self.workflow.add_node("historical_data", HistoricalDataAgent())
        self.workflow.add_node("forecast_data", ForecastDataAgent())
        self.workflow.add_node("aggregator", ResultAggregatorAgent())
        
        # Define routing
        self.workflow.add_conditional_edges(
            "query_planner",
            self.route_to_data_agents,
            {
                "current": "current_data",
                "historical": "historical_data",
                "forecast": "forecast_data",
                "comparison": ["current_data", "historical_data"]
            }
        )
```

### Progressive Implementation Path

#### Stage 1: Two-Agent System (Week 2-3)
Start simple with basic separation:
```
[Location Agent] → [Data Agent]
```

#### Stage 2: Add Temporal Intelligence (Week 4)
```
[Location Agent] →
                   → [Query Planner] → [Data Agent]
[Temporal Agent] →
```

#### Stage 3: Specialized Data Agents (Week 5-6)
```
[Location Agent] →
                   → [Query Planner] → [Current|Historical|Forecast]
[Temporal Agent] →
```

#### Stage 4: Full Orchestration (Week 7-8)
Add aggregation, comparison, alerting agents as needed

### Design Decisions for Multi-Agent System

#### 1. State Management Strategy
- **Shared State:** All agents read/write common state
- **Message Passing:** Agents pass specific messages
- **Hybrid:** Core state + agent-specific messages

#### 2. Error Handling
- **Fail Fast:** One failure stops entire query
- **Graceful Degradation:** Continue with partial results
- **Retry Logic:** Automatic retry with fallbacks

#### 3. Caching Strategy
- **Per-Agent Caches:** Each agent manages its cache
- **Shared Cache:** Central cache for all
- **Hierarchical:** Agent + shared caches

#### 4. Agent Communication
- **Direct:** Agents call each other
- **Orchestrator:** Central coordinator
- **Event-Driven:** Publish-subscribe pattern

### Performance Optimization with Multi-Agent

**Benefits:**
1. **Parallel Processing:** Multiple agents work simultaneously
2. **Specialized Caching:** Each agent optimizes its domain
3. **Targeted Optimization:** Optimize bottleneck agents
4. **Load Distribution:** Spread work across agents

**Monitoring:**
- Track per-agent metrics (latency, success rate, cache hits)
- Identify bottleneck agents
- Monitor inter-agent communication overhead

### Key Success Factors

1. **Clear Agent Boundaries**
   - Each agent has ONE responsibility
   - No overlapping concerns
   - Well-defined interfaces

2. **Standardized Communication**
   - Common message formats
   - Consistent error handling
   - Shared vocabulary

3. **Progressive Enhancement**
   - Start with 2 agents
   - Add specialization as patterns emerge
   - Refactor when complexity grows

4. **Individual Agent Monitoring**
   - Success rate per agent
   - Latency per agent
   - Error patterns per agent

## Query Resolution Strategies

### Intent Classification Hierarchy

Every query needs to be classified across three dimensions:

```
Query Intent
├── Temporal Classification
│   ├── Current (now, real-time)
│   ├── Future (forecast, prediction, tomorrow)
│   └── Past (historical, was, last)
├── Spatial Classification
│   ├── Point (specific location)
│   ├── Area (district, city)
│   └── Comparative (location A vs B)
└── Metric Classification
    ├── Single (PM2.5 only)
    ├── Multiple (PM2.5 and NO2)
    └── Derived (AQI from multiple pollutants)
```

### Data Source Selection Logic

```
If Query is CURRENT:
  → Check current_readings tables
  → Validate freshness (<2 hours old)
  → Fall back to latest historical if needed

If Query is FUTURE:
  → Check model outputs
  → Validate forecast validity
  → Select appropriate model

If Query is HISTORICAL:
  → Check materialized views first
  → Use pre-aggregated data if available
  → Query raw data only if necessary
```

### Key Design Decisions

#### 1. Location Resolution Strategy
- **Exact Match:** "Delhi" → specific sensor or aggregate?
- **Aggregation Rule:** Multiple sensors → average, max, or weighted?
- **Hierarchy:** City → District → Ward → Sensor

#### 2. Time Window Definitions
- **"Current":** Last 1 hour? 2 hours?
- **"Today":** Midnight to now? Last 24 hours?
- **"Last Month":** Calendar month? Rolling 30 days?

#### 3. Data Freshness Rules
- **Current Data:** Maximum age before considered stale
- **Forecast:** How old before regenerating
- **Historical:** Real-time or allow cached

#### 4. Aggregation Philosophy
- **Default Statistic:** Mean, median, or max?
- **Missing Data:** Interpolate, ignore, or fail?
- **Confidence Thresholds:** When to warn about data quality

#### 5. Model Selection Strategy
- **Multiple Models:** How to choose or combine?
- **Fallback:** What if model fails?
- **Version Management:** Latest vs most accurate?

### Response Enrichment Strategy

**For Current Queries:**
- Comparison to 1 hour ago (trend)
- Alert/threshold status
- Sensor reliability score

**For Forecast Queries:**
- Model confidence score
- Comparison to current values
- Alert if exceeding thresholds

**For Historical Queries:**
- Statistical summary (not just average)
- Anomaly highlights
- Trend analysis

### Critical Success Factor: Time-Location Matrix

Think of every query as requesting cells in a 3D matrix:
- **X-axis:** Location (sensor, district, city)
- **Y-axis:** Time (past, current, future)
- **Z-axis:** Metric (PM2.5, AQI, etc.)

The agent's job:
1. Map natural language to matrix coordinates
2. Determine optimal data source
3. Fetch and aggregate appropriately
4. Enrich with context

---

## Success Metrics

### Phase 1 (Week 2)
- Handle 10 basic query types
- <500ms response time
- 80% success rate on basic queries

### Phase 2 (Week 4)  
- Handle 25+ query types
- LLM fallback for complex queries
- 90% overall success rate

### Phase 3 (Week 6)
- Production API running
- <200ms average response time
- 95% success rate
- 1000+ queries logged

### Phase 4 (Week 8)
- <$100/month operating cost
- 10,000+ queries collected
- Ready for SLM training

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|------------|
| LLM costs too high | Aggressive caching, pattern matching |
| Query patterns too complex | Start simple, add complexity gradually |
| Performance issues | Materialized views, connection pooling |

### Business Risks  
| Risk | Mitigation |
|------|------------|
| User adoption low | Simple UI, clear examples |
| Incorrect SQL generation | Human review queue for low-confidence queries |
| Data security | Query validation, rate limiting |

---

## Future Roadmap (Post Week 8)

### Month 3-4: SLM Training
- Train domain-specific model on collected data
- Target: 500MB model running on CPU
- Expected cost reduction: 90%

### Month 5-6: Advanced Features
- Multi-step reasoning
- Predictive queries
- Alert automation
- Natural language reporting

### Month 7+: Scale & Optimize
- Multi-tenant support
- Real-time streaming queries
- Voice interface
- Mobile app integration

---

## Budget Estimate

### Development Phase (Week 1-8)
- OpenAI API: $100-200
- Infrastructure: $40/month (development server)
- Total: ~$500

### Production Phase (Month 3+)
- API costs: $50-100/month (decreasing with optimization)
- Server: $40/month
- Total: ~$100/month

### Post-SLM Phase (Month 6+)
- Server only: $40/month
- No API costs
- Total: ~$40/month

---

## Getting Started Checklist

### Day 1
- [ ] Set up development environment
- [ ] Install dependencies
- [ ] Connect to database
- [ ] Create project structure

### Week 1
- [ ] Implement basic tools
- [ ] Create pattern matcher
- [ ] Build SQL templates
- [ ] Test with 5 query types

### Week 2  
- [ ] Integrate LangGraph
- [ ] Add LLM fallback
- [ ] Implement caching
- [ ] Deploy to staging

### Month 1
- [ ] Launch production API
- [ ] Monitor performance
- [ ] Collect user feedback
- [ ] Iterate on patterns

---

## Code Repository Structure

```
air-quality-agent/
├── src/
│   ├── agents/          # Query processing agents
│   ├── tools/           # Database tools
│   ├── graphs/          # LangGraph workflows  
│   ├── utils/           # Utilities (cache, db, etc)
│   ├── api/             # FastAPI endpoints
│   └── training/        # SLM data collection
├── config/              # Configuration files
├── tests/               # Test suite
├── docs/                # Documentation
├── scripts/             # Deployment scripts
├── logs/                # Application logs
├── data/                # Training data collection
└── README.md
```

---

## Contact & Support

**Project Lead:** [Your Name]  
**Technical Questions:** [Slack/Email]  
**Repository:** [GitHub/GitLab Link]  
**Documentation:** [Wiki Link]  

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Next Review:** Week 2 Checkpoint
