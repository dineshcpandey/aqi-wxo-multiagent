from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from typing import List, Any, Dict, Optional
import datetime

# Import agents and workflow
from src.utils.database import DatabaseConnection
from src.agents.location_resolver import LocationResolverAgent
from src.agents.pm_data_agent import PMDataAgent
from src.graphs.pm_query_workflow import PMQueryWorkflow

app = FastAPI(title="Air Quality Q&A Agent", version="1.0.0")

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize DB connection and workflow once on app startup."""
    print("[API] Starting up Air Quality Q&A Agent...")
    
    try:
        # Initialize database connection
        db = DatabaseConnection()
        await db.connect()
        print("[API] ✅ Database connected successfully")
        
        # Initialize agents
        location_agent = LocationResolverAgent(db)
        pm_agent = PMDataAgent(db)
        workflow = PMQueryWorkflow(location_agent, pm_agent)
        
        print("[API] ✅ Agents initialized successfully")
        
        # Attach to app state for reuse
        app.state.db = db
        app.state.location_agent = location_agent
        app.state.pm_agent = pm_agent
        app.state.workflow = workflow
        
        # Create helper function for processing
        async def _process_with_agents(query_text: str):
            """Process query through workflow"""
            print(f"\n[API] Processing query: '{query_text}'")
            state = await workflow.process_query(query_text)
            
            # Enhanced debug logging
            print(f"[API] Workflow returned state:")
            print(f"  - waiting_for_user: {state.get('waiting_for_user')}")
            print(f"  - locations count: {len(state.get('locations', []))}")
            print(f"  - has error: {state.get('error') is not None}")
            print(f"  - has response: {bool(state.get('response'))}")
            
            if state.get('locations'):
                print(f"  - First location: {state['locations'][0].get('name')} ({state['locations'][0].get('level')})")
            
            return state
        
        app.state.process_with_agents = _process_with_agents
        
        print("[API] ✅ Startup complete. Ready to process queries.")
        
    except Exception as e:
        print(f"[API] ❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown"""
    print("[API] Shutting down...")
    if hasattr(app.state, 'db') and app.state.db:
        await app.state.db.disconnect()
        print("[API] Database disconnected")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "service": "Air Quality Q&A Agent",
        "status": "running",
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if hasattr(app.state, 'db') else "disconnected"
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.post('/query')
async def post_query(req: Request):
    """Accept a JSON body {"query": "..."} and return the workflow response."""
    try:
        body = await req.json()
        query_text = body.get('query') or body.get('text') or ''
        
        if not query_text:
            print("[API] ❌ Empty query received")
            return {"error": "No query provided"}
        
        print(f"\n{'='*60}")
        print(f"[API] New query received: '{query_text}'")
        print(f"[API] Timestamp: {datetime.datetime.now().isoformat()}")
        
        # Process through workflow
        state = await app.state.process_with_agents(query_text)
        
        # Build response
        resp = {
            "data": {
                "formatted_response": state.get('response'),
                "raw_data": state.get('pm_data')
            },
            "state": state,
            "query_metadata": {
                "confidence": 1.0,
                "source": "db",
                "timestamp": datetime.datetime.now().isoformat(),
                "query": query_text
            }
        }
        
        print(f"[API] Response prepared:")
        print(f"  - Has formatted response: {bool(state.get('response'))}")
        print(f"  - State includes disambiguation: {state.get('waiting_for_user', False)}")
        print(f"{'='*60}\n")
        
        return resp
        
    except Exception as e:
        print(f"[API] ❌ Error processing query: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/query/select')
async def post_query_selection(req: Request):
    """Accept a JSON body {"state": {...}, "selected_index": 0} and continue the workflow."""
    try:
        print(f"\n[API] /query/select endpoint called")
        body = await req.json()
        state = body.get('state')
        selected_index = body.get('selected_index')
        
        if selected_index is None and 'selectedIndex' in body:
            selected_index = body['selectedIndex']
        
        print(f"\n{'='*60}")
        print(f"[API] Selection received: index={selected_index}")
        
        # Validate inputs
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="'state' is required and must be a dict"
            )
        
        if selected_index is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="'selected_index' is required"
            )
        
        if not isinstance(state, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="'state' must be a JSON object"
            )
        
        locations = state.get('locations')
        if not isinstance(locations, list) or len(locations) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No selectable locations found in state"
            )
        
        # Validate index
        try:
            idx = int(selected_index)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="'selected_index' must be an integer"
            )
        
        if idx < 0 or idx >= len(locations):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"'selected_index' out of range [0, {len(locations)-1}]"
            )
        
        print(f"[API] Selected location: {locations[idx].get('name')} ({locations[idx].get('level')})")
        
        # Continue workflow with selection
        new_state = await app.state.workflow.continue_with_selection(state, idx)
        
        print(f"[API] Selection processed:")
        print(f"  - Has response: {bool(new_state.get('response'))}")
        print(f"  - Has PM data: {bool(new_state.get('pm_data'))}")
        print(f"  - Has error: {new_state.get('error')}")
        print(f"{'='*60}\n")
        
        # Build response
        resp = {
            "data": {
                "formatted_response": new_state.get('response'),
                "raw_data": new_state.get('pm_data')
            },
            "query_metadata": {
                "confidence": 1.0,
                "source": "db",
                "timestamp": datetime.datetime.now().isoformat(),
                "selected_index": idx,
                "selected_location": locations[idx].get('name')
            }
        }
        
        return resp
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ❌ Error processing selection: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to continue workflow: {e}"
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket)
    print(f"[API] WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            query = json.loads(data)
            query_text = query.get('text', '')
            
            print(f"[API] WebSocket query: '{query_text}'")
            
            if not query_text:
                await manager.send_personal_message(
                    json.dumps({"error": "no text provided"}), 
                    websocket
                )
                continue
            
            # Process query
            state = await app.state.process_with_agents(query_text)
            
            response = {
                "response": state.get('response'),
                "state": state,
                "metadata": {
                    "confidence": 1.0,
                    "data_source": "db",
                    "execution_time": None,
                    "agent_path": ["location_resolver", "pm_data_agent"]
                }
            }
            
            await manager.send_personal_message(json.dumps(response), websocket)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        print(f"[API] WebSocket client disconnected")
    except Exception as e:
        print(f"[API] WebSocket error: {e}")
        await manager.disconnect(websocket)


# Additional debug endpoints for development
@app.get("/debug/agents")
async def debug_agents():
    """Debug endpoint to check agent status"""
    return {
        "agents": {
            "location_resolver": hasattr(app.state, 'location_agent'),
            "pm_data_agent": hasattr(app.state, 'pm_agent'),
            "workflow": hasattr(app.state, 'workflow')
        },
        "database": hasattr(app.state, 'db')
    }


@app.post("/debug/test_location")
async def debug_test_location(req: Request):
    """Debug endpoint to test location resolution"""
    body = await req.json()
    location = body.get('location', '')
    
    if not hasattr(app.state, 'location_agent'):
        return {"error": "Location agent not initialized"}
    
    result = await app.state.location_agent.run({"location_query": location})
    return result
