"""Test the LLM-based action router."""

import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.action_router_llm import LLMActionRouter, route_input_llm


async def test_router():
    """Test the LLM router with various inputs."""
    print("="*60)
    print("  Testing LLM-Based Action Router")
    print("="*60)
    
    router = LLMActionRouter()
    
    test_cases = [
        # GENERATE_ROUTINE cases
        ("I want to create a new 3-day workout split", "generate_program"),
        ("Generate a new program for hypertrophy", "generate_program"),
        ("Make me a new mesocycle starting next week", "generate_program"),
        
        # UPDATE_ROUTINE cases
        ("Can you make my push day harder?", "update_routine"),
        ("Swap out squats for leg press in my routine", "update_routine"),
        ("I want to increase the weight on bench press", "update_routine"),
        
        # CHAT_RESPONSE cases
        ("Hello! How are you?", "chat_response"),
        ("What's a good alternative to bench press?", "chat_response"),
        ("How do I do a proper squat?", "chat_response"),
        ("What was my goal again?", "chat_response"),
    ]
    
    print("\nTesting routing decisions:\n")
    
    results = []
    for input_text, expected in test_cases:
        try:
            prompt_key, metadata = await router.route(input_text)
            
            status = "[OK]" if prompt_key == expected else "[FAIL]"
            intent = metadata.get("intent", "UNKNOWN")
            
            print(f"{status} Input: '{input_text[:50]}...'")
            print(f"     Expected: {expected}")
            print(f"     Got: {prompt_key} (intent: {intent})")
            print()
            
            results.append({
                "input": input_text,
                "expected": expected,
                "actual": prompt_key,
                "correct": prompt_key == expected,
                "metadata": metadata,
            })
            
        except Exception as e:
            print(f"[ERROR] Failed to route: {e}")
            print(f"        Input: '{input_text}'")
            print()
            results.append({
                "input": input_text,
                "expected": expected,
                "actual": None,
                "correct": False,
                "error": str(e),
            })
    
    # Summary
    print("="*60)
    print("  Summary")
    print("="*60)
    
    total = len(results)
    correct = sum(1 for r in results if r.get("correct", False))
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\nTotal tests: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    
    if correct == total:
        print("\n[SUCCESS] All routing decisions were correct!")
    else:
        print("\n[WARN] Some routing decisions were incorrect.")
        print("\nIncorrect cases:")
        for r in results:
            if not r.get("correct", False):
                print(f"  - '{r['input'][:50]}...'")
                print(f"    Expected: {r['expected']}, Got: {r.get('actual', 'ERROR')}")
    
    print("="*60)


async def test_with_conversation_history():
    """Test routing with conversation history context."""
    print("\n" + "="*60)
    print("  Testing with Conversation History")
    print("="*60)
    
    router = LLMActionRouter()
    
    # Simulate a conversation
    conversation = [
        {"role": "user", "content": "What's a good chest exercise?"},
        {"role": "assistant", "content": "Bench press is excellent for chest development."},
        {"role": "user", "content": "Can you add that to my routine?"},  # This should route to UPDATE_ROUTINE
    ]
    
    print("\nConversation context:")
    for msg in conversation:
        print(f"  {msg['role']}: {msg['content']}")
    
    print("\nRouting the last message with context...\n")
    
    prompt_key, metadata = await router.route(
        "Can you add that to my routine?",
        context={"conversation_history": conversation}
    )
    
    print(f"Routed to: {prompt_key}")
    print(f"Intent: {metadata.get('intent')}")
    print(f"Method: {metadata.get('method')}")
    
    expected = "update_routine"
    if prompt_key == expected:
        print(f"\n[OK] Correctly routed to {expected} using conversation context!")
    else:
        print(f"\n[WARN] Expected {expected} but got {prompt_key}")
    
    print("="*60)


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  LLM-Based Action Router Test Suite")
    print("="*60)
    print("\nThis will make actual LLM API calls.")
    print("Make sure your OPENAI_API_KEY is set in .env\n")
    
    try:
        # Test basic routing
        await test_router()
        
        # Test with conversation history
        await test_with_conversation_history()
        
        print("\n[SUCCESS] All tests completed!")
        
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

