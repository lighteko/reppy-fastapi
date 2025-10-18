"""Integration test for LLM action router with real API calls."""

import sys
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common import route_input_llm


async def test_router():
    """Test router with various inputs."""
    print("="*60)
    print("  LLM Action Router Integration Test")
    print("="*60)
    
    test_cases = [
        # Should route to generate_program
        {
            "input": "I want to create a new 3-day workout split",
            "expected": "generate_program"
        },
        {
            "input": "Generate a hypertrophy program for me",
            "expected": "generate_program"
        },
        {
            "input": "Make me a new mesocycle starting next week",
            "expected": "generate_program"
        },
        
        # Should route to update_routine
        {
            "input": "Can you make my push day harder?",
            "expected": "update_routine"
        },
        {
            "input": "Swap out squats for leg press in my routine",
            "expected": "update_routine"
        },
        {
            "input": "Change my bench press weight to 185 lbs",
            "expected": "update_routine"
        },
        
        # Should route to chat_response
        {
            "input": "Hello! How are you?",
            "expected": "chat_response"
        },
        {
            "input": "What's a good exercise for chest?",
            "expected": "chat_response"
        },
        {
            "input": "How do I do a proper squat?",
            "expected": "chat_response"
        },
        {
            "input": "What was my goal again?",
            "expected": "chat_response"
        },
        
        # Contextual test - with conversation history
        {
            "input": "Add that to my routine",
            "expected": "update_routine",
            "context": {
                "conversation_history": [
                    {"role": "user", "content": "What's a good chest exercise?"},
                    {"role": "assistant", "content": "Bench press is excellent for chest development."},
                    {"role": "user", "content": "Add that to my routine"}
                ]
            }
        }
    ]
    
    print("\nRunning tests...\n")
    
    passed = 0
    failed = 0
    errors = []
    
    for i, test in enumerate(test_cases, 1):
        input_text = test["input"]
        expected = test["expected"]
        context = test.get("context")
        
        try:
            # Route with LLM
            prompt_key, metadata = await route_input_llm(input_text, context)
            intent = metadata.get("intent", "UNKNOWN")
            
            # Check result
            if prompt_key == expected:
                status = "[PASS]"
                passed += 1
            else:
                status = "[FAIL]"
                failed += 1
                errors.append({
                    "test": i,
                    "input": input_text,
                    "expected": expected,
                    "got": prompt_key
                })
            
            print(f"{status} Test {i}:")
            print(f"  Input: '{input_text[:60]}{'...' if len(input_text) > 60 else ''}'")
            print(f"  Expected: {expected}")
            print(f"  Got: {prompt_key} (intent: {intent})")
            if context:
                print(f"  Context: conversation_history ({len(context['conversation_history'])} messages)")
            print()
            
        except Exception as e:
            print(f"[ERROR] Test {i} failed with exception:")
            print(f"  Input: '{input_text}'")
            print(f"  Error: {e}")
            print()
            failed += 1
            errors.append({
                "test": i,
                "input": input_text,
                "error": str(e)
            })
    
    # Summary
    print("="*60)
    print("  Summary")
    print("="*60)
    print(f"\nTotal: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
    
    if failed > 0:
        print(f"\n[WARNING] {failed} test(s) failed:")
        for error in errors:
            print(f"\n  Test {error['test']}:")
            print(f"    Input: {error['input'][:50]}...")
            if "error" in error:
                print(f"    Error: {error['error']}")
            else:
                print(f"    Expected: {error['expected']}, Got: {error['got']}")
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
    
    print("="*60)
    
    return failed == 0


async def main():
    """Run integration test."""
    print("\n" + "="*60)
    print("  LLM Action Router - Integration Test")
    print("="*60)
    print("\nThis will make actual LLM API calls.")
    print("Make sure OPENAI_API_KEY is set in .env\n")
    
    try:
        success = await test_router()
        
        if success:
            print("\n[OK] All router tests passed successfully!")
            sys.exit(0)
        else:
            print("\n[WARN] Some tests failed. Review results above.")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

