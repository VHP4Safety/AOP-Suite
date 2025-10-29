import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import os

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Represents a single logged operation"""
    timestamp: datetime
    operation_type: str
    description: str
    python_code: str
    comment: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_summary: Optional[str] = None

class AOPSuiteLogger:
    """Logs all AOP operations and generates downloadable Python scripts"""
    
    def __init__(self):
        self.entries: List[LogEntry] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_operation(self, operation_type: str, description: str, 
                     python_code: str, comment: str, 
                     parameters: Dict[str, Any] = None,
                     result_summary: str = None) -> None:
        """Log a single operation with its Python equivalent"""
        entry = LogEntry(
            timestamp=datetime.now(),
            operation_type=operation_type,
            description=description,
            python_code=python_code,
            comment=comment,
            parameters=parameters or {},
            result_summary=result_summary
        )
        self.entries.append(entry)
        logger.info(f"Logged operation: {operation_type} - {description}")
    
    def generate_python_script(self, include_comments: bool = True, 
                              include_imports: bool = True) -> str:
        """Generate a complete Python script from logged operations"""
        script_lines = []
        
        # Add header
        script_lines.extend([
            f"# AOP-Suite Generated Script",
            f"# Session: {self.session_id}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Total operations: {len(self.entries)}",
            ""
        ])
        
        # Add imports if requested
        if include_imports:
            imports = self._generate_imports()
            script_lines.extend(imports)
            script_lines.append("")
        
        # Add main function
        script_lines.extend([
            "def main():",
            "    \"\"\"Recreate AOP network operations from AOP-Suite session\"\"\"",
            ""
        ])
        
        # Add initialization
        script_lines.extend([
            "    # Initialize AOP network builder",
            "    builder = AOPNetworkBuilder()",
            "    network = builder.network",
            ""
        ])
        
        # Add each logged operation
        for i, entry in enumerate(self.entries, 1):
            if include_comments:
                script_lines.append(f"    # Operation {i}: {entry.description}")
                script_lines.append(f"    # {entry.comment}")
                if entry.result_summary:
                    script_lines.append(f"    # Result: {entry.result_summary}")
            
            # Add the actual Python code, indented for the function
            code_lines = entry.python_code.strip().split('\n')
            for code_line in code_lines:
                if code_line.strip():  # Skip empty lines
                    script_lines.append(f"    {code_line}")
            
            script_lines.append("")  # Add spacing between operations
        
        # Add footer
        script_lines.extend([
            "    # Get final network summary",
            "    summary = network.get_summary()",
            "    print(f'Final network contains: {summary}')",
            "",
            "    # Export network (optional)",
            "    # elements = network.to_cytoscape_elements()",
            "    # with open('aop_network.json', 'w') as f:",
            "    #     json.dump(elements, f, indent=2)",
            "",
            "    return network",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ])
        
        return '\n'.join(script_lines)
    
    def _generate_imports(self) -> List[str]:
        """Generate necessary imports based on logged operations"""
        imports = [
            "import json",
            "import logging",
            "from datetime import datetime",
            "from pyaop.aop.builder import AOPNetworkBuilder",
            ""
        ]

        return imports
    
    def get_operation_summary(self) -> Dict[str, Any]:
        """Get summary of all logged operations"""
        operation_counts = {}
        for entry in self.entries:
            operation_counts[entry.operation_type] = operation_counts.get(entry.operation_type, 0) + 1
        
        return {
            "session_id": self.session_id,
            "total_operations": len(self.entries),
            "operation_types": operation_counts,
            "start_time": self.entries[0].timestamp.isoformat() if self.entries else None,
            "end_time": self.entries[-1].timestamp.isoformat() if self.entries else None
        }
    
    def clear_log(self) -> None:
        """Clear all logged operations"""
        self.entries.clear()
        logger.info("Cleared operation log")
    
    def export_log_json(self) -> str:
        """Export log entries as JSON"""
        entries_data = []
        for entry in self.entries:
            entries_data.append({
                "timestamp": entry.timestamp.isoformat(),
                "operation_type": entry.operation_type,
                "description": entry.description,
                "python_code": entry.python_code,
                "comment": entry.comment,
                "parameters": entry.parameters,
                "result_summary": entry.result_summary
            })
        
        return json.dumps({
            "session_id": self.session_id,
            "entries": entries_data
        }, indent=2)
