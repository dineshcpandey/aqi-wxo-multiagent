# Air Quality Q&A Agent - Complete Setup Guide

## 🎯 Project Overview

A production-ready multi-agent Q&A system for air quality monitoring that processes natural language queries about pollution levels, trends, and health advisories across Indian cities. The system uses LangGraph orchestration, PostgreSQL/PostGIS for spatial data, and InstructLab for enhanced NLP capabilities.

**Core Capabilities:**
- Real-time air quality information (PM2.5, AQI, NO2, SO2, etc.)
- Historical trend analysis
- Multi-location comparisons
- Pollution hotspot detection
- Health advisories and recommendations
- Predictive forecasting

## 🏗️ System Architecture

### High-Level Architecture
```
User Query → Query Parser → Agent Router → Specialized Agents → PostgreSQL → Response Formatter → User
                  ↓                              ↓
           InstructLab (NLP)              Location Resolver
                                                 ↓
                                          Disambiguation
```

### Technology Stack
- **Language:** Python 3.9+
- **Orchestration:** LangGraph
- **Database:** PostgreSQL 14+ with PostGIS and TimescaleDB
- **NLP:** InstructLab with Mistral-7B
- **Cache:** Redis (optional)
- **API:** FastAPI
- **UI:** Streamlit
- **Async:** asyncpg, asyncio

## 📁 Project Structure

```
air-quality-agent/
├── src/
│   ├── agents/                 # Agent implementations
│   │   ├── agent_base.py      # Base agent class
│   │   ├── agent_registry.py  # Agent capability registry
│   │   ├── location_resolver.py
│   │   ├── pm_data_agent.py
│   │   ├── trend_agent.py
│   │   ├── comparison_agent.py
│   │   ├── hotspot_agent.py
│   │   ├── forecast_agent.py
│   │   ├── health_advisory_agent.py
│   │   ├── query_parser.py    # Regex-based parser
│   │   └── instructlab_parser.py # LLM-based parser
│   │
│   ├── graphs/                 # LangGraph workflows
│   │   ├── pm_query_workflow.py
│   │   ├── multi_agent_router.py
│   │   └── query_state.py
│   │
│   ├── utils/
│   │   ├── database.py        # DB connection
│   │   ├── cache.py           # Caching layer
│   │   └── monitoring.py      # Logging/metrics
│   │
│   ├── api/
│   │   └── main.py           # FastAPI application
│   │
│   └── ui/
│       └── streamlit_app.py  # Streamlit interface
│
├── db/
│   ├── schemas/              # Database schemas
│   ├── functions/            # PostgreSQL functions
│   └── migrations/           # DB migrations
│
├── instructlab/
│   ├── config.yaml          # InstructLab configuration
│   └── training_data/       # Training examples
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── config/
│   └── queries.yaml         # Query templates
│
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🤖 Agent Architecture

### Agent Registry

| Agent Name | Purpose | Primary Intents | DB Functions |
|------------|---------|-----------------|--------------|
| **LocationResolverAgent** | Resolves location names to codes, handles disambiguation | `location_search` | `gis.search_location_json` |
| **PMDataAgent** | Fetches current air quality readings | `current_reading` | `gis.get_current_pm25`, `gis.get_current_readings` |
| **TrendAgent** | Analyzes historical trends | `trend`, `historical` | `gis.get_time_series` |
| **ComparisonAgent** | Compares multiple locations | `comparison`, `versus` | `gis.compare_locations` |
| **HotspotAgent** | Identifies pollution hotspots | `hotspot`, `worst_areas` | `gis.find_hotspots` |
| **ForecastAgent** | Provides predictions | `forecast`, `prediction` | `gis.get_forecast` |
| **HealthAdvisoryAgent** | Health recommendations | `health`, `safety` | `gis.get_health_advisory` |

### Intent Classification

| Intent | Description | Example Queries |
|--------|-------------|-----------------|
| `current_reading` | Get current pollution levels | "What's the PM2.5 in Delhi?", "Current AQI in Mumbai" |
| `trend` | Historical data analysis | "Show PM2.5 trend for last 24 hours", "Weekly pattern" |
| `comparison` | Compare locations | "Compare Delhi vs Mumbai", "Which city is cleaner?" |
| `hotspot` | Find problem areas | "Pollution hotspots in NCR", "Worst areas today" |
| `forecast` | Future predictions | "Tomorrow's AQI", "Will it improve today?" |
| `health` | Health advice | "Is it safe to jog?", "Should I wear a mask?" |
| `alert` | Check alerts | "Any warnings for my area?", "Critical zones" |

## 🗣️ Query Patterns

### Basic Query Patterns

```yaml
current_reading:
  patterns:
    - "What is {metric} in {location}?"
    - "Current {metric} at {location}"
    - "{location} {metric} level"
    - "Show me air quality in {location}"
  
  examples:
    - "What is PM2.5 in Hazratganj?"
    - "Current AQI at India Gate"
    - "Delhi pollution level"
    - "Show me air quality in Araria"

trend:
  patterns:
    - "{metric} trend for last {duration} {unit}"
    - "Show {location} {metric} history"
    - "How has {metric} changed in {location}"
  
  examples:
    - "PM2.5 trend for last 24 hours"
    - "Show Delhi AQI history"
    - "How has pollution changed in Mumbai this week"

comparison:
  patterns:
    - "Compare {location1} and {location2}"
    - "Which is better: {location1} or {location2}"
    - "{location1} vs {location2} {metric}"
  
  examples:
    - "Compare Delhi and Mumbai air quality"
    - "Which is cleaner: Bangalore or Chennai?"
    - "Delhi vs Gurgaon PM2.5"
```

### Complex Query Patterns

```yaml
multi_intent:
  examples:
    - "Compare today's PM2.5 in Delhi with last week's average"
      intents: [current_reading, trend, comparison]
    
    - "Show pollution hotspots and forecast for tomorrow"
      intents: [hotspot, forecast]
    
    - "Is it safe to exercise in Delhi given current trends?"
      intents: [current_reading, trend, health]
```

## 💾 Database Architecture

### Core Tables Structure

```yaml
schemas:
  master:
    - data_sources       # Registry of all data sources
    - data_source_attributes  # Expected metrics per source
  
  aq:
    - sensors_*         # Dynamic per data source
    - current_readings_* # Latest readings
    - readings_*        # Historical (partitioned)
  
  sop:
    - triggers          # Threshold triggers
    - sop_instances     # Alert tracking
  
  gis:
    - locations         # Spatial location data
    - boundaries        # Administrative boundaries
```

### Key Database Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `gis.search_location_json` | Find locations by name | location_text | JSON array of matches |
| `gis.get_current_pm25` | Current PM2.5 value | code, level | pm25_value, timestamp |
| `gis.get_current_readings` | Multiple metrics | code, level, metrics[] | Table of values |
| `gis.get_time_series` | Historical data | code, level, duration, unit | Time series data |
| `gis.compare_locations` | Multi-location comparison | locations[], metric | Ranked results |
| `gis.find_hotspots` | Pollution clusters | region, threshold | Hotspot locations |
| `gis.get_forecast` | Predictions | code, level, hours | Forecast data |
| `gis.get_health_advisory` | Health advice | code, level | Advisory JSON |

## 🚀 Setup Instructions

### 1. Environment Setup

```bash
# Clone repository
git clone <repository>
cd air-quality-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your configurations
```

### 2. Database Setup

```bash
# Using Docker
docker-compose up -d postgres

# Or manual PostgreSQL setup
psql -U postgres -c "CREATE DATABASE airquality;"
psql -U postgres -d airquality -c "CREATE EXTENSION postgis;"
psql -U postgres -d airquality -c "CREATE EXTENSION timescaledb;"

# Run migrations
psql -U postgres -d airquality -f db/schemas/01_schemas.sql
psql -U postgres -d airquality -f db/functions/02_functions.sql
```

### 3. InstructLab Setup

```bash
# Install InstructLab
pip install instructlab

# Download model
ilab model download mistralai/Mistral-7B-Instruct-v0.2

# Configure
cp instructlab/config.yaml.example instructlab/config.yaml

# Start server
ilab model serve --config instructlab/config.yaml
```

### 4. Application Startup

```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Start Streamlit UI (separate terminal)
streamlit run src/ui/streamlit_app.py

# Or use Docker Compose for all services
docker-compose up
```

## 📊 Use Cases

### 1. Real-time Monitoring
**User:** "What's the current PM2.5 in Connaught Place?"
```
Flow: Query → LocationResolver → PMDataAgent → Response
DB Functions: gis.search_location_json → gis.get_current_pm25
Response: "PM2.5 in Connaught Place: 156 µg/m³ (Unhealthy)"
```

### 2. Trend Analysis
**User:** "Show me Delhi's air quality trend for the last week"
```
Flow: Query → LocationResolver → TrendAgent → Response with Chart
DB Functions: gis.search_location_json → gis.get_time_series
Response: Chart + "Air quality deteriorated by 35% over the week"
```

### 3. Location Comparison
**User:** "Which city has better air - Delhi or Mumbai?"
```
Flow: Query → LocationResolver (2x) → ComparisonAgent → Response
DB Functions: gis.compare_locations
Response: "Mumbai (AQI: 95) has better air quality than Delhi (AQI: 245)"
```

### 4. Health Advisory
**User:** "Is it safe to go jogging in Lodhi Garden?"
```
Flow: Query → LocationResolver → HealthAdvisoryAgent → Response
DB Functions: gis.get_health_advisory
Response: "Not recommended. AQI is 185. Limit outdoor activities."
```

### 5. Hotspot Detection
**User:** "Find pollution hotspots in NCR"
```
Flow: Query → HotspotAgent → Response with Map
DB Functions: gis.find_hotspots
Response: Map + "Found 12 hotspots. Worst: Anand Vihar (PM2.5: 385)"
```

## 🔄 Workflow Examples

### Simple Query Workflow
```python
# "What is PM2.5 in Hazratganj?"

1. QueryParser.parse()
   → intent: "current_reading"
   → entities: {location: "Hazratganj", metric: "pm25"}

2. LocationResolver.run()
   → search_location_json("Hazratganj")
   → returns: [{code: "HAZ01", level: "locality"}]

3. PMDataAgent.run()
   → get_current_pm25("HAZ01", "locality")
   → returns: {pm25_value: 87.5, timestamp: "..."}

4. ResponseFormatter.format()
   → "🟠 PM2.5 in Hazratganj: 87.5 µg/m³ (Moderate)"
```

### Disambiguation Workflow
```python
# "What is air quality in Araria?"

1. QueryParser.parse()
   → intent: "current_reading"
   → entities: {location: "Araria"}

2. LocationResolver.run()
   → search_location_json("Araria")
   → returns: [
       {code: "AR01", level: "district", name: "Araria District"},
       {code: "AR02", level: "city", name: "Araria City"}
     ]

3. DisambiguationAgent.show_options()
   → User selects: "Araria City"

4. PMDataAgent.run()
   → get_current_readings("AR02", "city", ["aqi", "pm25"])

5. ResponseFormatter.format()
   → "Air quality in Araria City: AQI 125 (Moderate)"
```

## 🧪 Testing Strategy

### Test Coverage Areas

1. **Unit Tests**
   - Individual agent functionality
   - Query parser patterns
   - Database function calls
   - Cache operations

2. **Integration Tests**
   - Complete workflow execution
   - Multi-agent coordination
   - Disambiguation flows
   - API endpoints

3. **Performance Tests**
   - Query response time (<200ms target)
   - Concurrent user handling (100+ users)
   - Cache hit rates (>60% target)

## 📈 Performance Metrics

### Target Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Simple Query Response | <200ms | p95 latency |
| Complex Query Response | <1s | p95 latency |
| Cache Hit Rate | >60% | Daily average |
| Success Rate | >95% | Weekly average |
| Concurrent Users | 100+ | Load test |

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=airquality
DB_USER=postgres
DB_PASSWORD=password

# InstructLab
USE_INSTRUCTLAB=false  # Start with false, enable after testing
INSTRUCTLAB_ENDPOINT=http://localhost:8000
SHADOW_MODE=true  # Run LLM in parallel for comparison

# Cache
CACHE_TTL_SECONDS=3600
REDIS_HOST=localhost
REDIS_PORT=6379

# API
API_PORT=8000
STREAMLIT_PORT=8501
```

## 🚦 Deployment Phases

### Phase 1: Foundation (Week 1-2)
- Basic agent structure
- Database setup with functions
- Simple query handling
- Streamlit interface

### Phase 2: Intelligence (Week 3-4)
- InstructLab integration (shadow mode)
- Enhanced query parsing
- Multi-agent coordination
- Caching layer

### Phase 3: Production (Week 5-6)
- Performance optimization
- Load testing
- Monitoring setup
- Documentation

### Phase 4: Enhancement (Week 7-8)
- Fine-tuning with collected data
- Advanced visualizations
- Mobile interface
- API marketplace

## 📝 Development Guidelines

### Adding a New Agent
1. Create agent class extending `AgentBase`
2. Register in `AgentRegistry` with capabilities
3. Define required DB functions
4. Add query patterns for the intent
5. Create unit tests
6. Update training data for InstructLab

### Adding a New Intent
1. Add intent to query parser patterns
2. Map intent to appropriate agent
3. Define required entities
4. Create example queries
5. Add to InstructLab training data

### Database Function Guidelines
- Use consistent parameter naming (p_code, p_level)
- Return JSON for complex results
- Include metadata (timestamp, source)
- Handle NULL cases gracefully
- Add appropriate indexes

## 🎓 InstructLab Training Data Format

```json
{
  "examples": [
    {
      "input": "What's the PM2.5 in Delhi?",
      "output": {
        "intent": "current_reading",
        "entities": {
          "location": "Delhi",
          "metric": "pm25"
        },
        "agent": "pm_data",
        "db_function": "gis.get_current_pm25"
      }
    }
  ]
}
```

## 📚 Resources

### Documentation
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [InstructLab Guide](https://instructlab.ai/docs)
- [PostGIS Reference](https://postgis.net/documentation/)
- [TimescaleDB Docs](https://docs.timescale.com/)

### Models
- Primary: mistralai/Mistral-7B-Instruct-v0.2
- Alternative: meta-llama/Llama-2-7b-chat-hf
- Small: microsoft/phi-2

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Slow location search | Add GiST index on location columns |
| High memory usage | Reduce connection pool size |
| InstructLab timeout | Increase timeout, use smaller model |
| Cache misses | Increase TTL, add query normalization |

## 📞 Support & Contribution

- **Issues:** GitHub Issues for bug reports
- **Discussions:** GitHub Discussions for features
- **Contributing:** Follow PR template, add tests

---

**Version:** 1.0.0  
**Last Updated:** January 2025  
**Status:** Production Ready  
**License:** MIT
