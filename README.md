# Air Quality Q&A Agent - Multi-Agent System

A production-ready multi-agent Q&A system for air quality monitoring that processes natural language queries about pollution levels, trends, and health advisories across Indian cities.

## Quick Start

1. **Setup Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configurations
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Access Application**
   - API: http://localhost:8000
   - UI: http://localhost:8501

## Project Structure

```
air-quality-agent/
├── src/                    # Source code
│   ├── agents/            # Agent implementations
│   ├── graphs/            # LangGraph workflows
│   ├── utils/             # Utilities
│   ├── api/               # FastAPI application
│   └── ui/                # Streamlit interface
├── db/                    # Database schemas and functions
├── instructlab/           # InstructLab configuration
├── tests/                 # Test suites
└── config/                # Configuration files
```

## Key Features

- **Real-time Air Quality Data**: Current PM2.5, AQI, NO2, SO2 readings
- **Trend Analysis**: Historical patterns and forecasting
- **Location Comparison**: Multi-city air quality comparison
- **Health Advisories**: Personalized health recommendations
- **Hotspot Detection**: Pollution concentration areas
- **Natural Language Processing**: Query understanding with InstructLab

## Documentation

See `docs/` folder for detailed setup and implementation guides.

## License

MIT License