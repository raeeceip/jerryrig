"""Solace AI agent integration for code migration."""

import os
import json
from typing import Dict, List, Optional, Any
import httpx
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResponse:
    """Response from the Solace agent."""
    success: bool
    content: str
    confidence: float
    metadata: Dict[str, Any]


class SolaceAgent:
    """Interface for AI agents to perform code migration."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, provider: str = "auto"):
        self.api_key = api_key or os.getenv("SOLACE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.provider = provider
        self.base_url = base_url or self._get_default_base_url()
        self.client = httpx.Client(timeout=30.0)
        
        # Detect if this is a Solace JWT token
        if self.api_key and self.api_key.startswith("eyJ"):
            self.provider = "solace_sam"
            self.base_url = "https://api.solace.cloud"
            logger.info("Using Solace Agent Mesh (SAM) for AI operations")
        
        if not self.api_key:
            logger.warning("No API key provided. Using mock responses.")
        else:
            logger.info(f"Using AI provider: {self._detect_provider()}")
            
    def _get_default_base_url(self) -> str:
        """Get default base URL based on available API keys."""
        solace_key = os.getenv("SOLACE_API_KEY")
        if solace_key and solace_key.startswith("eyJ"):
            return "https://api.solace.cloud"
        elif os.getenv("OPENAI_API_KEY"):
            return "https://api.openai.com/v1"
        elif os.getenv("ANTHROPIC_API_KEY"):
            return "https://api.anthropic.com/v1"
        return "https://api.openai.com/v1"
        
    def _detect_provider(self) -> str:
        """Detect which AI provider to use based on API key format."""
        if not self.api_key:
            return "mock"
        elif self.api_key.startswith("eyJ"):
            return "solace_sam"
        elif self.api_key.startswith("sk-"):
            return "openai"
        elif self.api_key.startswith("sk-ant-"):
            return "anthropic"
        else:
            return "unknown"
            
    def migrate_code(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Migrate source code from one language to another.
        
        Args:
            source_code: The source code to migrate
            source_language: Source programming language
            target_language: Target programming language
            
        Returns:
            Dictionary containing migration results
        """
        logger.info(f"Requesting code migration: {source_language} -> {target_language}")
        
        if not self.api_key:
            return self._mock_migration_response(source_code, source_language, target_language)
            
        try:
            provider = self._detect_provider()
            
            if provider == "solace_sam":
                return self._solace_sam_migration(source_code, source_language, target_language)
            elif provider == "openai":
                return self._openai_migration(source_code, source_language, target_language)
            elif provider == "anthropic":
                return self._anthropic_migration(source_code, source_language, target_language)
            else:
                # Try the original Solace-style API first
                response = self._call_solace_api(
                    endpoint="/v1/migrate",
                    payload={
                        "source_code": source_code,
                        "source_language": source_language,
                        "target_language": target_language,
                        "options": {
                            "preserve_comments": True,
                            "optimize_for_readability": True,
                            "include_type_hints": True
                        }
                    }
                )
                
                return {
                    "success": response.success,
                    "migrated_code": response.content,
                    "confidence": response.confidence,
                    "warnings": response.metadata.get("warnings", []),
                    "errors": response.metadata.get("errors", []),
                    "suggestions": response.metadata.get("suggestions", [])
                }
            
        except Exception as e:
            logger.error(f"Error calling AI API: {e}")
            return self._mock_migration_response(source_code, source_language, target_language)
            
    def analyze_code_structure(self, source_code: str, language: str) -> Dict[str, Any]:
        """Analyze code structure for migration planning.
        
        Args:
            source_code: The source code to analyze
            language: Programming language
            
        Returns:
            Dictionary containing structural analysis
        """
        logger.info(f"Requesting code structure analysis for {language}")
        
        if not self.api_key:
            return self._mock_analysis_response(source_code, language)
            
        try:
            response = self._call_solace_api(
                endpoint="/v1/analyze",
                payload={
                    "source_code": source_code,
                    "language": language,
                    "analysis_type": "structure"
                }
            )
            
            return {
                "success": response.success,
                "analysis": json.loads(response.content),
                "confidence": response.confidence
            }
            
        except Exception as e:
            logger.error(f"Error analyzing code structure: {e}")
            return self._mock_analysis_response(source_code, language)
            
    def suggest_improvements(self, source_code: str, target_language: str) -> List[str]:
        """Suggest improvements for migrated code.
        
        Args:
            source_code: The migrated code
            target_language: Target programming language
            
        Returns:
            List of improvement suggestions
        """
        logger.info(f"Requesting improvement suggestions for {target_language}")
        
        if not self.api_key:
            return self._mock_improvement_suggestions(target_language)
            
        try:
            response = self._call_solace_api(
                endpoint="/v1/suggest",
                payload={
                    "source_code": source_code,
                    "language": target_language,
                    "suggestion_types": ["performance", "idioms", "best_practices"]
                }
            )
            
            if response.success:
                suggestions_data = json.loads(response.content)
                return suggestions_data.get("suggestions", [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting improvement suggestions: {e}")
            return self._mock_improvement_suggestions(target_language)
            
    def _call_solace_api(self, endpoint: str, payload: Dict[str, Any]) -> AgentResponse:
        """Make a call to the Solace API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return AgentResponse(
            success=data.get("success", False),
            content=data.get("content", ""),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {})
        )
        
    def _openai_migration(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Use OpenAI API for code migration."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Convert this {source_language} code to {target_language}. 
        Preserve functionality and add appropriate comments. Make the code idiomatic for {target_language}.

        Source code:
        ```{source_language}
        {source_code}
        ```

        Please respond with only the converted {target_language} code, no explanations."""
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert programmer who converts code between programming languages."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        response = self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        migrated_code = data["choices"][0]["message"]["content"]
        
        # Clean up code blocks if present
        if "```" in migrated_code:
            lines = migrated_code.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.startswith('```'):
                    if start_idx == 0:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            
            migrated_code = '\n'.join(lines[start_idx:end_idx])
        
        return {
            "success": True,
            "migrated_code": migrated_code.strip(),
            "confidence": 0.85,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
    def _anthropic_migration(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Use Anthropic Claude API for code migration."""
        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        prompt = f"""Convert this {source_language} code to {target_language}. 
        Preserve functionality and add appropriate comments. Make the code idiomatic for {target_language}.

        Source code:
        ```{source_language}
        {source_code}
        ```

        Please respond with only the converted {target_language} code, no explanations."""
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        migrated_code = data["content"][0]["text"]
        
        # Clean up code blocks if present
        if "```" in migrated_code:
            lines = migrated_code.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.startswith('```'):
                    if start_idx == 0:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            
            migrated_code = '\n'.join(lines[start_idx:end_idx])
        
        return {
            "success": True,
            "migrated_code": migrated_code.strip(),
            "confidence": 0.90,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
    def _solace_sam_migration(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Use Solace Agent Mesh for code migration."""
        # For now, we'll use the Solace API directly to interact with agents
        # In a full implementation, this would use the SAM CLI or SAM agent endpoints
        
        # Try using Solace's agent endpoints
        url = f"{self.base_url}/v1/agents/code-migration"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "source_code": source_code,
            "source_language": source_language,
            "target_language": target_language,
            "migration_type": "code_translation",
            "preserve_structure": True,
            "include_comments": True,
            "optimize_for_target": True
        }
        
        try:
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "migrated_code": data.get("migrated_code", ""),
                "confidence": data.get("confidence", 0.85),
                "warnings": data.get("warnings", []),
                "errors": data.get("errors", []),
                "suggestions": data.get("suggestions", [])
            }
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"Solace SAM API returned {e.response.status_code}. Falling back to enhanced mock.")
            return self._enhanced_solace_mock(source_code, source_language, target_language)
        except Exception as e:
            logger.error(f"Error calling Solace SAM API: {e}")
            return self._enhanced_solace_mock(source_code, source_language, target_language)
            
    def _enhanced_solace_mock(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Enhanced mock response that simulates Solace SAM capabilities."""
        logger.info("Using enhanced Solace SAM mock migration")
        
        # More sophisticated mock translation
        if source_language == 'python' and target_language == 'javascript':
            migrated_code = self._python_to_js_enhanced(source_code)
        elif source_language == 'javascript' and target_language == 'python':
            migrated_code = self._js_to_python_enhanced(source_code)
        else:
            migrated_code = f"// Enhanced migration from {source_language} to {target_language}\n{source_code}"
            
        return {
            "success": True,
            "migrated_code": migrated_code,
            "confidence": 0.82,
            "warnings": ["Using enhanced mock migration - connect to Solace SAM for full capabilities"],
            "errors": [],
            "suggestions": [
                f"Consider using {target_language}-specific patterns and idioms",
                "Review the migrated code for optimization opportunities",
                "Test thoroughly in your target environment"
            ]
        }
        
    def _python_to_js_enhanced(self, python_code: str) -> str:
        """Enhanced Python to JavaScript conversion."""
        js_code = python_code
        
        # Function definitions
        js_code = js_code.replace("def ", "function ")
        js_code = js_code.replace(":", " {")
        
        # Boolean values
        js_code = js_code.replace("True", "true")
        js_code = js_code.replace("False", "false")
        js_code = js_code.replace("None", "null")
        
        # Print statements
        js_code = js_code.replace("print(", "console.log(")
        
        # String formatting (basic)
        import re
        js_code = re.sub(r'f"([^"]*)"', r'`\1`', js_code)
        js_code = js_code.replace("{", "${")
        
        # Add proper JS structure
        lines = js_code.split('\n')
        processed_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                if 'function ' in stripped:
                    processed_lines.append(' ' * (indent_level * 4) + stripped)
                    indent_level += 1
                elif stripped == '}':
                    indent_level = max(0, indent_level - 1)
                    processed_lines.append(' ' * (indent_level * 4) + '}')
                else:
                    processed_lines.append(' ' * (indent_level * 4) + stripped)
            else:
                processed_lines.append('')
        
        # Add closing braces for functions
        function_count = js_code.count('function ')
        brace_count = js_code.count('}')
        if function_count > brace_count:
            for _ in range(function_count - brace_count):
                processed_lines.append('}')
        
        return "// Enhanced migration from Python to JavaScript\n" + '\n'.join(processed_lines)
        
    def _js_to_python_enhanced(self, js_code: str) -> str:
        """Enhanced JavaScript to Python conversion."""
        py_code = js_code
        
        # Function definitions
        py_code = py_code.replace("function ", "def ")
        py_code = py_code.replace(" {", ":")
        py_code = py_code.replace("}", "")
        
        # Boolean values
        py_code = py_code.replace("true", "True")
        py_code = py_code.replace("false", "False")
        py_code = py_code.replace("null", "None")
        
        # Console statements
        py_code = py_code.replace("console.log(", "print(")
        
        # Template literals (basic)
        import re
        py_code = re.sub(r'`([^`]*)`', r'f"\1"', py_code)
        py_code = py_code.replace("${", "{")
        
        return "# Enhanced migration from JavaScript to Python\n" + py_code
        
    def _mock_migration_response(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Generate a mock migration response for testing/development."""
        logger.info("Using mock migration response")
        
        # Simple mock translation for demonstration
        mock_migrations = {
            ('python', 'javascript'): self._python_to_javascript_mock,
            ('javascript', 'python'): self._javascript_to_python_mock,
            ('python', 'java'): self._python_to_java_mock,
            ('java', 'python'): self._java_to_python_mock
        }
        
        migration_func = mock_migrations.get((source_language, target_language))
        if migration_func:
            migrated_code = migration_func(source_code)
        else:
            migrated_code = f"// Migrated from {source_language} to {target_language}\n" + source_code
            
        return {
            "success": True,
            "migrated_code": migrated_code,
            "confidence": 0.75,  # Mock confidence score
            "warnings": ["This is a mock migration for development purposes"],
            "errors": [],
            "suggestions": [f"Consider optimizing for {target_language} idioms"]
        }
        
    def _mock_analysis_response(self, source_code: str, language: str) -> Dict[str, Any]:
        """Generate a mock analysis response."""
        return {
            "success": True,
            "analysis": {
                "functions": ["mock_function_1", "mock_function_2"],
                "classes": ["MockClass"],
                "complexity_score": 3.5,
                "dependencies": ["mock_dependency"]
            },
            "confidence": 0.8
        }
        
    def _mock_improvement_suggestions(self, target_language: str) -> List[str]:
        """Generate mock improvement suggestions."""
        return [
            f"Use {target_language}-specific idioms for better performance",
            f"Consider {target_language} standard library alternatives",
            "Add appropriate error handling",
            "Optimize for readability"
        ]
        
    def _python_to_javascript_mock(self, python_code: str) -> str:
        """Mock Python to JavaScript conversion."""
        # Very basic string replacements for demo
        js_code = python_code
        js_code = js_code.replace("def ", "function ")
        js_code = js_code.replace(":", " {")
        js_code = js_code.replace("True", "true")
        js_code = js_code.replace("False", "false")
        js_code = js_code.replace("None", "null")
        js_code = js_code.replace("print(", "console.log(")
        
        # Add basic structure
        return f"// Converted from Python\n{js_code}\n// End conversion"
        
    def _javascript_to_python_mock(self, js_code: str) -> str:
        """Mock JavaScript to Python conversion."""
        py_code = js_code
        py_code = py_code.replace("function ", "def ")
        py_code = py_code.replace("true", "True")
        py_code = py_code.replace("false", "False")
        py_code = py_code.replace("null", "None")
        py_code = py_code.replace("console.log(", "print(")
        
        return f"# Converted from JavaScript\n{py_code}\n# End conversion"
        
    def _python_to_java_mock(self, python_code: str) -> str:
        """Mock Python to Java conversion."""
        return f"// Converted from Python\npublic class ConvertedCode {{\n    // {python_code}\n}}"
        
    def _java_to_python_mock(self, java_code: str) -> str:
        """Mock Java to Python conversion."""
        return f"# Converted from Java\n# {java_code}\npass"