"""
Tool Recommendation Engine for Darwin System

This module provides intelligent tool recommendations based on context, past usage,
and task requirements. It analyzes available tools and suggests the most appropriate
ones for given scenarios.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime
import hashlib


class ToolRecommendationEngine:
    """
    Engine for recommending tools based on context, usage patterns, and requirements.
    
    Analyzes tool metadata, usage history, and task context to provide intelligent
    tool suggestions that enhance development workflow.
    """
    
    def __init__(self):
        """Initialize the tool recommendation engine."""
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
        self.usage_history: List[Dict[str, Any]] = []
        self.tool_relationships: Dict[str, Set[str]] = defaultdict(set)
        self.category_map: Dict[str, List[str]] = defaultdict(list)
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        
    def register_tool(
        self,
        tool_name: str,
        description: str,
        categories: List[str],
        keywords: List[str],
        parameters: List[str],
        capabilities: List[str],
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Register a tool in the recommendation engine.
        
        Args:
            tool_name: Name of the tool
            description: Tool description
            categories: List of categories the tool belongs to
            keywords: Keywords associated with the tool
            parameters: List of parameter names
            capabilities: List of capabilities the tool provides
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Registration confirmation with tool details
        """
        try:
            tool_id = self._generate_tool_id(tool_name)
            
            self.tool_registry[tool_id] = {
                'name': tool_name,
                'description': description,
                'categories': categories,
                'keywords': keywords,
                'parameters': parameters,
                'capabilities': capabilities,
                'registered_at': datetime.now().isoformat(),
                'usage_count': 0,
                'success_rate': 1.0
            }
            
            for category in categories:
                self.category_map[category].append(tool_id)
            
            for keyword in keywords:
                self.keyword_index[keyword.lower()].add(tool_id)
            
            return {
                'status': 'success',
                'tool_id': tool_id,
                'tool_name': tool_name,
                'message': f'Tool {tool_name} registered successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'tool_name': tool_name,
                'error': str(e)
            }
    
    def recommend_tools(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Recommend tools based on task description and context.
        
        Args:
            task_description: Description of the task to accomplish
            context: Optional context information (categories, previous tools, etc.)
            top_k: Number of top recommendations to return
            **kwargs: Additional compatibility parameters
            
        Returns:
            List of recommended tools with relevance scores
        """
        try:
            if not self.tool_registry:
                return []
            
            context = context or {}
            scores: Dict[str, float] = {}
            
            for tool_id, tool_info in self.tool_registry.items():
                score = self._calculate_relevance_score(
                    tool_id,
                    tool_info,
                    task_description,
                    context
                )
                scores[tool_id] = score
            
            sorted_tools = sorted(
                scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            recommendations = []
            for tool_id, score in sorted_tools:
                if score > 0:
                    tool_info = self.tool_registry[tool_id]
                    recommendations.append({
                        'tool_id': tool_id,
                        'tool_name': tool_info['name'],
                        'description': tool_info['description'],
                        'relevance_score': round(score, 3),
                        'categories': tool_info['categories'],
                        'usage_count': tool_info['usage_count'],
                        'success_rate': tool_info['success_rate'],
                        'reason': self._generate_recommendation_reason(
                            tool_info,
                            task_description,
                            score
                        )
                    })
            
            return recommendations
        except Exception as e:
            return [{
                'status': 'error',
                'error': str(e),
                'recommendations': []
            }]
    
    def record_tool_usage(
        self,
        tool_name: str,
        task_description: str,
        success: bool,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Record tool usage for learning and improving recommendations.
        
        Args:
            tool_name: Name of the tool used
            task_description: Description of the task
            success: Whether the tool usage was successful
            context: Optional context information
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Confirmation of usage recording
        """
        try:
            tool_id = self._find_tool_id(tool_name)
            if not tool_id:
                return {
                    'status': 'error',
                    'message': f'Tool {tool_name} not found in registry'
                }
            
            usage_record = {
                'tool_id': tool_id,
                'tool_name': tool_name,
                'task_description': task_description,
                'success': success,
                'context': context or {},
                'timestamp': datetime.now().isoformat()
            }
            
            self.usage_history.append(usage_record)
            
            tool_info = self.tool_registry[tool_id]
            tool_info['usage_count'] += 1
            
            total_uses = tool_info['usage_count']
            current_successes = tool_info['success_rate'] * (total_uses - 1)
            new_successes = current_successes + (1 if success else 0)
            tool_info['success_rate'] = new_successes / total_uses
            
            if context and 'related_tools' in context:
                for related_tool in context['related_tools']:
                    self.tool_relationships[tool_id].add(related_tool)
            
            return {
                'status': 'success',
                'message': 'Usage recorded successfully',
                'tool_name': tool_name,
                'updated_success_rate': tool_info['success_rate']
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_tool_analytics(
        self,
        tool_name: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get analytics and statistics about tool usage.
        
        Args:
            tool_name: Optional specific tool name (None for all tools)
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Analytics data including usage patterns and success rates
        """
        try:
            if tool_name:
                tool_id = self._find_tool_id(tool_name)
                if not tool_id:
                    return {
                        'status': 'error',
                        'message': f'Tool {tool_name} not found'
                    }
                
                tool_info = self.tool_registry[tool_id]
                tool_usage = [
                    record for record in self.usage_history
                    if record['tool_id'] == tool_id
                ]
                
                return {
                    'status': 'success',
                    'tool_name': tool_name,
                    'usage_count': tool_info['usage_count'],
                    'success_rate': tool_info['success_rate'],
                    'categories': tool_info['categories'],
                    'related_tools': list(self.tool_relationships.get(tool_id, [])),
                    'recent_usage': tool_usage[-10:]
                }
            else:
                total_tools = len(self.tool_registry)
                total_usage = sum(
                    tool['usage_count']
                    for tool in self.tool_registry.values()
                )
                
                avg_success_rate = (
                    sum(tool['success_rate'] for tool in self.tool_registry.values()) /
                    total_tools if total_tools > 0 else 0
                )
                
                most_used = sorted(
                    self.tool_registry.items(),
                    key=lambda x: x[1]['usage_count'],
                    reverse=True
                )[:5]
                
                return {
                    'status': 'success',
                    'total_tools': total_tools,
                    'total_usage': total_usage,
                    'average_success_rate': round(avg_success_rate, 3),
                    'most_used_tools': [
                        {
                            'name': tool[1]['name'],
                            'usage_count': tool[1]['usage_count'],
                            'success_rate': tool[1]['success_rate']
                        }
                        for tool in most_used
                    ],
                    'category_distribution': {
                        category: len(tools)
                        for category, tools in self.category_map.items()
                    }
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def suggest_tool_combinations(
        self,
        task_description: str,
        top_k: int = 3,
        **kwargs
    ) -> List[List[Dict[str, Any]]]:
        """
        Suggest combinations of tools that work well together.
        
        Args:
            task_description: Description of the complex task
            top_k: Number of combinations to suggest
            **kwargs: Additional compatibility parameters
            
        Returns:
            List of tool combinations with explanations
        """
        try:
            initial_tools = self.recommend_tools(task_description, top_k=top_k * 2)
            
            if not initial_tools:
                return []
            
            combinations = []
            
            for i, tool in enumerate(initial_tools[:top_k]):
                combination = [tool]
                tool_id = tool['tool_id']
                
                if tool_id in self.tool_relationships:
                    related_ids = self.tool_relationships[tool_id]
                    for related_id in list(related_ids)[:2]:
                        if related_id in self.tool_registry:
                            related_tool = self.tool_registry[related_id]
                            combination.append({
                                'tool_id': related_id,
                                'tool_name': related_tool['name'],
                                'description': related_tool['description'],
                                'relationship': 'frequently_used_together'
                            })
                
                if len(combination) > 1:
                    combinations.append(combination)
            
            return combinations[:top_k]
        except Exception as e:
            return []
    
    def find_similar_tools(
        self,
        tool_name: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Find tools similar to the specified tool.
        
        Args:
            tool_name: Name of the reference tool
            top_k: Number of similar tools to return
            **kwargs: Additional compatibility parameters
            
        Returns:
            List of similar tools with similarity scores
        """
        try:
            tool_id = self._find_tool_id(tool_name)
            if not tool_id:
                return []
            
            reference_tool = self.tool_registry[tool_id]
            similarities: Dict[str, float] = {}
            
            for other_id, other_tool in self.tool_registry.items():
                if other_id == tool_id:
                    continue
                
                similarity = self._calculate_similarity(
                    reference_tool,
                    other_tool
                )
                similarities[other_id] = similarity
            
            sorted_similar = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            similar_tools = []
            for other_id, similarity in sorted_similar:
                other_tool = self.tool_registry[other_id]
                similar_tools.append({
                    'tool_id': other_id,
                    'tool_name': other_tool['name'],
                    'description': other_tool['description'],
                    'similarity_score': round(similarity, 3),
                    'common_categories': list(
                        set(reference_tool['categories']) &
                        set(other_tool['categories'])
                    )
                })
            
            return similar_tools
        except Exception as e:
            return []
    
    def _generate_tool_id(self, tool_name: str) -> str:
        """Generate a unique tool ID from the tool name."""
        return hashlib.md5(tool_name.encode()).hexdigest()[:16]
    
    def _find_tool_id(self, tool_name: str) -> Optional[str]:
        """Find tool ID by tool name."""
        for tool_id, tool_info in self.tool_registry.items():
            if tool_info['name'] == tool_name:
                return tool_id
        return None
    
    def _calculate_relevance_score(
        self,
        tool_id: str,
        tool_info: Dict[str, Any],
        task_description: str,
        context: Dict[str, Any]
    ) -> float:
        """Calculate relevance score for a tool given task and context."""
        score = 0.0
        task_lower = task_description.lower()
        task_words = set(re.findall(r'\w+', task_lower))
        
        description_words = set(
            re.findall(r'\w+', tool_info['description'].lower())
        )
        keyword_matches = len(task_words & description_words)
        score += keyword_matches * 0.3
        
        for keyword in tool_info['keywords']:
            if keyword.lower() in task_lower:
                score += 0.5
        
        if 'categories' in context:
            category_overlap = len(
                set(context['categories']) & set(tool_info['categories'])
            )
            score += category_overlap * 0.8
        
        usage_factor = min(tool_info['usage_count'] / 10.0, 1.0)
        score += usage_factor * 0.3
        
        score += tool_info['success_rate'] * 0.4
        
        if 'previous_tools' in context:
            for prev_tool in context['previous_tools']:
                prev_id = self._find_tool_id(prev_tool)
                if prev_id and tool_id in self.tool_relationships.get(prev_id, set()):
                    score += 0.6
        
        return score
    
    def _calculate_similarity(
        self,
        tool1: Dict[str, Any],
        tool2: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between two tools."""
        similarity = 0.0
        
        category_overlap = len(
            set(tool1['categories']) & set(tool2['categories'])
        )
        category_union = len(
            set(tool1['categories']) | set(tool2['categories'])
        )
        if category_union > 0:
            similarity += (category_overlap / category_union) * 0.4
        
        keyword_overlap = len(
            set(tool1['keywords']) & set(tool2['keywords'])
        )
        keyword_union = len(
            set(tool1['keywords']) | set(tool2['keywords'])
        )
        if keyword_union > 0:
            similarity += (keyword_overlap / keyword_union) * 0.3
        
        capability_overlap = len(
            set(tool1['capabilities']) & set(tool2['capabilities'])
        )
        capability_union = len(
            set(tool1['capabilities']) | set(tool2['capabilities'])
        )
        if capability_union > 0:
            similarity += (capability_overlap / capability_union) * 0.3
        
        return similarity
    
    def _generate_recommendation_reason(
        self,
        tool_info: Dict[str, Any],
        task_description: str,
        score: float
    ) -> str:
        """Generate a human-readable reason for the recommendation."""
        reasons = []
        
        task_lower = task_description.lower()
        
        matching_keywords = [
            kw for kw in tool_info['keywords']
            if kw.lower() in task_lower
        ]
        if matching_keywords:
            reasons.append(
                f"Matches keywords: {', '.join(matching_keywords[:3])}"
            )
        
        if tool_info['usage_count'] > 5:
            reasons.append(
                f"Frequently used ({tool_info['usage_count']} times)"
            )
        
        if tool_info['success_rate'] > 0.8:
            reasons.append(
                f"High success rate ({tool_info['success_rate']:.1%})"
            )
        
        if tool_info['categories']:
            reasons.append(
                f"Categories: {', '.join(tool_info['categories'][:2])}"
            )
        
        if not reasons:
            reasons.append("General relevance to task")
        
        return "; ".join(reasons)


def create_recommendation_engine(top_k: int = None, **kwargs) -> ToolRecommendationEngine:
    """
    Factory function to create a new tool recommendation engine instance.
    
    Args:
        top_k: For compatibility with tool registry
        **kwargs: Additional compatibility parameters
        
    Returns:
        New ToolRecommendationEngine instance
    """
    return ToolRecommendationEngine()


def recommend_tools_for_task(
    task_description: str,
    engine: Optional[ToolRecommendationEngine] = None,
    top_k: int = 5,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Convenience function to get tool recommendations for a task.
    
    Args:
        task_description: Description of the task
        engine: Optional existing engine instance
        top_k: Number of recommendations to return
        **kwargs: Additional compatibility parameters
        
    Returns:
        List of recommended tools
    """
    if engine is None:
        engine = ToolRecommendationEngine()
    
    try:
        return engine.recommend_tools(task_description, top_k=top_k)
    except Exception as e:
        return [{
            'status': 'error',
            'error': str(e),
            'recommendations': []
        }]


if __name__ == '__main__':
    engine = create_recommendation_engine()
    
    engine.register_tool(
        tool_name='code_analyzer',
        description='Analyzes code quality and provides suggestions',
        categories=['analysis', 'quality'],
        keywords=['code', 'analyze', 'quality', 'review'],
        parameters=['file_path', 'language'],
        capabilities=['static_analysis', 'code_review', 'metrics']
    )
    
    engine.register_tool(
        tool_name='test_generator',
        description='Generates unit tests for code',
        categories=['testing', 'automation'],
        keywords=['test', 'unit', 'generate', 'coverage'],
        parameters=['code_path', 'framework'],
        capabilities=['test_generation', 'coverage_analysis']
    )
    
    engine.register_tool(
        tool_name='documentation_builder',
        description='Creates documentation from code',
        categories=['documentation', 'automation'],
        keywords=['docs', 'documentation', 'generate', 'api'],
        parameters=['source_dir', 'output_format'],
        capabilities=['doc_generation', 'api_docs']
    )
    
    recommendations = engine.recommend_tools(
        'I need to analyze my code quality and find issues',
        top_k=3
    )
    
    print('Tool Recommendations:')
    for rec in recommendations:
        print(f"\n- {rec['tool_name']}")
        print(f"  Score: {rec['relevance_score']}")
        print(f"  Reason: {rec['reason']}")
    
    engine.record_tool_usage(
        'code_analyzer',
        'Analyzed Python code for quality issues',
        success=True
    )
    
    analytics = engine.get_tool_analytics()
    print(f"\nTotal tools registered: {analytics['total_tools']}")
    print(f"Average success rate: {analytics['average_success_rate']}")