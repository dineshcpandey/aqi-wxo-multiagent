import asyncpg
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConnection:
    def __init__(self, connection_string: Optional[str] = None):
        if connection_string:
            self.connection_string = connection_string
        else:
            # Build connection string from environment variables
            self.connection_string = self._build_connection_string()
        self.pool = None
    
    def _build_connection_string(self) -> str:
        """Build connection string from environment variables"""
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'airquality')
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def connect(self):
        """Establish connection pool to the database"""
        try:
            self.pool = await asyncpg.create_pool(self.connection_string, min_size=2, max_size=10)
            print(f"✅ Successfully connected to database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            print("🔐 Database connection closed")
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            if not self.pool:
                await self.connect()
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                print(f"✅ Database connection test successful: {result}")
                return True
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    async def execute_query(self, sql: str, params: List = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        try:
            if not self.pool:
                await self.connect()
                
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, *(params or []))
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            print(f"SQL: {sql}")
            raise
    
    async def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get all active data sources from the database"""
        sql = """
        SELECT code, name, source_type, readings_table_name 
        FROM master.data_sources 
        WHERE is_active = true
        """
        return await self.execute_query(sql)

 