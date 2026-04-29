# Re-export from templates.services.positronic_brain
try:
    from app.templates.services.positronic_brain import *
except ImportError:
    # Stub for Core build where brain is not available
    def get_brain():
        raise RuntimeError("Positronic brain not available in Core build")
    
    class PositronicBrain:
        pass
    
    class BrainEvent:
        pass
    
    class EventType:
        pass
    
    class ModuleType:
        pass
