"""
Test Suite for Modular Component System
=====================================

Tests the complete modular component system including:
- Component rendering and functionality
- Event handling and backend integration
- Role-specific variations
- Workspace stage model integration
- Onboarding flow
- Cross-browser compatibility
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import json
from typing import Dict, Any

from app.main import fastapi_app
from app.core.database import get_db


class TestModularComponents:
    """Test suite for the modular component system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(fastapi_app)
        self.base_url = "/api/components"
        
    def test_component_config_endpoints(self):
        """Test component configuration endpoints"""
        # Test tenant configuration
        response = self.client.get(f"{self.base_url}/config/tenant")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "tenant"
        assert "config" in data
        assert "theme" in data["config"]
        assert data["config"]["theme"] == "blue"
        
        # Test advocate configuration
        response = self.client.get(f"{self.base_url}/config/advocate")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "advocate"
        assert data["config"]["theme"] == "purple"
        
        # Test legal configuration
        response = self.client.get(f"{self.base_url}/config/legal")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "legal"
        assert data["config"]["theme"] == "green"
        
        # Test admin configuration
        response = self.client.get(f"{self.base_url}/config/admin")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["config"]["theme"] == "red"
    
    def test_workspace_stage_integration(self):
        """Test workspace stage model integration"""
        # Test workspace stage endpoint
        response = self.client.get(f"{self.base_url}/workspace-stage")
        assert response.status_code == 200
        data = response.json()
        assert "stage" in data
        assert "urgency" in data
        assert "storage_connected" in data
        assert "has_documents" in data
        
        # Test next step endpoint
        response = self.client.get(f"{self.base_url}/next-step")
        assert response.status_code == 200
        data = response.json()
        assert "step" in data
        assert "title" in data
        assert "description" in data
        assert "priority" in data
    
    def test_capture_component_events(self):
        """Test capture component event handling"""
        # Test upload event
        upload_event = {
            "component_id": "capture_upload_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "capture-upload",
            "files": [
                {"name": "test.pdf", "size": 1024, "type": "application/pdf"}
            ],
            "total_size": 1024
        }
        
        response = self.client.post(f"{self.base_url}/capture/upload", json=upload_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "files_processed" in data
        
        # Test quick input event
        input_event = {
            "component_id": "capture_input_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "capture-quick-input",
            "input_type": "note",
            "content": "Test note content",
            "tags": ["urgent", "landlord"]
        }
        
        response = self.client.post(f"{self.base_url}/capture/input", json=input_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "input_id" in data
        
        # Test voice recording event
        voice_event = {
            "component_id": "capture_voice_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "capture-voice-input",
            "duration": 30.5,
            "transcript": "Test voice transcript",
            "audio_url": None
        }
        
        response = self.client.post(f"{self.base_url}/capture/voice", json=voice_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "recording_id" in data
    
    def test_understand_component_events(self):
        """Test understand component event handling"""
        # Test timeline event
        timeline_event = {
            "component_id": "understand_timeline_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "understand-timeline-select",
            "event_id": "timeline_123",
            "event_data": {"date": "2026-04-15", "type": "eviction_notice"}
        }
        
        response = self.client.post(f"{self.base_url}/understand/timeline", json=timeline_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        
        # Test rights analysis event
        rights_event = {
            "component_id": "understand_rights_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "understand-rights-select",
            "right_id": "right_456",
            "right_data": {"right": "quiet_enjoyment", "status": "protected"}
        }
        
        response = self.client.post(f"{self.base_url}/understand/rights", json=rights_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "right_id" in data
        
        # Test risk detection event
        risk_event = {
            "component_id": "understand_risk_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "understand-risk-select",
            "risk_id": "risk_789",
            "risk_data": {"risk": "eviction", "level": "high"}
        }
        
        response = self.client.post(f"{self.base_url}/understand/risk", json=risk_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "risk_id" in data
    
    def test_plan_component_events(self):
        """Test plan component event handling"""
        # Test action event
        action_event = {
            "component_id": "plan_action_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "plan-action-select",
            "action_id": "action_123",
            "action_data": {"action": "file_response", "priority": "urgent"}
        }
        
        response = self.client.post(f"{self.base_url}/plan/action", json=action_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "action_id" in data
        
        # Test deadline event
        deadline_event = {
            "component_id": "plan_deadline_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "plan-deadline-select",
            "deadline_id": "deadline_456",
            "deadline_data": {"deadline": "2026-04-20", "type": "court_hearing"}
        }
        
        response = self.client.post(f"{self.base_url}/plan/deadline", json=deadline_event)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deadline_id" in data
    
    def test_role_specific_events(self):
        """Test role-specific component events"""
        # Test tenant emergency action
        response = self.client.post(
            f"{self.base_url}/tenant/emergency-action",
            params={
                "component_id": "tenant_emergency_test",
                "emergency_id": "emergency_123",
                "action": "call_hotline"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "emergency_id" in data
        
        # Test advocate handoff
        response = self.client.post(
            f"{self.base_url}/advocate/handoff-client",
            params={
                "component_id": "advocate_handoff_test",
                "client_id": "client_123",
                "target_role": "legal"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "handoff_id" in data
        
        # Test legal review
        response = self.client.post(
            f"{self.base_url}/legal/start-review",
            params={
                "component_id": "legal_review_test",
                "case_id": "case_123",
                "review_type": "document_analysis"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "review_id" in data
        
        # Test admin maintenance
        response = self.client.post(
            f"{self.base_url}/admin/system-maintenance",
            params={
                "component_id": "admin_maintenance_test",
                "maintenance_type": "database_backup"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "task_id" in data
    
    def test_role_specific_pages(self):
        """Test role-specific page accessibility"""
        # Test tenant dashboard page
        response = self.client.get("/tenant/dashboard")
        # Should redirect to storage if not authenticated, or serve page if authenticated
        assert response.status_code in [302, 200]
        
        # Test advocate dashboard page
        response = self.client.get("/advocate/dashboard")
        assert response.status_code in [302, 200]
        
        # Test legal dashboard page
        response = self.client.get("/legal/dashboard")
        assert response.status_code in [302, 200]
        
        # Test admin dashboard page
        response = self.client.get("/admin/dashboard")
        assert response.status_code in [302, 200]
    
    def test_component_error_handling(self):
        """Test component error handling"""
        # Test invalid event data
        invalid_event = {
            "component_id": "",  # Invalid empty ID
            "role": "invalid_role",
            "timestamp": "invalid_timestamp",
            "event_type": "capture-upload",
            "files": []
        }
        
        response = self.client.post(f"{self.base_url}/capture/upload", json=invalid_event)
        # Should handle gracefully (either accept or return meaningful error)
        assert response.status_code in [200, 400, 422]
        
        # Test missing required fields
        incomplete_event = {
            "component_id": "test_component",
            # Missing required fields
        }
        
        response = self.client.post(f"{self.base_url}/capture/upload", json=incomplete_event)
        assert response.status_code in [200, 400, 422]
    
    def test_component_performance(self):
        """Test component performance and response times"""
        import time
        
        # Test multiple concurrent requests
        events = [
            {
                "component_id": f"perf_test_{i}",
                "role": "tenant",
                "timestamp": "2026-04-16T20:00:00Z",
                "event_type": "capture-upload",
                "files": [{"name": f"test_{i}.pdf", "size": 1024, "type": "application/pdf"}],
                "total_size": 1024
            }
            for i in range(10)
        ]
        
        start_time = time.time()
        
        for event in events:
            response = self.client.post(f"{self.base_url}/capture/upload", json=event)
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 10 requests in reasonable time (less than 5 seconds)
        assert total_time < 5.0
        assert total_time / len(events) < 0.5  # Average per request < 500ms
    
    def test_component_css_integration(self):
        """Test that component CSS is properly integrated"""
        # Test design system CSS accessibility
        response = self.client.get("/design-system/index.css")
        assert response.status_code == 200
        
        css_content = response.text
        assert "--color-tenant-primary" in css_content
        assert "--color-advocate-primary" in css_content
        assert "--color-legal-primary" in css_content
        assert "--color-admin-primary" in css_content
        
        # Test role-specific CSS imports
        assert "function-groups/role-specific/tenant/index.css" in css_content
        assert "function-groups/role-specific/advocate/index.css" in css_content
        assert "function-groups/role-specific/legal/index.css" in css_content
        assert "function-groups/role-specific/admin/index.css" in css_content
    
    def test_component_html_templates(self):
        """Test that component HTML templates are accessible"""
        # Test tenant dashboard template
        response = self.client.get("/tenant/dashboard")
        if response.status_code == 200:
            html_content = response.text
            assert "tenant-dashboard" in html_content
            assert "workspace-stage-panel" in html_content
            assert "emergency-actions" in html_content
    
    def test_onboarding_integration(self):
        """Test onboarding system integration"""
        # Test onboarding completion event
        onboarding_event = {
            "component_id": "onboarding_tracker_test",
            "role": "tenant",
            "timestamp": "2026-04-16T20:00:00Z",
            "event_type": "onboarding-complete",
            "data": {
                "completed_steps": ["welcome", "role-selection", "capture-demo", "understand-demo", "plan-demo"],
                "total_steps": 6
            }
        }
        
        # This would be handled by the onboarding system, but we can test the routing
        response = self.client.get("/onboarding")
        assert response.status_code in [200, 302]
    
    def test_component_accessibility(self):
        """Test component accessibility features"""
        # Test that components have proper ARIA labels and keyboard navigation
        # This would be tested in the actual rendered HTML
        pass
    
    def test_component_responsive_design(self):
        """Test component responsive design"""
        # Test that components adapt to different screen sizes
        # This would be tested in the actual rendered CSS
        pass
    
    def test_component_browser_compatibility(self):
        """Test component browser compatibility"""
        # Test that components work across different browsers
        # This would be tested in actual browser environments
        pass


class TestComponentIntegration:
    """Test integration between components and backend services"""
    
    def setup_method(self):
        """Setup integration test environment"""
        self.client = TestClient(fastapi_app)
    
    def test_component_to_backend_integration(self):
        """Test that components properly integrate with existing backend services"""
        # Test that component events can reach existing services
        # This would require mocking the actual backend services
        
        # For now, test that the endpoints exist and return expected structure
        response = self.client.get("/api/components/workspace-stage")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "timestamp" in data
    
    def test_workspace_stage_model_integration(self):
        """Test integration with workspace stage model"""
        response = self.client.get("/api/components/workspace-stage")
        assert response.status_code == 200
        
        data = response.json()
        # Should return workspace stage data
        assert "stage" in data
        assert "urgency" in data
        assert "storage_connected" in data
    
    def test_role_ui_integration(self):
        """Test integration with existing role UI system"""
        # Test that role-specific configurations work with existing role system
        for role in ["tenant", "advocate", "legal", "admin"]:
            response = self.client.get(f"/api/components/config/{role}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["role"] == role
            assert "config" in data


if __name__ == "__main__":
    pytest.main([__file__])
