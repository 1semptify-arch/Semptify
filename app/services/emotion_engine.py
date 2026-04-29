"""
Semptify Adaptive Emotion Engine
================================
Multi-dimensional emotional state tracking that mimics human psychology.
Drives adaptive UI, content presentation, and system behavior.

The 7 Emotional Dimensions:
1. INTENSITY - How urgent/critical the situation feels (panic → calm)
2. CLARITY - How well user understands their situation (confused → clear)
3. CONFIDENCE - User's belief they can win (hopeless → empowered)
4. MOMENTUM - Progress feeling (stuck → moving forward)
5. OVERWHELM - Cognitive load (drowning → manageable)
6. TRUST - Trust in the system (skeptical → relying on it)
7. RESOLVE - Fighting spirit (giving up → determined)

Each dimension influences:
- What content to show
- How much to show at once
- Tone of messaging
- UI complexity
- Suggested actions
- Pacing of guidance
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import math

logger = logging.getLogger(__name__)


class EmotionalTrigger(Enum):
    """Events that shift emotional state"""
    # Positive triggers
    TASK_COMPLETED = "task_completed"
    EVIDENCE_UPLOADED = "evidence_uploaded"
    VIOLATION_FOUND = "violation_found"
    DEADLINE_MET = "deadline_met"
    DOCUMENT_ORGANIZED = "document_organized"
    HELP_ACCESSED = "help_accessed"
    WIN_MILESTONE = "win_milestone"
    SUPPORT_CONNECTED = "support_connected"
    
    # Negative triggers
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_MISSED = "deadline_missed"
    CONFUSION_DETECTED = "confusion_detected"
    RAPID_PAGE_SWITCHING = "rapid_page_switching"
    LONG_INACTIVITY = "long_inactivity"
    ERROR_ENCOUNTERED = "error_encountered"
    COURT_DATE_NEAR = "court_date_near"
    REPEATED_HELP_CLICKS = "repeated_help_clicks"
    ABANDONED_TASK = "abandoned_task"
    
    # Neutral/Informational
    SESSION_START = "session_start"
    FEATURE_EXPLORED = "feature_explored"
    DOCUMENT_VIEWED = "document_viewed"


@dataclass
class EmotionalState:
    """The 7-dimensional emotional state of a user"""
    
    # Scale: 0.0 (negative extreme) to 1.0 (positive extreme)
    # 0.5 = neutral
    
    intensity: float = 0.5      # 0=panic, 0.5=alert, 1=calm
    clarity: float = 0.5        # 0=confused, 0.5=understanding, 1=crystal clear
    confidence: float = 0.5     # 0=hopeless, 0.5=uncertain, 1=empowered
    momentum: float = 0.5       # 0=stuck, 0.5=steady, 1=rolling
    overwhelm: float = 0.5      # 0=drowning, 0.5=managing, 1=in control (inverted scale)
    trust: float = 0.5          # 0=skeptical, 0.5=neutral, 1=relying
    resolve: float = 0.5        # 0=giving up, 0.5=uncertain, 1=determined
    
    # Derived composite scores
    @property
    def crisis_level(self) -> float:
        """Overall crisis indicator (0=stable, 1=crisis)"""
        return 1.0 - (
            (self.intensity * 0.3) +
            (self.clarity * 0.15) +
            (self.confidence * 0.2) +
            (self.overwhelm * 0.2) +
            (self.resolve * 0.15)
        )
    
    @property
    def readiness_score(self) -> float:
        """Ready to take action (0=not ready, 1=ready)"""
        return (
            (self.clarity * 0.25) +
            (self.confidence * 0.25) +
            (self.momentum * 0.2) +
            (self.overwhelm * 0.15) +
            (self.resolve * 0.15)
        )
    
    @property
    def engagement_health(self) -> float:
        """Overall engagement health (0=disengaging, 1=engaged)"""
        return (
            (self.trust * 0.3) +
            (self.momentum * 0.25) +
            (self.confidence * 0.25) +
            (self.resolve * 0.2)
        )
    
    @property
    def cognitive_capacity(self) -> float:
        """How much info can user absorb (0=minimal, 1=full)"""
        return (
            (self.overwhelm * 0.4) +
            (self.clarity * 0.3) +
            (self.intensity * 0.3)
        )
    
    @property
    def dominant_emotion(self) -> str:
        """The strongest emotional factor right now"""
        emotions = {
            'panicked': 1.0 - self.intensity,
            'confused': 1.0 - self.clarity,
            'hopeless': 1.0 - self.confidence,
            'stuck': 1.0 - self.momentum,
            'overwhelmed': 1.0 - self.overwhelm,
            'skeptical': 1.0 - self.trust,
            'defeated': 1.0 - self.resolve,
            'calm': self.intensity,
            'clear': self.clarity,
            'confident': self.confidence,
            'progressing': self.momentum,
            'in_control': self.overwhelm,
            'trusting': self.trust,
            'determined': self.resolve
        }
        return max(emotions, key=emotions.get)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dimensions': {
                'intensity': round(self.intensity, 3),
                'clarity': round(self.clarity, 3),
                'confidence': round(self.confidence, 3),
                'momentum': round(self.momentum, 3),
                'overwhelm': round(self.overwhelm, 3),
                'trust': round(self.trust, 3),
                'resolve': round(self.resolve, 3)
            },
            'composites': {
                'crisis_level': round(self.crisis_level, 3),
                'readiness_score': round(self.readiness_score, 3),
                'engagement_health': round(self.engagement_health, 3),
                'cognitive_capacity': round(self.cognitive_capacity, 3)
            },
            'dominant_emotion': self.dominant_emotion
        }


@dataclass
class UIAdaptation:
    """How the UI should adapt based on emotional state"""
    
    # Content density
    max_items_shown: int = 5            # How many items to show at once
    information_depth: str = "moderate"  # minimal, moderate, detailed
    
    # Visual presentation
    color_warmth: str = "neutral"       # cool, neutral, warm (calming colors when stressed)
    animation_level: str = "normal"     # reduced, normal, engaging
    contrast_level: str = "normal"      # high (for clarity), normal, soft
    
    # Interaction style
    guidance_level: str = "moderate"    # minimal, moderate, hand-holding
    confirmation_prompts: bool = False  # Extra "are you sure?" for overwhelmed users
    auto_save_frequency: str = "normal" # frequent (for anxious users), normal
    
    # Content tone
    message_tone: str = "supportive"    # urgent, direct, supportive, encouraging, celebratory
    encouragement_level: str = "moderate"  # none, light, moderate, heavy
    
    # Navigation
    breadcrumb_detail: str = "normal"   # minimal, normal, detailed
    back_button_prominent: bool = False # Larger back button for confused users
    progress_visibility: str = "normal" # hidden, normal, prominent
    
    # Actions
    primary_action_size: str = "normal" # small, normal, large, huge
    action_limit: int = 3               # Max actions shown at once
    suggested_action: Optional[str] = None  # What we think they should do
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmotionEngine:
    """
    The Adaptive Emotion Engine
    
    Tracks user emotional state across 7 dimensions and adapts
    the entire UI/UX experience accordingly.
    """
    
    # How much each trigger affects each dimension
    TRIGGER_EFFECTS: Dict[EmotionalTrigger, Dict[str, float]] = {
        # Positive triggers boost relevant dimensions
        EmotionalTrigger.TASK_COMPLETED: {
            'momentum': 0.15, 'confidence': 0.1, 'overwhelm': 0.08, 'resolve': 0.05
        },
        EmotionalTrigger.EVIDENCE_UPLOADED: {
            'momentum': 0.1, 'confidence': 0.12, 'clarity': 0.05, 'resolve': 0.08
        },
        EmotionalTrigger.VIOLATION_FOUND: {
            'confidence': 0.2, 'resolve': 0.15, 'clarity': 0.1, 'momentum': 0.1
        },
        EmotionalTrigger.DEADLINE_MET: {
            'confidence': 0.15, 'intensity': 0.2, 'overwhelm': 0.15, 'momentum': 0.1
        },
        EmotionalTrigger.DOCUMENT_ORGANIZED: {
            'clarity': 0.1, 'overwhelm': 0.12, 'momentum': 0.08
        },
        EmotionalTrigger.HELP_ACCESSED: {
            'clarity': 0.08, 'trust': 0.1, 'overwhelm': 0.05
        },
        EmotionalTrigger.WIN_MILESTONE: {
            'confidence': 0.25, 'resolve': 0.2, 'momentum': 0.2, 'intensity': 0.15, 'trust': 0.15
        },
        EmotionalTrigger.SUPPORT_CONNECTED: {
            'trust': 0.2, 'confidence': 0.1, 'resolve': 0.15, 'intensity': 0.1
        },
        
        # Negative triggers decrease relevant dimensions
        EmotionalTrigger.DEADLINE_APPROACHING: {
            'intensity': -0.2, 'overwhelm': -0.15, 'resolve': 0.05  # Slight resolve boost
        },
        EmotionalTrigger.DEADLINE_MISSED: {
            'confidence': -0.25, 'intensity': -0.3, 'resolve': -0.15, 'momentum': -0.2
        },
        EmotionalTrigger.CONFUSION_DETECTED: {
            'clarity': -0.15, 'confidence': -0.1, 'overwhelm': -0.1
        },
        EmotionalTrigger.RAPID_PAGE_SWITCHING: {
            'clarity': -0.12, 'overwhelm': -0.15, 'momentum': -0.08
        },
        EmotionalTrigger.LONG_INACTIVITY: {
            'momentum': -0.2, 'resolve': -0.15, 'trust': -0.1
        },
        EmotionalTrigger.ERROR_ENCOUNTERED: {
            'trust': -0.15, 'confidence': -0.1, 'overwhelm': -0.1
        },
        EmotionalTrigger.COURT_DATE_NEAR: {
            'intensity': -0.25, 'overwhelm': -0.2, 'resolve': 0.1  # Boost resolve (fight response)
        },
        EmotionalTrigger.REPEATED_HELP_CLICKS: {
            'clarity': -0.2, 'confidence': -0.1, 'trust': 0.05
        },
        EmotionalTrigger.ABANDONED_TASK: {
            'momentum': -0.15, 'resolve': -0.1, 'confidence': -0.08
        },
        
        # Neutral triggers - minor effects
        EmotionalTrigger.SESSION_START: {
            'momentum': 0.05, 'trust': 0.02
        },
        EmotionalTrigger.FEATURE_EXPLORED: {
            'clarity': 0.05, 'trust': 0.03
        },
        EmotionalTrigger.DOCUMENT_VIEWED: {
            'clarity': 0.03, 'momentum': 0.02
        },
    }
    
    def __init__(self):
        self.user_states: Dict[str, EmotionalState] = {}
        self.user_history: Dict[str, List[Dict]] = {}
        self.decay_rate = 0.02  # How fast emotions return to baseline per hour
        
    def get_state(self, user_id: str) -> EmotionalState:
        """Get current emotional state for user"""
        if user_id not in self.user_states:
            self.user_states[user_id] = EmotionalState()
        return self.user_states[user_id]
    
    def process_trigger(
        self, 
        user_id: str, 
        trigger: EmotionalTrigger,
        context: Optional[Dict[str, Any]] = None
    ) -> EmotionalState:
        """
        Process an emotional trigger and update state.
        
        Args:
            user_id: User identifier
            trigger: The trigger event
            context: Additional context (e.g., days_until_deadline)
        """
        state = self.get_state(user_id)
        effects = self.TRIGGER_EFFECTS.get(trigger, {})
        context = context or {}
        
        # Apply context multipliers
        multiplier = 1.0
        
        # Deadline proximity intensifies effects
        if 'days_until_deadline' in context:
            days = context['days_until_deadline']
            if days <= 1:
                multiplier = 2.0
            elif days <= 3:
                multiplier = 1.5
            elif days <= 7:
                multiplier = 1.2
        
        # Court date proximity
        if 'days_until_court' in context:
            days = context['days_until_court']
            if days <= 1:
                multiplier = max(multiplier, 2.5)
            elif days <= 3:
                multiplier = max(multiplier, 1.8)
            elif days <= 7:
                multiplier = max(multiplier, 1.4)
        
        # Apply effects to each dimension
        for dimension, delta in effects.items():
            current = getattr(state, dimension)
            adjusted_delta = delta * multiplier
            
            # Apply with diminishing returns near extremes
            if adjusted_delta > 0:
                # Harder to increase as you get higher
                effective_delta = adjusted_delta * (1.0 - current * 0.5)
            else:
                # Harder to decrease as you get lower
                effective_delta = adjusted_delta * (current * 0.5 + 0.5)
            
            new_value = max(0.0, min(1.0, current + effective_delta))
            setattr(state, dimension, new_value)
        
        # Record in history
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        self.user_history[user_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'trigger': trigger.value,
            'context': context,
            'state_after': state.to_dict()
        })
        
        # Keep last 100 events
        self.user_history[user_id] = self.user_history[user_id][-100:]
        
        logger.info(f"Emotion trigger {trigger.value} for user {user_id}: "
                   f"dominant={state.dominant_emotion}, crisis={state.crisis_level:.2f}")
        
        return state
    
    def apply_time_decay(self, user_id: str, hours_elapsed: float) -> EmotionalState:
        """
        Apply time-based decay toward baseline (0.5).
        Emotions naturally stabilize over time.
        """
        state = self.get_state(user_id)
        decay = self.decay_rate * hours_elapsed
        
        for dim in ['intensity', 'clarity', 'confidence', 'momentum', 
                    'overwhelm', 'trust', 'resolve']:
            current = getattr(state, dim)
            # Move toward 0.5 baseline
            if current > 0.5:
                new_val = max(0.5, current - decay)
            else:
                new_val = min(0.5, current + decay)
            setattr(state, dim, new_val)
        
        return state
    
    def calculate_ui_adaptation(self, user_id: str) -> UIAdaptation:
        """
        Calculate how UI should adapt based on emotional state.
        This is the bridge between emotion and interface.
        """
        state = self.get_state(user_id)
        adaptation = UIAdaptation()
        
        # === CRISIS MODE ===
        if state.crisis_level > 0.7:
            adaptation.max_items_shown = 1
            adaptation.information_depth = "minimal"
            adaptation.guidance_level = "hand-holding"
            adaptation.message_tone = "supportive"
            adaptation.encouragement_level = "heavy"
            adaptation.primary_action_size = "huge"
            adaptation.action_limit = 1
            adaptation.color_warmth = "warm"
            adaptation.animation_level = "reduced"
            adaptation.suggested_action = "Take one breath. Here's your ONE task."
        
        # === HIGH STRESS ===
        elif state.crisis_level > 0.5:
            adaptation.max_items_shown = 3
            adaptation.information_depth = "minimal"
            adaptation.guidance_level = "moderate"
            adaptation.message_tone = "supportive"
            adaptation.encouragement_level = "moderate"
            adaptation.primary_action_size = "large"
            adaptation.action_limit = 2
            adaptation.color_warmth = "warm"
        
        # === CONFUSED STATE ===
        if state.clarity < 0.3:
            adaptation.breadcrumb_detail = "detailed"
            adaptation.back_button_prominent = True
            adaptation.guidance_level = "hand-holding"
            adaptation.information_depth = "minimal"
            adaptation.contrast_level = "high"
            
        # === LOW CONFIDENCE ===
        if state.confidence < 0.3:
            adaptation.encouragement_level = "heavy"
            adaptation.message_tone = "encouraging"
            adaptation.progress_visibility = "prominent"
            # Show past wins
            adaptation.suggested_action = "Remember: You've already made progress!"
        
        # === OVERWHELMED ===
        if state.overwhelm < 0.3:
            adaptation.max_items_shown = min(adaptation.max_items_shown, 2)
            adaptation.confirmation_prompts = True
            adaptation.auto_save_frequency = "frequent"
            adaptation.action_limit = 1
            adaptation.animation_level = "reduced"
        
        # === LOSING RESOLVE ===
        if state.resolve < 0.3:
            adaptation.message_tone = "encouraging"
            adaptation.encouragement_level = "heavy"
            adaptation.suggested_action = "Your fight matters. Every step counts."
        
        # === LOW TRUST ===
        if state.trust < 0.3:
            adaptation.information_depth = "detailed"  # Show more to build trust
            adaptation.guidance_level = "minimal"  # Let them explore
        
        # === MOMENTUM STALLED ===
        if state.momentum < 0.3:
            adaptation.progress_visibility = "prominent"
            adaptation.primary_action_size = "large"
            adaptation.suggested_action = "Pick up where you left off"
        
        # === POSITIVE STATES ===
        
        # High readiness - show more options
        if state.readiness_score > 0.7:
            adaptation.max_items_shown = 7
            adaptation.action_limit = 5
            adaptation.information_depth = "detailed"
            adaptation.guidance_level = "minimal"
        
        # High cognitive capacity - can handle complexity
        if state.cognitive_capacity > 0.7:
            adaptation.max_items_shown = 10
            adaptation.information_depth = "detailed"
            adaptation.animation_level = "engaging"
        
        # Rolling with momentum
        if state.momentum > 0.7:
            adaptation.message_tone = "direct"
            adaptation.encouragement_level = "light"
            adaptation.suggested_action = "You're on a roll. Keep going!"
        
        # Highly determined
        if state.resolve > 0.8:
            adaptation.message_tone = "direct"
            adaptation.primary_action_size = "normal"
            adaptation.action_limit = 5
        
        return adaptation
    
    def get_personalized_message(self, user_id: str, context: str = "general") -> Dict[str, str]:
        """
        Get emotionally-appropriate messaging for the user.
        """
        state = self.get_state(user_id)
        
        messages = {
            'greeting': '',
            'encouragement': '',
            'action_prompt': '',
            'help_offer': ''
        }
        
        # === GREETINGS ===
        if state.crisis_level > 0.7:
            messages['greeting'] = "I'm here with you. Let's take this one step at a time."
        elif state.crisis_level > 0.5:
            messages['greeting'] = "You've got this. Let's focus on what matters most today."
        elif state.momentum > 0.7:
            messages['greeting'] = "Great momentum! Ready to keep building your case?"
        elif state.confidence > 0.7:
            messages['greeting'] = "Welcome back, warrior. Your case is getting stronger."
        else:
            messages['greeting'] = "Welcome back. Here's where you left off."
        
        # === ENCOURAGEMENT ===
        if state.confidence < 0.3:
            messages['encouragement'] = "Every piece of evidence you gather strengthens your position. You're building something real."
        elif state.resolve < 0.3:
            messages['encouragement'] = "The fact that you're here means you haven't given up. That takes courage."
        elif state.overwhelm < 0.3:
            messages['encouragement'] = "It's okay to feel overwhelmed. We'll break this down into tiny, manageable pieces."
        elif state.momentum < 0.3:
            messages['encouragement'] = "Starting again is the hardest part. One small action can restart your momentum."
        elif state.momentum > 0.7:
            messages['encouragement'] = "You're making real progress. Keep this energy going!"
        else:
            messages['encouragement'] = "You're doing the work. That matters."
        
        # === ACTION PROMPTS ===
        if state.crisis_level > 0.7:
            messages['action_prompt'] = "Just do this one thing:"
        elif state.overwhelm < 0.3:
            messages['action_prompt'] = "When you're ready, here's a small next step:"
        elif state.readiness_score > 0.7:
            messages['action_prompt'] = "Ready for action? Here's what's next:"
        else:
            messages['action_prompt'] = "Your next step:"
        
        # === HELP OFFERS ===
        if state.clarity < 0.3:
            messages['help_offer'] = "Confused? That's completely normal. Let me explain this differently."
        elif state.trust < 0.3:
            messages['help_offer'] = "Want to understand how this works? I'll show you everything."
        else:
            messages['help_offer'] = "Need help? I'm here."
        
        return messages
    
    def get_suggested_next_action(
        self, 
        user_id: str, 
        available_actions: List[Dict[str, Any]],
        case_context: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Based on emotional state and case context, suggest the best next action.
        """
        state = self.get_state(user_id)
        case_context = case_context or {}
        
        # Score each action based on emotional fit
        scored_actions = []
        
        for action in available_actions:
            score = 0.5  # Base score
            
            difficulty = action.get('difficulty', 'medium')
            action_type = action.get('type', 'general')
            urgency = action.get('urgency', 'normal')
            
            # Difficulty matching
            if state.overwhelm < 0.3 or state.confidence < 0.3:
                # User is struggling - prefer easy actions
                if difficulty == 'easy':
                    score += 0.3
                elif difficulty == 'hard':
                    score -= 0.4
            elif state.readiness_score > 0.7:
                # User is ready - can handle harder tasks
                if difficulty == 'hard':
                    score += 0.1
            
            # Urgency matching
            if urgency == 'urgent' and state.intensity > 0.3:
                # Calm enough to handle urgent tasks
                score += 0.2
            elif urgency == 'urgent' and state.intensity < 0.3:
                # Too panicked - might overwhelm
                score -= 0.1
            
            # Quick wins when momentum is low
            if state.momentum < 0.4 and action.get('quick_win', False):
                score += 0.3
            
            # Evidence gathering when confidence is low
            if state.confidence < 0.4 and action_type == 'evidence':
                score += 0.2  # Building evidence builds confidence
            
            # Organization when clarity is low
            if state.clarity < 0.4 and action_type == 'organize':
                score += 0.25
            
            # Deadline-based urgency
            if 'deadline_days' in action:
                days = action['deadline_days']
                if days <= 1:
                    score += 0.5
                elif days <= 3:
                    score += 0.3
                elif days <= 7:
                    score += 0.15
            
            scored_actions.append((score, action))
        
        # Sort by score and return best
        scored_actions.sort(key=lambda x: x[0], reverse=True)
        
        if scored_actions:
            return scored_actions[0][1]
        return None
    
    def get_dashboard_config(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete dashboard configuration based on emotional state.
        This drives the adaptive UI.
        """
        state = self.get_state(user_id)
        adaptation = self.calculate_ui_adaptation(user_id)
        messages = self.get_personalized_message(user_id)
        
        return {
            'emotional_state': state.to_dict(),
            'ui_adaptation': adaptation.to_dict(),
            'messages': messages,
            'dashboard_mode': self._determine_dashboard_mode(state),
            'visible_sections': self._determine_visible_sections(state, adaptation),
            'color_scheme': self._determine_color_scheme(state),
            'animation_config': self._determine_animations(adaptation),
        }
    
    def _determine_dashboard_mode(self, state: EmotionalState) -> str:
        """Determine which dashboard mode to show"""
        if state.crisis_level > 0.7:
            return "crisis"  # Single focus, hand-holding
        elif state.crisis_level > 0.5:
            return "focused"  # Limited options, supportive
        elif state.readiness_score > 0.7:
            return "power"  # Full features, let them work
        elif state.momentum > 0.7:
            return "flow"  # Streamlined, keep momentum
        else:
            return "guided"  # Default balanced experience
    
    def _determine_visible_sections(
        self, 
        state: EmotionalState, 
        adaptation: UIAdaptation
    ) -> List[str]:
        """Determine which dashboard sections to show"""
        sections = []
        
        # Always show mission/progress in some form
        sections.append('mission_status')
        
        # Crisis mode - minimal sections
        if state.crisis_level > 0.7:
            sections.append('single_action')
            sections.append('help_line')
            return sections
        
        # Add based on capacity
        if state.cognitive_capacity > 0.4:
            sections.append('today_tasks')
        
        if state.cognitive_capacity > 0.5:
            sections.append('timeline')
            sections.append('evidence_summary')
        
        if state.cognitive_capacity > 0.6:
            sections.append('upcoming_deadlines')
            sections.append('quick_actions')
        
        if state.cognitive_capacity > 0.7:
            sections.append('case_strength')
            sections.append('document_hub')
            sections.append('tools')
        
        if state.readiness_score > 0.8:
            sections.append('advanced_tools')
            sections.append('research')
        
        return sections
    
    def _determine_color_scheme(self, state: EmotionalState) -> Dict[str, str]:
        """Determine color scheme based on emotional state"""
        
        if state.crisis_level > 0.7:
            # Warm, calming colors
            return {
                'primary': '#5B8C5A',      # Sage green - calming
                'secondary': '#8B7355',     # Warm brown
                'accent': '#D4A574',        # Soft gold
                'background': '#FAF7F2',    # Warm white
                'text': '#3D3D3D',
                'success': '#5B8C5A',
                'warning': '#C9A227',       # Soft gold, not alarming
                'danger': '#B87333'         # Copper, not red
            }
        elif state.crisis_level > 0.5:
            # Balanced, supportive colors
            return {
                'primary': '#4A7C59',
                'secondary': '#6B8E8E',
                'accent': '#D4A574',
                'background': '#F8F9FA',
                'text': '#2D3436',
                'success': '#27AE60',
                'warning': '#F39C12',
                'danger': '#D35400'
            }
        elif state.momentum > 0.7:
            # Energetic, momentum colors
            return {
                'primary': '#2C5F2D',       # Forest green - growth
                'secondary': '#2874A6',     # Blue - moving forward
                'accent': '#F4D03F',        # Bright gold - winning
                'background': '#FFFFFF',
                'text': '#1A1A1A',
                'success': '#27AE60',
                'warning': '#F39C12',
                'danger': '#E74C3C'
            }
        else:
            # Default balanced scheme
            return {
                'primary': '#2C3E50',
                'secondary': '#3498DB',
                'accent': '#E67E22',
                'background': '#F8F9FA',
                'text': '#2D3436',
                'success': '#27AE60',
                'warning': '#F39C12',
                'danger': '#E74C3C'
            }
    
    def _determine_animations(self, adaptation: UIAdaptation) -> Dict[str, Any]:
        """Determine animation settings"""
        if adaptation.animation_level == "reduced":
            return {
                'enabled': True,
                'duration_multiplier': 0.5,
                'complexity': 'minimal',
                'transitions': 'fade',
                'celebratory': False
            }
        elif adaptation.animation_level == "engaging":
            return {
                'enabled': True,
                'duration_multiplier': 1.0,
                'complexity': 'full',
                'transitions': 'slide',
                'celebratory': True
            }
        else:
            return {
                'enabled': True,
                'duration_multiplier': 0.8,
                'complexity': 'moderate',
                'transitions': 'fade',
                'celebratory': True
            }


# Global instance
emotion_engine = EmotionEngine()


# === API Helper Functions ===

def get_user_emotional_state(user_id: str) -> Dict[str, Any]:
    """Get full emotional state for API response"""
    return emotion_engine.get_state(user_id).to_dict()

def process_user_trigger(
    user_id: str, 
    trigger_name: str, 
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Process a trigger and return new state"""
    try:
        trigger = EmotionalTrigger(trigger_name)
    except ValueError:
        return {'error': f'Unknown trigger: {trigger_name}'}
    
    state = emotion_engine.process_trigger(user_id, trigger, context)
    return state.to_dict()

def get_adaptive_dashboard(user_id: str) -> Dict[str, Any]:
    """Get full adaptive dashboard configuration"""
    return emotion_engine.get_dashboard_config(user_id)

def get_ui_adaptation(user_id: str) -> Dict[str, Any]:
    """Get UI adaptation settings"""
    return emotion_engine.calculate_ui_adaptation(user_id).to_dict()
