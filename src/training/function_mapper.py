# src/training/function_mapper.py
class FunctionMappingGenerator:
    """Generate training data from DB function calls"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.functions = self._load_function_specs()
    
    def _load_function_specs(self):
        """Define your DB functions and their parameters"""
        return {
            'gis.search_location_json': {
                'params': ['location_text'],
                'examples': [
                    ("What's the PM2.5 in Hazratganj?", {"location_text": "Hazratganj"}),
                    ("Air quality in Araria", {"location_text": "Araria"}),
                    ("Show Delhi pollution", {"location_text": "Delhi"})
                ]
            },
            'gis.get_current_pm25': {
                'params': ['code', 'level'],
                'chain_after': 'gis.search_location_json',  # Indicates this needs location resolution first
            }
        }
    
    async def generate_training_data(self):
        """Generate training examples from actual queries"""
        training_data = []
        
        # Get successful queries from your logs
        queries = await self.db.execute_query("""
            SELECT DISTINCT user_query, intent, entities, response
            FROM query_logs 
            WHERE success = true 
            AND confidence > 0.9
            LIMIT 1000
        """)
        
        for query_record in queries:
            example = self._create_training_example(query_record)
            training_data.append(example)
        
        return training_data
    
    def _create_training_example(self, query_record):
        """Format for InstructLab training"""
        return {
            "instruction": "Parse the air quality query and identify the database function to call.",
            "input": query_record['user_query'],
            "output": json.dumps({
                "intent": query_record['intent'],
                "function": self._map_intent_to_function(query_record['intent']),
                "parameters": query_record['entities']
            })
        }