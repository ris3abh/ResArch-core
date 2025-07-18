# Spinscribe Web Integration

This integration implements the **Service Wrapper Pattern** to add web interfaces to the existing Spinscribe CAMEL-AI system without modifying any agent communication.

## Architecture

```
Web Frontend ←→ FastAPI Backend ←→ Service Wrapper ←→ Existing CAMEL System
```

### Key Principles

1. **Zero Changes** to existing CAMEL agent communication
2. **Direct Import** of existing Spinscribe modules
3. **Service Wrapper** pattern for web interface
4. **Preserve** all agent-to-agent interactions

## Quick Start

1. **Setup Infrastructure**:
   ```bash
   ./scripts/dev_setup.sh
   ```

2. **Start Backend**:
   ```bash
   ./scripts/start_backend.sh
   ```

3. **Test Integration**:
   ```bash
   python scripts/test_integration.py
   ```

## What's Preserved

- ✅ All CAMEL Workforce functionality
- ✅ Agent-to-agent communication protocols
- ✅ Enhanced workflow processing
- ✅ Knowledge management and RAG
- ✅ Checkpoint system integration
- ✅ Memory management (100K tokens)

## What's Added

- 🌐 FastAPI web interface
- 🔄 Real-time WebSocket updates
- 📊 Progress monitoring
- 🗄️ Database persistence
- 🔒 Authentication system
- 📱 RESTful API endpoints

## Using Existing Spinscribe Modules

The integration directly imports your existing modules:

```python
from spinscribe.enhanced_process import run_enhanced_content_task
from spinscribe.workforce.enhanced_builder import EnhancedWorkforceBuilder
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
```

No modifications needed to existing code!

## API Endpoints

### Workflows
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows/{id}` - Get status
- `POST /api/v1/workflows/{id}/pause` - Pause workflow
- `POST /api/v1/workflows/{id}/cancel` - Cancel workflow

### Checkpoints
- `GET /api/v1/checkpoints/{id}` - Get checkpoint
- `POST /api/v1/checkpoints/{id}/approve` - Approve/reject

### WebSocket
- `WS /api/v1/workflows/{id}/live` - Real-time updates

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

## Development

The system uses your existing docker-compose.yml with:
- PostgreSQL (port 5432)
- Redis (port 6379) 
- Qdrant (port 6333)

## Testing

Integration tests verify that:
- Web API correctly starts CAMEL workflows
- Existing agent communication is preserved
- Real-time monitoring works
- Checkpoint system integrates properly
