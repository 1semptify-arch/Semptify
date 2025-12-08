"""
Mesh Handlers - Module Action Handlers for Mesh Network
========================================================

Each module registers handlers that can:
1. Respond to direct calls
2. Participate in parallel requests
3. Contribute to collaborative sessions

This is where modules "talk" to each other through the mesh.

NOTE: This bridges TWO mesh systems:
1. mesh_network.py - MeshNetwork class (for /api/mesh/modules, mesh workflows)
2. mesh_integration.py - ServiceMeshRegistry (for /api/mesh/nodes/{node}/call/{cap})
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import random

from app.core.mesh_network import (
    get_mesh_network,
    mesh_handler,
    mesh_contributor
)
from app.core.mesh_integration import service_mesh

logger = logging.getLogger(__name__)


def dual_mesh_handler(module_id: str, action: str):
    """
    Decorator that registers a handler with BOTH mesh systems:
    1. mesh_network.py (MeshNetwork) - for mesh workflows
    2. mesh_integration.py (ServiceMeshRegistry) - for node calls
    """
    def decorator(func):
        # Register with MeshNetwork
        wrapped = mesh_handler(module_id, action)(func)
        # Also register with ServiceMeshRegistry (for /api/mesh/nodes calls)
        service_mesh.register_handler(module_id, action, wrapped)
        return wrapped
    return decorator


def register_all_mesh_handlers():
    """Register all module handlers with the mesh network."""
    mesh = get_mesh_network()
    
    # =========================================================================
    # DOCUMENTS MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="documents",
        name="Document Manager",
        capabilities=["extract_data", "get_case_summary", "get_documents", "analyze"],
        provides=["document_data", "extracted_text", "document_metadata"],
        requires=[]
    )
    
    @mesh_handler("documents", "get_case_summary")
    async def documents_get_case_summary(payload: dict) -> dict:
        """Get document-based case summary."""
        return {
            "documents_count": random.randint(1, 5),
            "document_types": ["eviction_notice", "lease_agreement"],
            "key_dates_from_docs": {
                "notice_date": "2025-11-15",
                "lease_start": "2024-01-01",
                "lease_end": "2025-12-31"
            },
            "extracted_parties": {
                "landlord": "ABC Property Management",
                "tenant": payload.get("user_id", "Unknown")
            }
        }
    
    @mesh_handler("documents", "extract_data")
    async def documents_extract_data(payload: dict) -> dict:
        """Extract data from documents."""
        return {
            "extraction_status": "complete",
            "fields_extracted": 12,
            "confidence": 0.95,
            "data": {
                "rent_amount": 1200,
                "due_date": 1,
                "security_deposit": 1200,
                "landlord_address": "123 Main St"
            }
        }
    
    @mesh_handler("documents", "get_deadlines")
    async def documents_get_deadlines(payload: dict) -> dict:
        """Get deadlines from documents."""
        return {
            "document_deadlines": [
                {"source": "eviction_notice", "deadline": "2025-12-15", "type": "response_due"}
            ]
        }
    
    @mesh_contributor("documents")
    async def documents_contribute(context: dict, goal: str) -> dict:
        """Contribute document analysis to collaborative request."""
        if goal == "build_defense":
            return {
                "document_analysis": {
                    "notice_valid": True,
                    "service_proper": True,
                    "amount_accurate": False,  # Discrepancy found!
                    "discrepancy_details": "Notice claims $2400 owed, records show $1200"
                },
                "supporting_documents": ["lease.pdf", "payment_receipts.pdf"],
                "document_strengths": ["Proper notice format", "Clear lease terms"],
                "document_weaknesses": ["Amount discrepancy needs addressing"]
            }
        return {"documents_analyzed": True}
    
    # =========================================================================
    # CALENDAR MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="calendar",
        name="Calendar & Deadlines",
        capabilities=["get_deadlines", "calculate_dates", "get_case_summary", "schedule"],
        provides=["deadlines", "critical_dates", "schedule"],
        requires=["document_data"]
    )
    
    @mesh_handler("calendar", "get_case_summary")
    async def calendar_get_case_summary(payload: dict) -> dict:
        """Get calendar-based case info."""
        today = datetime.now()
        return {
            "upcoming_deadlines": [
                {
                    "name": "Answer Due",
                    "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "days_remaining": 5,
                    "priority": "critical"
                },
                {
                    "name": "Hearing Date",
                    "date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
                    "days_remaining": 14,
                    "priority": "high"
                }
            ],
            "next_critical_date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "days_until_critical": 5
        }
    
    @mesh_handler("calendar", "get_deadlines")
    async def calendar_get_deadlines(payload: dict) -> dict:
        """Get all deadlines."""
        today = datetime.now()
        return {
            "calendar_deadlines": [
                {"name": "Answer Due", "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"), "critical": True},
                {"name": "Discovery Deadline", "date": (today + timedelta(days=10)).strftime("%Y-%m-%d"), "critical": False},
                {"name": "Hearing", "date": (today + timedelta(days=14)).strftime("%Y-%m-%d"), "critical": True}
            ]
        }
    
    @mesh_handler("calendar", "calculate_dates")
    async def calendar_calculate_dates(payload: dict) -> dict:
        """Calculate important dates."""
        base_date = payload.get("base_date", datetime.now().strftime("%Y-%m-%d"))
        return {
            "calculated_dates": {
                "answer_deadline": "2025-12-09",
                "hearing_date": "2025-12-18",
                "appeal_deadline": "2025-12-28"
            }
        }
    
    @mesh_contributor("calendar")
    async def calendar_contribute(context: dict, goal: str) -> dict:
        """Contribute deadline info to collaborative request."""
        today = datetime.now()
        if goal == "build_defense":
            return {
                "critical_deadlines": {
                    "answer_due": {
                        "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                        "days_remaining": 5,
                        "action_required": "File Answer with court"
                    },
                    "hearing": {
                        "date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
                        "days_remaining": 14,
                        "action_required": "Prepare for court appearance"
                    }
                },
                "timeline_status": "urgent",
                "recommended_actions_by_date": [
                    {"by": "2025-12-06", "action": "Complete Answer form"},
                    {"by": "2025-12-08", "action": "File Answer with court"},
                    {"by": "2025-12-12", "action": "Prepare evidence"},
                    {"by": "2025-12-17", "action": "Review Zoom court procedures"}
                ]
            }
        return {"deadlines_calculated": True}
    
    # =========================================================================
    # EVICTION DEFENSE MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="eviction_defense",
        name="Eviction Defense",
        capabilities=["analyze_defenses", "get_case_summary", "get_strategy", "evaluate_case"],
        provides=["defenses", "strategy", "case_evaluation"],
        requires=["document_data", "deadlines"]
    )
    
    @mesh_handler("eviction_defense", "get_case_summary")
    async def eviction_get_case_summary(payload: dict) -> dict:
        """Get eviction-specific case summary."""
        return {
            "case_type": "nonpayment",
            "eviction_stage": "pre-hearing",
            "available_defenses": ["improper_notice", "payment_dispute", "habitability"],
            "defense_strength": "moderate",
            "recommended_strategy": "Challenge amount claimed + assert habitability issues"
        }
    
    @mesh_handler("eviction_defense", "analyze_defenses")
    async def eviction_analyze_defenses(payload: dict) -> dict:
        """Analyze available defenses."""
        return {
            "defenses": [
                {"name": "Improper Notice", "strength": "strong", "applicable": True},
                {"name": "Payment Made", "strength": "moderate", "applicable": True},
                {"name": "Habitability", "strength": "strong", "applicable": True},
                {"name": "Retaliation", "strength": "weak", "applicable": False}
            ],
            "primary_defense": "Habitability",
            "backup_defenses": ["Improper Notice", "Payment Made"]
        }
    
    @mesh_handler("eviction_defense", "get_deadlines")
    async def eviction_get_deadlines(payload: dict) -> dict:
        """Get eviction-specific deadlines."""
        return {
            "eviction_deadlines": [
                {"type": "answer", "deadline": "2025-12-09", "mandatory": True},
                {"type": "counterclaim", "deadline": "2025-12-09", "mandatory": False}
            ]
        }
    
    @mesh_contributor("eviction_defense")
    async def eviction_contribute(context: dict, goal: str) -> dict:
        """Contribute defense analysis to collaborative request."""
        if goal == "build_defense":
            # Use info from other modules in context
            doc_analysis = context.get("document_analysis", {})
            
            defenses = []
            if doc_analysis.get("amount_accurate") == False:
                defenses.append({
                    "name": "Payment Dispute",
                    "strength": "strong",
                    "basis": doc_analysis.get("discrepancy_details", "Amount discrepancy"),
                    "evidence_needed": ["Payment receipts", "Bank statements"]
                })
            
            defenses.append({
                "name": "Habitability Defense",
                "strength": "moderate",
                "basis": "Potential habitability issues",
                "evidence_needed": ["Photos", "Maintenance requests", "Inspection reports"]
            })
            
            return {
                "defense_strategy": {
                    "primary_defense": defenses[0]["name"] if defenses else "Procedural",
                    "all_defenses": defenses,
                    "recommended_approach": "Lead with payment dispute, support with habitability",
                    "success_probability": "65%"
                },
                "counterclaim_options": [
                    {"type": "Rent Abatement", "basis": "Habitability issues"},
                    {"type": "Return of Deposit", "basis": "Wrongful retention"}
                ],
                "defense_narrative": (
                    "Tenant disputes the amount claimed. Records show payments were made. "
                    "Additionally, habitability issues have been ongoing and unremedied."
                )
            }
        return {"defenses_analyzed": True}
    
    # =========================================================================
    # LAW LIBRARY MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="law_library",
        name="Law Library",
        capabilities=["get_statutes", "get_case_summary", "research", "cite"],
        provides=["statutes", "citations", "legal_research"],
        requires=["case_type"]
    )
    
    @mesh_handler("law_library", "get_case_summary")
    async def law_get_case_summary(payload: dict) -> dict:
        """Get relevant legal info for case."""
        return {
            "applicable_statutes": [
                "Minn. Stat. § 504B.285 - Eviction Procedures",
                "Minn. Stat. § 504B.161 - Habitability Requirements"
            ],
            "key_deadlines_by_law": {
                "answer_period": "7 days from service",
                "appeal_period": "10 days from judgment"
            },
            "relevant_case_law": ["Smith v. Landlord (2020)", "Tenant Rights v. Property Mgmt (2019)"]
        }
    
    @mesh_contributor("law_library")
    async def law_contribute(context: dict, goal: str) -> dict:
        """Contribute legal research to collaborative request."""
        if goal == "build_defense":
            eviction_type = context.get("eviction_type", "nonpayment")
            
            return {
                "legal_basis": {
                    "primary_statutes": [
                        {
                            "citation": "Minn. Stat. § 504B.285",
                            "title": "Eviction Actions",
                            "relevant_section": "Subd. 1 - Notice requirements",
                            "supports": "Procedural defense"
                        },
                        {
                            "citation": "Minn. Stat. § 504B.161",
                            "title": "Covenants of Habitability",
                            "relevant_section": "Landlord obligations",
                            "supports": "Habitability defense"
                        }
                    ],
                    "supporting_case_law": [
                        "Fritz v. Warthen (Minn. 1974) - Habitability implied warranty",
                        "Reiter v. Cooper (2018) - Notice defects"
                    ],
                    "tenant_rights": [
                        "Right to habitable premises",
                        "Right to proper notice",
                        "Right to cure (if applicable)",
                        "Right to assert counterclaims"
                    ]
                },
                "procedural_requirements": {
                    "notice_requirements": "14-day notice for nonpayment",
                    "service_requirements": "Personal or posted service",
                    "answer_requirements": "Written answer within 7 days"
                }
            }
        return {"legal_research_complete": True}
    
    # =========================================================================
    # FORMS MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="forms",
        name="Form Generator",
        capabilities=["generate_form", "get_deadlines", "prepare_answer"],
        provides=["forms", "court_documents"],
        requires=["case_data", "defenses"]
    )
    
    @mesh_handler("forms", "get_deadlines")
    async def forms_get_deadlines(payload: dict) -> dict:
        """Get form-related deadlines."""
        return {
            "form_deadlines": [
                {"form": "Answer", "deadline": "2025-12-09", "status": "not_started"},
                {"form": "Counterclaim", "deadline": "2025-12-09", "status": "not_started"}
            ]
        }
    
    @mesh_contributor("forms")
    async def forms_contribute(context: dict, goal: str) -> dict:
        """Contribute form preparation to collaborative request."""
        if goal == "build_defense":
            defense_strategy = context.get("defense_strategy", {})
            legal_basis = context.get("legal_basis", {})
            
            return {
                "recommended_forms": [
                    {
                        "name": "Answer to Eviction Complaint",
                        "form_number": "HOU301",
                        "priority": "critical",
                        "auto_fill_ready": True,
                        "pre_filled_fields": {
                            "defenses": defense_strategy.get("all_defenses", []),
                            "legal_citations": [s["citation"] for s in legal_basis.get("primary_statutes", [])]
                        }
                    },
                    {
                        "name": "Counterclaim",
                        "form_number": "HOU302",
                        "priority": "recommended",
                        "auto_fill_ready": True
                    },
                    {
                        "name": "Request for Continuance",
                        "form_number": "HOU303",
                        "priority": "optional",
                        "auto_fill_ready": False
                    }
                ],
                "filing_instructions": {
                    "where": "Dakota County District Court",
                    "how": "In person or e-file",
                    "fee": "$0 (fee waiver available)",
                    "copies_needed": 3
                }
            }
        return {"forms_prepared": True}
    
    # =========================================================================
    # COPILOT MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="copilot",
        name="AI Copilot",
        capabilities=["generate_guidance", "answer_question", "summarize", "explain"],
        provides=["guidance", "explanations", "summaries"],
        requires=[]
    )
    
    @mesh_handler("copilot", "answer_question")
    async def copilot_answer(payload: dict) -> dict:
        """Answer a user question."""
        question = payload.get("question", "")
        return {
            "answer": f"Based on your case data, here's what I found regarding '{question}'...",
            "confidence": 0.85,
            "sources": ["law_library", "eviction_defense"]
        }
    
    @mesh_contributor("copilot")
    async def copilot_contribute(context: dict, goal: str) -> dict:
        """Contribute AI guidance to collaborative request."""
        if goal == "build_defense":
            defense_strategy = context.get("defense_strategy", {})
            deadlines = context.get("critical_deadlines", {})
            forms = context.get("recommended_forms", [])
            
            # Build comprehensive guidance
            primary_defense = defense_strategy.get("primary_defense", "General defense")
            days_remaining = deadlines.get("answer_due", {}).get("days_remaining", 7)
            
            return {
                "ai_guidance": {
                    "summary": (
                        f"Your strongest defense is {primary_defense}. "
                        f"You have {days_remaining} days to file your Answer. "
                        "I recommend focusing on documenting the payment discrepancy."
                    ),
                    "priority_actions": [
                        "1. Complete the Answer form today",
                        "2. Gather payment receipts and bank statements",
                        "3. Document any habitability issues with photos",
                        "4. File Answer at least 1 day before deadline"
                    ],
                    "warnings": [
                        "Missing the answer deadline means automatic judgment against you",
                        "Keep copies of everything you file"
                    ],
                    "encouragement": (
                        "Your case has merit. The payment discrepancy is a strong point. "
                        "Many tenants successfully defend against eviction with similar facts."
                    )
                },
                "next_steps_plain_english": [
                    "Fill out your Answer form using the defenses we identified",
                    "Make 3 copies of everything",
                    "File at the courthouse by December 9th",
                    "Prepare your evidence for the hearing on December 18th"
                ]
            }
        return {"guidance_generated": True}
    
    # =========================================================================
    # TIMELINE MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="timeline",
        name="Timeline Engine",
        capabilities=["get_timeline", "get_case_summary", "add_event"],
        provides=["timeline", "history"],
        requires=[]
    )
    
    @mesh_handler("timeline", "get_case_summary")
    async def timeline_get_case_summary(payload: dict) -> dict:
        """Get timeline-based case summary."""
        return {
            "case_timeline": [
                {"date": "2024-01-01", "event": "Lease signed"},
                {"date": "2025-10-01", "event": "Habitability complaint filed"},
                {"date": "2025-11-15", "event": "Eviction notice received"},
                {"date": "2025-11-20", "event": "Summons served"}
            ],
            "case_duration_days": 339,
            "critical_events": 2
        }
    
    @mesh_contributor("timeline")
    async def timeline_contribute(context: dict, goal: str) -> dict:
        """Contribute timeline analysis."""
        if goal == "build_defense":
            return {
                "case_chronology": [
                    {"date": "2024-01-01", "event": "Lease executed", "relevance": "Establishes tenancy"},
                    {"date": "2025-10-01", "event": "Maintenance request submitted", "relevance": "Shows habitability issues"},
                    {"date": "2025-10-15", "event": "Follow-up request", "relevance": "Landlord on notice"},
                    {"date": "2025-11-01", "event": "Rent payment made", "relevance": "Disputes amount claimed"},
                    {"date": "2025-11-15", "event": "Eviction notice posted", "relevance": "Start of eviction"},
                    {"date": "2025-11-20", "event": "Summons served", "relevance": "Triggers answer deadline"}
                ],
                "timeline_insights": [
                    "Habitability complaints preceded eviction - possible retaliation defense",
                    "Payment made in November contradicts landlord's claim"
                ]
            }
        return {"timeline_built": True}
    
    # =========================================================================
    # ZOOM COURT MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="zoom_court",
        name="Zoom Court Helper",
        capabilities=["get_prep_guide", "check_hearing", "get_tips"],
        provides=["hearing_prep", "zoom_guide"],
        requires=["hearing_date"]
    )
    
    @mesh_contributor("zoom_court")
    async def zoom_contribute(context: dict, goal: str) -> dict:
        """Contribute hearing preparation."""
        if goal == "build_defense":
            return {
                "hearing_preparation": {
                    "format": "Zoom video hearing",
                    "preparation_checklist": [
                        "Test Zoom connection 1 day before",
                        "Find quiet, well-lit location",
                        "Have all documents organized and accessible",
                        "Dress professionally",
                        "Log in 10 minutes early"
                    ],
                    "what_to_expect": [
                        "Judge will call case by name",
                        "Landlord presents first",
                        "You present your defenses",
                        "Judge may ask questions",
                        "Decision may be same day or mailed"
                    ],
                    "tips": [
                        "Mute when not speaking",
                        "Look at camera, not screen",
                        "Speak clearly and slowly",
                        "Address judge as 'Your Honor'",
                        "Don't interrupt - wait your turn"
                    ]
                }
            }
        return {"hearing_prep_ready": True}

    # =========================================================================
    # COURT LEARNING MODULE - Bidirectional Learning from Court Outcomes
    # =========================================================================

    mesh.register_module(
        module_id="court_learning",
        name="Court Learning Engine",
        capabilities=[
            "get_defense_rates", "get_judge_patterns", "get_landlord_patterns",
            "get_learning_stats", "recommend_strategy", "record_outcome",
            "seed_data", "get_case_summary"
        ],
        provides=["defense_success_rates", "judge_patterns", "landlord_patterns", "strategy_recommendation"],
        requires=["case_data", "outcome_data"]
    )

    @dual_mesh_handler("court_learning", "get_defense_rates")
    async def court_learning_get_defense_rates(payload: dict) -> dict:
        """Get defense success rates from learning engine."""
        try:
            from app.services.eviction.court_learning import get_learning_engine
            engine = await get_learning_engine()
            rates = await engine.get_defense_success_rates(
                county=payload.get("county", "Dakota"),
                min_cases=payload.get("min_cases", 3)
            )
            return {
                "defense_rates": [
                    {
                        "code": r.defense_code,
                        "name": r.defense_name,
                        "win_rate": r.win_rate,
                        "total_uses": r.total_uses,
                        "confidence": r.confidence
                    }
                    for r in rates
                ]
            }
        except Exception as e:
            logger.error(f"Court learning get_defense_rates error: {e}")
            return {"error": str(e), "defense_rates": []}

    @dual_mesh_handler("court_learning", "get_judge_patterns")
    async def court_learning_get_judge_patterns(payload: dict) -> dict:
        """Get judge patterns from learning engine."""
        try:
            from app.services.eviction.court_learning import get_learning_engine
            engine = await get_learning_engine()
            patterns = await engine.get_judge_patterns(
                county=payload.get("county", "Dakota")
            )
            return {
                "judge_patterns": [
                    {
                        "name": p.judge_name,
                        "tenant_win_rate": p.tenant_win_rate,
                        "total_cases": p.total_cases,
                        "favored_defenses": p.favored_defenses,
                        "motion_grant_rate": p.motion_grant_rate
                    }
                    for p in patterns
                ]
            }
        except Exception as e:
            logger.error(f"Court learning get_judge_patterns error: {e}")
            return {"error": str(e), "judge_patterns": []}

    @dual_mesh_handler("court_learning", "get_learning_stats")
    async def court_learning_get_stats(payload: dict) -> dict:
        """Get overall learning statistics."""
        try:
            from app.services.eviction.court_learning import get_learning_engine
            engine = await get_learning_engine()
            stats = await engine.get_learning_stats()
            return {
                "total_cases": stats.get("total_cases_recorded", 0),
                "total_defenses": stats.get("total_defense_outcomes", 0),
                "counties": stats.get("counties_covered", []),
                "learning_active": True
            }
        except Exception as e:
            logger.error(f"Court learning get_stats error: {e}")
            return {"error": str(e), "total_cases": 0, "learning_active": False}

    @dual_mesh_handler("court_learning", "recommend_strategy")
    async def court_learning_recommend_strategy(payload: dict) -> dict:
        """Get strategy recommendation based on case characteristics."""
        try:
            from app.services.eviction.court_learning import get_learning_engine
            engine = await get_learning_engine()
            recommendation = await engine.get_recommended_strategy(
                notice_type=payload.get("notice_type", ""),
                amount_claimed_cents=payload.get("amount_claimed_cents", 0),
                available_defenses=payload.get("available_defenses", []),
                judge_name=payload.get("judge_name"),
                landlord_name=payload.get("landlord_name")
            )
            return {"recommendation": recommendation}
        except Exception as e:
            logger.error(f"Court learning recommend_strategy error: {e}")
            return {"error": str(e), "recommendation": None}

    @dual_mesh_handler("court_learning", "get_case_summary")
    async def court_learning_get_case_summary(payload: dict) -> dict:
        """Get court learning insights for case summary."""
        try:
            from app.services.eviction.court_learning import get_learning_engine
            engine = await get_learning_engine()
            
            # Get top defenses
            rates = await engine.get_defense_success_rates(county="Dakota", min_cases=3)
            top_defenses = [
                {"code": r.defense_code, "win_rate": r.win_rate}
                for r in rates[:5]
            ] if rates else []
            
            stats = await engine.get_learning_stats()
            
            return {
                "learning_insights": {
                    "top_defenses": top_defenses,
                    "total_cases_learned": stats.get("total_cases_recorded", 0),
                    "data_driven": stats.get("total_cases_recorded", 0) > 0
                }
            }
        except Exception as e:
            logger.error(f"Court learning get_case_summary error: {e}")
            return {"learning_insights": {"top_defenses": [], "total_cases_learned": 0, "data_driven": False}}

    @mesh_contributor("court_learning")
    async def court_learning_contribute(context: dict, goal: str) -> dict:
        """Contribute court learning data to collaborative requests."""
        if goal == "build_defense":
            try:
                from app.services.eviction.court_learning import get_learning_engine
                engine = await get_learning_engine()
                
                rates = await engine.get_defense_success_rates(county="Dakota", min_cases=3)
                top_defenses = rates[:5] if rates else []
                
                judge_name = context.get("judge_name")
                judge_insight = None
                if judge_name:
                    patterns = await engine.get_judge_patterns(county="Dakota")
                    judge_data = next((p for p in patterns if p.judge_name == judge_name), None)
                    if judge_data:
                        judge_insight = {
                            "name": judge_data.judge_name,
                            "tenant_win_rate": judge_data.tenant_win_rate,
                            "favored_defenses": judge_data.favored_defenses
                        }
                
                return {
                    "court_learning_analysis": {
                        "recommended_defenses": [
                            {
                                "code": r.defense_code,
                                "name": r.defense_name,
                                "success_rate": r.win_rate,
                                "confidence": r.confidence
                            }
                            for r in top_defenses
                        ],
                        "judge_insights": judge_insight,
                        "data_based": True,
                        "cases_analyzed": len(engine._case_outcomes) if hasattr(engine, '_case_outcomes') else 0
                    }
                }
            except Exception as e:
                logger.error(f"Court learning contribute error: {e}")
                return {"court_learning_analysis": {"error": str(e), "data_based": False}}
        return {"court_learning_data": True}

    # =========================================================================
    # CONTEXT MODULE
    # =========================================================================

    mesh.register_module(
        module_id="context",
        name="Context Engine",
        capabilities=["get_context", "update_context", "get_case_summary"],
        provides=["user_context", "case_context"],
        requires=[]
    )
    
    @mesh_handler("context", "get_case_summary")
    async def context_get_case_summary(payload: dict) -> dict:
        """Get context-based summary."""
        return {
            "user_context": {
                "experience_level": "first_time",
                "stress_level": "high",
                "preferred_communication": "simple_language"
            },
            "case_context": {
                "urgency": "high",
                "complexity": "moderate",
                "self_represented": True
            }
        }
    
    # =========================================================================
    # UI MODULE
    # =========================================================================
    
    mesh.register_module(
        module_id="ui",
        name="Adaptive UI",
        capabilities=["update_display", "show_alert", "get_dashboard"],
        provides=["ui_state", "display_data"],
        requires=[]
    )
    
    @mesh_contributor("ui")
    async def ui_contribute(context: dict, goal: str) -> dict:
        """Contribute UI recommendations."""
        if goal == "build_defense":
            return {
                "ui_recommendations": {
                    "priority_panel": {
                        "show": True,
                        "content": "Answer due in 5 days",
                        "color": "red",
                        "action_button": "Start Answer Form"
                    },
                    "progress_tracker": {
                        "total_steps": 5,
                        "completed_steps": 1,
                        "current_step": "Prepare Defense"
                    },
                    "quick_actions": [
                        {"label": "Fill Answer Form", "priority": "high"},
                        {"label": "View Deadlines", "priority": "medium"},
                        {"label": "Get Help", "priority": "low"}
                    ]
                }
            }
        return {"ui_updated": True}

    # =========================================================================
    # LEGAL TRAILS MODULE
    # =========================================================================
    mesh.register_module(
        module_id="legal_trails",
        name="Legal Trails",
        capabilities=[
            "log_violation", "log_eviction_threat", "log_late_fee",
            "track_broker", "create_claim", "calculate_deadlines",
            "generate_complaint", "find_attorney"
        ],
        provides=["violations", "claims", "deadlines", "attorneys", "complaints"],
        requires=["case_data", "violation_data"]
    )

    @dual_mesh_handler("legal_trails", "log_violation")
    async def legal_trails_log_violation(payload: dict) -> dict:
        """Log a violation through the mesh."""
        try:
            from app.routers.legal_trails import violations_db, Violation
            import uuid
            from datetime import datetime
            
            violation_id = str(uuid.uuid4())[:8]
            violation_data = {
                "id": violation_id,
                "violation_type": payload.get("violation_type"),
                "date_occurred": payload.get("date_occurred"),
                "description": payload.get("description"),
                "perpetrator": payload.get("perpetrator"),
                "perpetrator_role": payload.get("perpetrator_role"),
                "company": payload.get("company"),
                "amount_if_financial": payload.get("amount_if_financial"),
                "statutes_violated": payload.get("statutes_violated", []),
                "evidence_ids": payload.get("evidence_ids", []),
                "witnesses": payload.get("witnesses", []),
                "created_at": datetime.now().isoformat()
            }
            violations_db[violation_id] = violation_data
            return {"success": True, "violation_id": violation_id}
        except Exception as e:
            return {"error": str(e)}

    @dual_mesh_handler("legal_trails", "calculate_deadlines")
    async def legal_trails_calculate_deadlines(payload: dict) -> dict:
        """Calculate filing deadlines through the mesh."""
        try:
            from datetime import date, timedelta
            violation_date_str = payload.get("violation_date")
            if not violation_date_str:
                return {"error": "violation_date required"}
            
            violation_date = date.fromisoformat(violation_date_str)
            today = date.today()
            
            STATUTE_OF_LIMITATIONS = {
                "civil_retaliation": 6,
                "civil_fraud": 6,
                "hud_complaint": 1,
                "criminal_theft": 5,
                "license_complaint": 2,
            }
            
            windows = []
            for claim_type, years in STATUTE_OF_LIMITATIONS.items():
                deadline = violation_date + timedelta(days=years * 365)
                days_remaining = (deadline - today).days
                urgency = "expired" if days_remaining < 0 else "critical" if days_remaining < 90 else "warning" if days_remaining < 365 else "safe"
                windows.append({
                    "claim_type": claim_type,
                    "deadline": deadline.isoformat(),
                    "days_remaining": max(0, days_remaining),
                    "urgency": urgency
                })
            return {"windows": windows}
        except Exception as e:
            return {"error": str(e)}

    @dual_mesh_handler("legal_trails", "find_attorney")
    async def legal_trails_find_attorney(payload: dict) -> dict:
        """Get attorney recommendations through the mesh."""
        return {
            "attorneys": [
                {"name": "Madia Law LLC", "specialty": "Fraud, tenant justice", "website": "https://madialaw.com"},
                {"name": "Burns & Hansen, P.A.", "specialty": "Real estate litigation", "website": "https://patrickburnslaw.com"},
                {"name": "HOME Line", "specialty": "Free tenant hotline", "phone": "612-728-5767"},
                {"name": "Legal Aid - Housing", "specialty": "Free legal services", "phone": "612-334-5970"}
            ]
        }

    @mesh_contributor("legal_trails")
    async def legal_trails_contribute(context: dict, goal: str) -> dict:
        """Contribute legal trails data to collaborative workflows."""
        if goal == "build_defense":
            from app.routers.legal_trails import violations_db, eviction_threats_db, late_fees_db
            return {
                "legal_trails": {
                    "violations_count": len(violations_db),
                    "threats_count": len(eviction_threats_db),
                    "late_fees_count": len(late_fees_db),
                    "statutes": ["MN 504B.177", "MN 504B.285", "MN 504B.161"],
                    "filing_windows": {
                        "civil": "6 years",
                        "hud": "1 year",
                        "license": "2 years"
                    }
                }
            }
        return {"legal_trails_ready": True}

    logger.info("✅ All mesh handlers registered")    # Return stats
    mesh_status = mesh.get_status()
    return {
        "modules_registered": mesh_status["modules_connected"],
        "total_handlers": mesh_status["total_handlers"]
    }
