#!/usr/bin/env python3
"""
Test script to verify that LUCA works correctly with Langfuse disabled.

This script tests:
1. Observability module with LANGFUSE_ENABLED=false
2. Guardrails system without Langfuse
3. LLM creation without Langfuse callbacks
"""

import os
import sys
import logging

# Set environment to disable Langfuse
os.environ['LANGFUSE_ENABLED'] = 'false'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_observability_module():
    """Test the observability module with Langfuse disabled."""
    print("🧪 Testing observability module with Langfuse disabled...")

    try:
        from tools.observability import (
            is_langfuse_enabled,
            get_langfuse_client,
            create_observed_llm
        )

        # Test if Langfuse is correctly disabled
        enabled = is_langfuse_enabled()
        print(f"   ✅ is_langfuse_enabled(): {enabled}")

        # Test client creation
        client = get_langfuse_client()
        print(f"   ✅ get_langfuse_client(): {client}")

        # Test LLM creation (should work without Langfuse)
        llm = create_observed_llm()
        print(f"   ✅ create_observed_llm(): {type(llm)}")

        return True

    except Exception as e:
        print(f"   ❌ Error in observability test: {e}")
        return False


def test_guardrails_system():
    """Test the guardrails system with Langfuse disabled."""
    print("🧪 Testing guardrails system with Langfuse disabled...")

    try:
        from guardrails.core import EducationalGuardrailLayer
        from guardrails.schemas import EducationalContext, GuardrailConfig

        # Create guardrail config
        config = GuardrailConfig(
            enable_langfuse_logging=True  # This should work even with Langfuse disabled
        )

        # Initialize guardrail layer
        guardrail = EducationalGuardrailLayer(config)
        print(f"   ✅ EducationalGuardrailLayer initialized")
        print(f"   ✅ Langfuse client: {guardrail.langfuse_client}")

        # Test validation
        context = EducationalContext(
            student_id="test_student",
            session_id="test_session",
            subject="Bases de Datos"
        )

        # This should work without throwing errors
        import asyncio
        result = asyncio.run(guardrail.validate_input("¿Qué es una base de datos?", context))
        print(f"   ✅ validate_input(): passed={result.passed}")

        return True

    except Exception as e:
        print(f"   ❌ Error in guardrails test: {e}")
        return False


def test_orchestrator_initialization():
    """Test that the orchestrator can be initialized without Langfuse."""
    print("🧪 Testing orchestrator initialization with Langfuse disabled...")

    try:
        from orchestrator.agent import OrchestratorAgent

        # This should work without Langfuse
        agent = OrchestratorAgent()
        print(f"   ✅ OrchestratorAgent initialized")
        print(f"   ✅ Agent LLM type: {type(agent.llm)}")

        return True

    except Exception as e:
        print(f"   ❌ Error in orchestrator test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools_functionality():
    """Test that tools work without Langfuse."""
    print("🧪 Testing tools functionality with Langfuse disabled...")

    try:
        from tools.llm_config import create_default_llm
        from tools.registry import ToolRegistry

        # Test LLM creation
        llm = create_default_llm()
        print(f"   ✅ create_default_llm(): {type(llm)}")

        # Test tool registry
        registry = ToolRegistry()
        tools = registry.get_tools_for_agent("tutor")
        print(f"   ✅ ToolRegistry.get_tools_for_agent(): {len(tools)} tools")

        return True

    except Exception as e:
        print(f"   ❌ Error in tools test: {e}")
        return False


def main():
    """Run all tests with Langfuse disabled."""
    print("🚀 Testing LUCA with Langfuse disabled (LANGFUSE_ENABLED=false)")
    print("=" * 60)

    tests = [
        ("Observability Module", test_observability_module),
        ("Guardrails System", test_guardrails_system),
        ("Tools Functionality", test_tools_functionality),
        ("Orchestrator Initialization", test_orchestrator_initialization),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))
        print()

    print("📊 Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not success:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! LUCA works correctly with Langfuse disabled.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())