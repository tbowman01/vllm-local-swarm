"""
Researcher Agent for SPARC Multi-Agent Framework

The Researcher agent specializes in information gathering, evidence synthesis, and knowledge discovery.
It performs web searches, analyzes documentation, queries knowledge bases, and provides well-sourced
research reports to support other agents' work.

Core capabilities: Information retrieval, source verification, evidence triangulation, knowledge synthesis
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging
from urllib.parse import urlparse
import re

import ray
from .base_agent import BaseAgent, AgentMessage, MessageType, AgentStatus


class ResearchSource:
    """Structured representation of a research source"""
    
    def __init__(self, url: str, title: str, content: str, source_type: str, credibility_score: float = 0.0):
        self.id = str(uuid.uuid4())
        self.url = url
        self.title = title
        self.content = content
        self.source_type = source_type  # "web", "documentation", "paper", "api", etc.
        self.credibility_score = credibility_score
        self.retrieved_at = datetime.utcnow()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "source_type": self.source_type,
            "credibility_score": self.credibility_score,
            "retrieved_at": self.retrieved_at.isoformat(),
            "metadata": self.metadata
        }


@ray.remote
class ResearcherAgent(BaseAgent):
    """
    Researcher Agent - Information Specialist
    
    Core Responsibilities:
    - Gather information from multiple sources (web, docs, APIs, databases)
    - Verify source credibility and cross-reference information
    - Synthesize findings into structured reports
    - Provide evidence-based recommendations
    - Maintain source attribution and citations
    - Support other agents with knowledge and context
    """
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            role="researcher",
            capabilities=[
                "web_search",
                "document_analysis",
                "source_verification",
                "evidence_triangulation",
                "knowledge_synthesis",
                "citation_management",
                "fact_checking"
            ],
            model_config=kwargs.get("model_config", {"model": "phi-3.5", "temperature": 0.2}),
            memory_config=kwargs.get("memory_config", {}),
            **kwargs
        )
        
        # Researcher-specific state
        self.source_database: Dict[str, ResearchSource] = {}
        self.search_history: List[Dict[str, Any]] = []
        self.credibility_thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        self.research_templates = {}
        
        # Load research templates and credibility rules
        self._load_research_templates()
        self._load_credibility_rules()
    
    def _load_system_prompt(self) -> str:
        """Load Researcher agent system prompt with evidence-based methodology"""
        return """
You are the Researcher Agent, the information specialist in a SPARC-aligned multi-agent system.

CORE ROLE: Information gathering, evidence synthesis, and knowledge discovery

RESPONSIBILITIES:
1. GATHER information from authoritative and diverse sources
2. VERIFY source credibility and reliability using established criteria
3. TRIANGULATE evidence across multiple independent sources
4. SYNTHESIZE findings into structured, well-documented reports
5. PROVIDE proper citations and source attribution
6. SUPPORT other agents with relevant context and knowledge

INFORMATION GATHERING STRATEGY:
- Primary sources: Official documentation, academic papers, authoritative websites
- Secondary sources: Technical blogs, tutorials, community discussions
- Verification: Cross-reference critical information across multiple sources
- Recency: Prioritize recent information but consider historical context
- Diversity: Seek varied perspectives and approaches

EVIDENCE TRIANGULATION METHOD:
1. Identify multiple independent sources for key claims
2. Compare information consistency across sources
3. Note discrepancies and investigate further
4. Assess source quality and potential bias
5. Synthesize consensus view with noted uncertainties

SOURCE CREDIBILITY ASSESSMENT:
- Authority: Author expertise, institutional affiliation
- Accuracy: Factual correctness, internal consistency  
- Objectivity: Bias assessment, commercial interests
- Currency: Publication date, update frequency
- Coverage: Completeness, depth of information

RESEARCH REPORT STRUCTURE:
For each research task, provide:
- Executive Summary: Key findings and recommendations
- Methodology: Sources searched, criteria used
- Findings: Organized by topic/question with evidence
- Sources: Complete citation list with credibility scores
- Confidence Assessment: Reliability of each finding
- Recommendations: Actionable next steps based on evidence
- Gaps and Limitations: Areas needing further research

CITATION FORMAT:
- Source Title (Author/Organization, Date)
- URL and access date
- Credibility score and reasoning
- Relevant excerpt or summary
- How it supports the finding

QUALITY STANDARDS:
- Minimum 3 sources for any significant claim
- Always provide source attribution
- Flag uncertain or contradictory information
- Distinguish between facts, opinions, and speculation
- Update findings when new evidence emerges

COLLABORATION PROTOCOL:
- Provide research context to support other agents
- Answer queries with evidence-backed responses
- Flag when insufficient evidence exists
- Suggest additional research directions
- Share relevant sources proactively

Focus on accuracy, thoroughness, and proper documentation. Be systematic in your
approach and maintain the highest standards of research integrity.
"""
    
    def _initialize_tools(self):
        """Initialize Researcher-specific tools and capabilities"""
        self.available_tools = {
            "web_searcher": self._search_web,
            "document_analyzer": self._analyze_document,
            "source_verifier": self._verify_source,
            "evidence_triangulator": self._triangulate_evidence,
            "knowledge_synthesizer": self._synthesize_knowledge,
            "citation_manager": self._manage_citations,
            "credibility_assessor": self._assess_credibility
        }
    
    def _load_research_templates(self):
        """Load templates for different types of research tasks"""
        self.research_templates = {
            "technical_research": {
                "sections": [
                    "overview",
                    "technical_specifications",
                    "implementation_approaches",
                    "best_practices",
                    "limitations_and_considerations",
                    "sources"
                ],
                "min_sources": 5,
                "credibility_threshold": "medium"
            },
            "comparative_analysis": {
                "sections": [
                    "alternatives_overview",
                    "feature_comparison",
                    "performance_analysis",
                    "use_case_recommendations",
                    "sources"
                ],
                "min_sources": 3,
                "credibility_threshold": "medium"
            },
            "problem_investigation": {
                "sections": [
                    "problem_definition",
                    "root_cause_analysis",
                    "known_solutions",
                    "recommended_approach",
                    "sources"
                ],
                "min_sources": 4,
                "credibility_threshold": "high"
            }
        }
    
    def _load_credibility_rules(self):
        """Load rules for assessing source credibility"""
        self.credibility_rules = {
            "domain_authority": {
                ".edu": 0.9,
                ".gov": 0.9,
                ".org": 0.7,
                "github.com": 0.8,
                "stackoverflow.com": 0.7,
                "medium.com": 0.5,
                "blog": 0.4
            },
            "source_types": {
                "documentation": 0.9,
                "academic_paper": 0.9,
                "official_guide": 0.8,
                "technical_blog": 0.6,
                "forum_post": 0.4,
                "tutorial": 0.5
            },
            "recency_bonus": {
                "days_30": 0.1,
                "days_90": 0.05,
                "days_365": 0.0,
                "older": -0.1
            }
        }
    
    async def _execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research task with systematic information gathering and synthesis
        
        Args:
            task_data: Research query, scope, requirements, etc.
            
        Returns:
            Structured research report with findings and sources
        """
        try:
            query = task_data.get("description", "")
            research_type = task_data.get("research_type", "technical_research")
            depth = task_data.get("depth", "medium")  # "shallow", "medium", "deep"
            specific_questions = task_data.get("questions", [])
            constraints = task_data.get("constraints", {})
            
            self.logger.info(f"Starting research for: {query}")
            
            # Phase 1: Query Analysis and Planning
            research_plan = await self._plan_research(query, research_type, specific_questions, depth)
            
            # Phase 2: Information Gathering
            sources = await self._gather_information(research_plan)
            
            # Phase 3: Source Verification and Credibility Assessment
            verified_sources = await self._verify_and_assess_sources(sources)
            
            # Phase 4: Evidence Triangulation
            triangulated_evidence = await self._triangulate_evidence(verified_sources, research_plan)
            
            # Phase 5: Knowledge Synthesis
            research_report = await self._synthesize_research_report(
                query, research_plan, triangulated_evidence, verified_sources
            )
            
            # Phase 6: Quality Assessment
            quality_metrics = await self._assess_research_quality(research_report, verified_sources)
            
            return {
                "status": "completed",
                "research_query": query,
                "research_type": research_type,
                "report": research_report,
                "sources": [source.to_dict() for source in verified_sources],
                "quality_metrics": quality_metrics,
                "confidence_level": quality_metrics.get("overall_confidence", 0.7),
                "tokens_used": research_report.get("tokens_used", 0),
                "processing_time": research_report.get("processing_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in research task: {e}")
            return {
                "status": "error",
                "error": str(e),
                "partial_research": getattr(self, '_partial_research', {})
            }
    
    async def _plan_research(self, query: str, research_type: str, questions: List[str], depth: str) -> Dict[str, Any]:
        """Plan research approach based on query and requirements"""
        template = self.research_templates.get(research_type, self.research_templates["technical_research"])
        
        # Analyze query to extract key concepts and search terms
        key_concepts = await self._extract_key_concepts(query)
        search_strategies = await self._develop_search_strategies(key_concepts, questions)
        
        research_plan = {
            "query": query,
            "research_type": research_type,
            "depth": depth,
            "key_concepts": key_concepts,
            "specific_questions": questions,
            "search_strategies": search_strategies,
            "target_sections": template["sections"],
            "min_sources": template["min_sources"],
            "credibility_threshold": template["credibility_threshold"],
            "estimated_time": self._estimate_research_time(depth, len(questions))
        }
        
        await self.update_memory("current_research_plan", research_plan)
        return research_plan
    
    async def _extract_key_concepts(self, query: str) -> List[str]:
        """Extract key concepts and terms from research query"""
        # Simple implementation - in production would use NLP/LLM
        # Remove common words and extract meaningful terms
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        
        words = re.findall(r'\w+', query.lower())
        key_concepts = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Add technical term patterns
        technical_patterns = re.findall(r'[A-Z][a-zA-Z0-9]*(?:\.[a-zA-Z0-9]+)*', query)  # APIs, libraries, etc.
        key_concepts.extend(technical_patterns)
        
        return list(set(key_concepts))
    
    async def _develop_search_strategies(self, concepts: List[str], questions: List[str]) -> List[Dict[str, Any]]:
        """Develop search strategies for different information sources"""
        strategies = []
        
        # Primary search: Official documentation
        strategies.append({
            "strategy": "official_documentation",
            "search_terms": [f"{concept} documentation" for concept in concepts[:3]],
            "sources": ["official sites", "docs", "specifications"],
            "priority": "high"
        })
        
        # Secondary search: Technical articles and tutorials
        strategies.append({
            "strategy": "technical_articles",
            "search_terms": [f"{concept} tutorial", f"{concept} guide" for concept in concepts[:3]],
            "sources": ["technical blogs", "tutorials", "guides"],
            "priority": "medium"
        })
        
        # Tertiary search: Community discussions and Q&A
        strategies.append({
            "strategy": "community_discussion",
            "search_terms": [f"{concept} stackoverflow", f"{concept} github issues" for concept in concepts[:2]],
            "sources": ["stackoverflow", "github", "forums"],
            "priority": "medium"
        })
        
        # Question-specific searches
        for question in questions:
            question_concepts = await self._extract_key_concepts(question)
            strategies.append({
                "strategy": "question_specific",
                "search_terms": [question] + question_concepts,
                "sources": ["all"],
                "priority": "high",
                "question": question
            })
        
        return strategies
    
    def _estimate_research_time(self, depth: str, num_questions: int) -> int:
        """Estimate research time in minutes"""
        base_time = {"shallow": 5, "medium": 15, "deep": 30}
        question_time = num_questions * 3
        return base_time.get(depth, 15) + question_time
    
    async def _gather_information(self, research_plan: Dict[str, Any]) -> List[ResearchSource]:
        """Gather information using multiple search strategies"""
        all_sources = []
        
        for strategy in research_plan["search_strategies"]:
            self.logger.info(f"Executing search strategy: {strategy['strategy']}")
            
            sources = await self._execute_search_strategy(strategy)
            all_sources.extend(sources)
            
            # Store search in history
            self.search_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "strategy": strategy["strategy"],
                "search_terms": strategy["search_terms"],
                "results_found": len(sources)
            })
        
        return all_sources
    
    async def _execute_search_strategy(self, strategy: Dict[str, Any]) -> List[ResearchSource]:
        """Execute a specific search strategy"""
        sources = []
        
        for search_term in strategy["search_terms"]:
            try:
                # In a real implementation, this would call actual search APIs
                # For now, simulate finding sources
                simulated_sources = await self._simulate_web_search(search_term, strategy)
                sources.extend(simulated_sources)
                
            except Exception as e:
                self.logger.warning(f"Search failed for '{search_term}': {e}")
        
        return sources
    
    async def _simulate_web_search(self, search_term: str, strategy: Dict[str, Any]) -> List[ResearchSource]:
        """Simulate web search results (placeholder for actual search implementation)"""
        # In production, this would use actual search APIs like Google Custom Search,
        # scrape documentation sites, query GitHub, etc.
        
        simulated_results = [
            ResearchSource(
                url=f"https://docs.example.com/{search_term.replace(' ', '-')}",
                title=f"Official Documentation: {search_term}",
                content=f"Comprehensive documentation for {search_term}...",
                source_type="documentation"
            ),
            ResearchSource(
                url=f"https://github.com/example/{search_term.replace(' ', '-')}",
                title=f"GitHub Repository: {search_term}",
                content=f"Open source implementation of {search_term}...",
                source_type="repository"
            ),
            ResearchSource(
                url=f"https://stackoverflow.com/questions/example-{search_term.replace(' ', '-')}",
                title=f"Stack Overflow: How to use {search_term}",
                content=f"Community discussion about {search_term}...",
                source_type="forum_post"
            )
        ]
        
        # Add to source database
        for source in simulated_results:
            self.source_database[source.id] = source
        
        return simulated_results
    
    async def _verify_and_assess_sources(self, sources: List[ResearchSource]) -> List[ResearchSource]:
        """Verify source accessibility and assess credibility"""
        verified_sources = []
        
        for source in sources:
            try:
                # Assess credibility
                credibility_score = await self._assess_source_credibility(source)
                source.credibility_score = credibility_score
                
                # Filter by credibility threshold
                research_plan = await self.retrieve_memory("current_research_plan")
                threshold = self.credibility_thresholds.get(
                    research_plan.get("credibility_threshold", "medium"), 0.5
                )
                
                if credibility_score >= threshold:
                    verified_sources.append(source)
                    self.logger.info(f"Source verified: {source.title} (score: {credibility_score:.2f})")
                else:
                    self.logger.info(f"Source filtered out: {source.title} (score: {credibility_score:.2f})")
                    
            except Exception as e:
                self.logger.warning(f"Failed to verify source {source.url}: {e}")
        
        return verified_sources
    
    async def _assess_source_credibility(self, source: ResearchSource) -> float:
        """Assess credibility of a source using multiple criteria"""
        score = 0.5  # Base score
        
        # Domain authority assessment
        domain = urlparse(source.url).netloc.lower()
        for domain_pattern, authority_score in self.credibility_rules["domain_authority"].items():
            if domain_pattern in domain:
                score += authority_score * 0.3
                break
        
        # Source type assessment
        source_type_score = self.credibility_rules["source_types"].get(source.source_type, 0.5)
        score += source_type_score * 0.4
        
        # Recency assessment (would need actual date parsing)
        # For now, assume moderate recency
        score += 0.05
        
        # Content quality indicators (simplified)
        content_quality = await self._assess_content_quality(source.content)
        score += content_quality * 0.25
        
        return min(1.0, max(0.0, score))
    
    async def _assess_content_quality(self, content: str) -> float:
        """Assess quality of content based on various indicators"""
        if not content:
            return 0.0
        
        quality_score = 0.5
        
        # Length indicator (reasonable content length)
        if 100 < len(content) < 5000:
            quality_score += 0.1
        
        # Technical terms presence
        technical_terms = ["API", "function", "method", "class", "library", "framework"]
        if any(term in content for term in technical_terms):
            quality_score += 0.2
        
        # Code examples presence
        if "```" in content or "def " in content or "class " in content:
            quality_score += 0.2
        
        return min(1.0, quality_score)
    
    async def _triangulate_evidence(self, sources: List[ResearchSource], research_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Triangulate evidence across multiple sources to identify consensus and conflicts"""
        evidence_points = {}
        
        # Extract key claims and information from each source
        for source in sources:
            claims = await self._extract_claims_from_source(source)
            
            for claim in claims:
                claim_key = claim["key"]
                if claim_key not in evidence_points:
                    evidence_points[claim_key] = {
                        "claim": claim["text"],
                        "supporting_sources": [],
                        "conflicting_sources": [],
                        "confidence": 0.0
                    }
                
                # Add source as supporting evidence
                evidence_points[claim_key]["supporting_sources"].append({
                    "source_id": source.id,
                    "source_title": source.title,
                    "credibility": source.credibility_score,
                    "excerpt": claim["excerpt"]
                })
        
        # Calculate confidence for each evidence point
        for claim_key, evidence in evidence_points.items():
            # Confidence based on number of sources and their credibility
            source_count = len(evidence["supporting_sources"])
            avg_credibility = sum(s["credibility"] for s in evidence["supporting_sources"]) / source_count
            
            # Confidence formula: (source_count * avg_credibility) / max_possible_score
            evidence["confidence"] = min(1.0, (source_count * avg_credibility) / 3.0)
        
        # Identify high-confidence consensus findings
        consensus_findings = {
            k: v for k, v in evidence_points.items() 
            if v["confidence"] >= 0.7 and len(v["supporting_sources"]) >= 2
        }
        
        # Identify uncertain or conflicting information
        uncertain_findings = {
            k: v for k, v in evidence_points.items()
            if v["confidence"] < 0.5 or len(v["supporting_sources"]) < 2
        }
        
        return {
            "all_evidence": evidence_points,
            "consensus_findings": consensus_findings,
            "uncertain_findings": uncertain_findings,
            "total_claims": len(evidence_points),
            "high_confidence_claims": len(consensus_findings)
        }
    
    async def _extract_claims_from_source(self, source: ResearchSource) -> List[Dict[str, Any]]:
        """Extract key claims and information from source content"""
        # Simplified implementation - in production would use NLP/LLM
        content = source.content
        
        # Extract sentences that look like factual claims
        sentences = content.split('.')
        claims = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 20:  # Reasonable length
                # Create a simple key from first few words
                words = sentence.split()[:5]
                claim_key = "_".join(w.lower() for w in words if w.isalnum())
                
                claims.append({
                    "key": claim_key,
                    "text": sentence,
                    "excerpt": sentence[:200] + "..." if len(sentence) > 200 else sentence
                })
        
        return claims[:10]  # Limit to avoid too many claims
    
    async def _synthesize_research_report(
        self, 
        query: str, 
        research_plan: Dict[str, Any], 
        evidence: Dict[str, Any], 
        sources: List[ResearchSource]
    ) -> Dict[str, Any]:
        """Synthesize findings into structured research report"""
        
        template = self.research_templates.get(
            research_plan["research_type"], 
            self.research_templates["technical_research"]
        )
        
        report = {
            "executive_summary": await self._generate_executive_summary(query, evidence),
            "methodology": {
                "search_strategies": research_plan["search_strategies"],
                "sources_found": len(sources),
                "sources_used": len([s for s in sources if s.credibility_score >= 0.5]),
                "credibility_threshold": research_plan["credibility_threshold"]
            },
            "findings": {},
            "sources": self._format_source_citations(sources),
            "confidence_assessment": self._assess_overall_confidence(evidence),
            "recommendations": await self._generate_recommendations(evidence, sources),
            "gaps_and_limitations": await self._identify_research_gaps(evidence, research_plan)
        }
        
        # Populate findings by template sections
        for section in template["sections"]:
            if section != "sources":
                report["findings"][section] = await self._generate_section_content(
                    section, evidence, sources, query
                )
        
        return report
    
    async def _generate_executive_summary(self, query: str, evidence: Dict[str, Any]) -> str:
        """Generate executive summary of research findings"""
        consensus_count = len(evidence.get("consensus_findings", {}))
        total_claims = evidence.get("total_claims", 0)
        
        summary = f"Research conducted on: {query}\n\n"
        summary += f"Key findings: {consensus_count} high-confidence conclusions from {total_claims} analyzed claims.\n"
        
        # Highlight top findings
        consensus_findings = evidence.get("consensus_findings", {})
        if consensus_findings:
            summary += "\nMain conclusions:\n"
            for i, (key, finding) in enumerate(list(consensus_findings.items())[:3]):
                summary += f"• {finding['claim']}\n"
        
        return summary
    
    def _format_source_citations(self, sources: List[ResearchSource]) -> List[Dict[str, Any]]:
        """Format sources as proper citations"""
        citations = []
        
        for source in sorted(sources, key=lambda s: s.credibility_score, reverse=True):
            citation = {
                "title": source.title,
                "url": source.url,
                "type": source.source_type,
                "credibility_score": round(source.credibility_score, 2),
                "retrieved_date": source.retrieved_at.strftime("%Y-%m-%d"),
                "relevance": "high" if source.credibility_score > 0.7 else "medium"
            }
            citations.append(citation)
        
        return citations
    
    def _assess_overall_confidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall confidence in research findings"""
        consensus_findings = evidence.get("consensus_findings", {})
        uncertain_findings = evidence.get("uncertain_findings", {})
        total_claims = evidence.get("total_claims", 1)
        
        confidence_ratio = len(consensus_findings) / total_claims
        uncertainty_ratio = len(uncertain_findings) / total_claims
        
        overall_confidence = "high" if confidence_ratio > 0.7 else "medium" if confidence_ratio > 0.4 else "low"
        
        return {
            "overall_level": overall_confidence,
            "confidence_ratio": round(confidence_ratio, 2),
            "uncertainty_ratio": round(uncertainty_ratio, 2),
            "high_confidence_findings": len(consensus_findings),
            "uncertain_findings": len(uncertain_findings),
            "reliability_notes": self._generate_reliability_notes(evidence)
        }
    
    def _generate_reliability_notes(self, evidence: Dict[str, Any]) -> List[str]:
        """Generate notes about reliability and limitations"""
        notes = []
        
        uncertain_findings = evidence.get("uncertain_findings", {})
        if len(uncertain_findings) > 0:
            notes.append(f"{len(uncertain_findings)} findings have low confidence or limited source support")
        
        consensus_findings = evidence.get("consensus_findings", {})
        if len(consensus_findings) == 0:
            notes.append("No high-confidence consensus findings identified")
        
        return notes
    
    async def _generate_recommendations(self, evidence: Dict[str, Any], sources: List[ResearchSource]) -> List[str]:
        """Generate actionable recommendations based on research"""
        recommendations = []
        
        consensus_findings = evidence.get("consensus_findings", {})
        if consensus_findings:
            recommendations.append("Proceed with implementation based on consensus findings")
        
        uncertain_findings = evidence.get("uncertain_findings", {})
        if uncertain_findings:
            recommendations.append("Conduct additional research on uncertain findings before proceeding")
        
        # Source-based recommendations
        high_quality_sources = [s for s in sources if s.credibility_score > 0.8]
        if high_quality_sources:
            recommendations.append(f"Consult {len(high_quality_sources)} high-quality sources for implementation details")
        
        return recommendations
    
    async def _identify_research_gaps(self, evidence: Dict[str, Any], research_plan: Dict[str, Any]) -> List[str]:
        """Identify gaps in research coverage"""
        gaps = []
        
        # Check if specific questions were answered
        questions = research_plan.get("specific_questions", [])
        if questions:
            # In production, would analyze if each question was adequately addressed
            gaps.append(f"Verification needed for {len(questions)} specific questions")
        
        # Check evidence confidence gaps
        uncertain_findings = evidence.get("uncertain_findings", {})
        if len(uncertain_findings) > 2:
            gaps.append("Multiple findings require additional verification")
        
        return gaps
    
    async def _generate_section_content(self, section: str, evidence: Dict[str, Any], sources: List[ResearchSource], query: str) -> str:
        """Generate content for specific report section"""
        consensus_findings = evidence.get("consensus_findings", {})
        
        if section == "overview":
            return f"Research overview for: {query}\nBased on analysis of {len(sources)} sources."
        
        elif section == "technical_specifications":
            tech_findings = [f for f in consensus_findings.values() if "API" in f["claim"] or "specification" in f["claim"]]
            return "\n".join([f["claim"] for f in tech_findings[:3]])
        
        elif section == "best_practices":
            practice_findings = [f for f in consensus_findings.values() if "best" in f["claim"] or "practice" in f["claim"]]
            return "\n".join([f["claim"] for f in practice_findings[:3]])
        
        else:
            # Generic section content
            relevant_findings = list(consensus_findings.values())[:2]
            return "\n".join([f["claim"] for f in relevant_findings])
    
    async def _assess_research_quality(self, report: Dict[str, Any], sources: List[ResearchSource]) -> Dict[str, Any]:
        """Assess overall quality of research conducted"""
        metrics = {
            "source_count": len(sources),
            "high_credibility_sources": len([s for s in sources if s.credibility_score > 0.7]),
            "average_credibility": sum(s.credibility_score for s in sources) / len(sources) if sources else 0,
            "source_diversity": len(set(s.source_type for s in sources)),
            "coverage_completeness": self._assess_coverage_completeness(report),
            "overall_confidence": report["confidence_assessment"]["overall_level"]
        }
        
        # Calculate overall quality score
        quality_factors = [
            min(1.0, metrics["source_count"] / 5),  # 5+ sources = full score
            min(1.0, metrics["high_credibility_sources"] / 3),  # 3+ high-cred sources
            metrics["average_credibility"],
            min(1.0, metrics["source_diversity"] / 3)  # 3+ source types
        ]
        
        metrics["overall_quality_score"] = sum(quality_factors) / len(quality_factors)
        
        return metrics
    
    def _assess_coverage_completeness(self, report: Dict[str, Any]) -> float:
        """Assess how completely the research covers the intended scope"""
        findings = report.get("findings", {})
        total_sections = len(findings)
        populated_sections = len([v for v in findings.values() if v and v.strip()])
        
        return populated_sections / total_sections if total_sections > 0 else 0.0
    
    async def _process_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process queries for specific information or source verification"""
        query_type = query_data.get("query_type", "information")
        
        if query_type == "information":
            # Quick information lookup
            search_term = query_data.get("search_term", "")
            sources = await self._quick_search(search_term)
            
            return {
                "query_type": "information",
                "search_term": search_term,
                "sources_found": len(sources),
                "top_results": [source.to_dict() for source in sources[:3]],
                "summary": f"Found {len(sources)} relevant sources for '{search_term}'"
            }
        
        elif query_type == "source_verification":
            # Verify credibility of specific source
            url = query_data.get("url", "")
            source_info = await self._verify_single_source(url)
            
            return {
                "query_type": "source_verification",
                "url": url,
                "verification_result": source_info
            }
        
        elif query_type == "knowledge_check":
            # Check existing knowledge on topic
            topic = query_data.get("topic", "")
            relevant_sources = await self._find_relevant_sources(topic)
            
            return {
                "query_type": "knowledge_check",
                "topic": topic,
                "known_sources": len(relevant_sources),
                "knowledge_summary": self._summarize_existing_knowledge(relevant_sources)
            }
        
        return {"result": "Query processed", "query_type": query_type}
    
    async def _quick_search(self, search_term: str) -> List[ResearchSource]:
        """Perform quick search for immediate information needs"""
        # Check existing sources first
        relevant_sources = [
            source for source in self.source_database.values()
            if search_term.lower() in source.content.lower() or search_term.lower() in source.title.lower()
        ]
        
        # If not enough, perform new search
        if len(relevant_sources) < 3:
            new_sources = await self._simulate_web_search(search_term, {"strategy": "quick_search"})
            relevant_sources.extend(new_sources)
        
        return relevant_sources[:5]
    
    async def _verify_single_source(self, url: str) -> Dict[str, Any]:
        """Verify credibility of a single source"""
        # Create temporary source object for analysis
        temp_source = ResearchSource(
            url=url,
            title="Source to verify",
            content="",  # Would fetch content in real implementation
            source_type="unknown"
        )
        
        credibility_score = await self._assess_source_credibility(temp_source)
        
        return {
            "url": url,
            "credibility_score": credibility_score,
            "credibility_level": "high" if credibility_score > 0.7 else "medium" if credibility_score > 0.4 else "low",
            "assessment_factors": {
                "domain_authority": "assessed",
                "content_quality": "not_available",
                "source_type": temp_source.source_type
            }
        }
    
    async def _find_relevant_sources(self, topic: str) -> List[ResearchSource]:
        """Find relevant sources from existing database"""
        return [
            source for source in self.source_database.values()
            if topic.lower() in source.content.lower() or topic.lower() in source.title.lower()
        ]
    
    def _summarize_existing_knowledge(self, sources: List[ResearchSource]) -> str:
        """Summarize existing knowledge on topic"""
        if not sources:
            return "No existing knowledge found on this topic"
        
        summary = f"Found {len(sources)} relevant sources. "
        summary += f"Average credibility: {sum(s.credibility_score for s in sources) / len(sources):.2f}. "
        summary += f"Source types: {', '.join(set(s.source_type for s in sources))}"
        
        return summary
    
    # Tool implementations
    def _search_web(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Tool: Search web with specified filters"""
        # Would implement actual web search
        return []
    
    def _analyze_document(self, document_path: str) -> Dict[str, Any]:
        """Tool: Analyze document content for key information"""
        # Would implement document analysis
        return {}
    
    def _verify_source(self, source_url: str) -> Dict[str, Any]:
        """Tool: Verify source credibility and accessibility"""
        # Would implement source verification
        return {}
    
    def _manage_citations(self, sources: List[ResearchSource]) -> List[str]:
        """Tool: Generate proper citations"""
        citations = []
        for source in sources:
            citation = f"{source.title}. Retrieved from {source.url} on {source.retrieved_at.strftime('%Y-%m-%d')}"
            citations.append(citation)
        return citations