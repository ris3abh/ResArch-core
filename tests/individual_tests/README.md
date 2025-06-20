# SpinScribe Individual Component Tests

This directory contains tests for individual components of the SpinScribe system.

## Structure

- `test_agent_factory.py` - Tests for the agent factory and agent creation
- `test_database_models.py` - Tests for database models and operations
- `test_knowledge_management.py` - Tests for knowledge management system
- `test_chat_system.py` - Tests for chat and communication system
- `test_workflow_engine.py` - Tests for workflow and task management

## Running Tests

### Run All Tests
```bash
cd tests/individual_tests
python run_tests.py
```

### Run Specific Test
```bash
cd tests/individual_tests
pytest test_agent_factory.py -v
```

### Run with Coverage
```bash
cd tests/individual_tests
pytest test_agent_factory.py --cov=app.agents --cov-report=html
```

## Test Requirements

- All tests should be independent and not rely on external state
- Use fixtures for common setup (database sessions, test projects, etc.)
- Mock external API calls when possible
- Include both positive and negative test cases
- Test error handling scenarios

## Adding New Tests

1. Create a new test file following the naming convention `test_<component>.py`
2. Add the file to the `tests` list in `run_tests.py`
3. Use the provided fixtures in `conftest.py`
4. Follow existing test patterns for consistency
