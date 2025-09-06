#!/usr/bin/env python3
"""
Sample Python code for testing JerryRig migration.
"""

import json
import os
from typing import List, Dict, Optional

class DataProcessor:
    """A simple data processor class."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.data = []
        
    def load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def process_data(self, input_data: List[Dict]) -> List[Dict]:
        """Process the input data."""
        processed = []
        config = self.load_config()
        
        for item in input_data:
            if self.validate_item(item):
                processed_item = {
                    "id": item.get("id"),
                    "value": item.get("value", 0) * config.get("multiplier", 1),
                    "processed": True
                }
                processed.append(processed_item)
        
        return processed
    
    def validate_item(self, item: Dict) -> bool:
        """Validate a data item."""
        return "id" in item and "value" in item
    
    def save_results(self, data: List[Dict], filename: str = "results.json") -> None:
        """Save processed results to file."""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results saved to {filename}")

def main():
    """Main function to demonstrate the processor."""
    processor = DataProcessor()
    
    sample_data = [
        {"id": 1, "value": 10},
        {"id": 2, "value": 20},
        {"id": 3, "value": 15},
        {"id": 4}  # Missing value - should be filtered
    ]
    
    results = processor.process_data(sample_data)
    processor.save_results(results)
    
    print(f"Processed {len(results)} items successfully!")

if __name__ == "__main__":
    main()