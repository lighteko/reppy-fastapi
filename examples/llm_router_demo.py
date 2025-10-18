"""Demonstration of LLM-based vs Pattern-based routing."""

import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.action_router import route_input
from src.common.action_router_llm import route_input_llm


async def compare_routers():
    """Compare pattern-based and LLM-based routers."""
    print("="*60)
    print("  Pattern-Based vs LLM-Based Router Comparison")
    print("="*60)
    
    test_cases = [
        # Clear cases
        "I want to generate a new 3-day workout split",
        "Can you make my push day harder?",
        "Hello! How are you?",
        
        # Ambiguous cases
        "I want to increase the weight on bench press",  # Update or question?
        "What exercises should I do for chest?",         # Chat
        "Add bench press to my routine",                 # Update (contextual)
    ]
    
    print("\nComparing routing decisions:\n")
    print(f"{'Input':<50} | {'Pattern':<15} | {'LLM':<15} | {'Match'}")
    print("-" * 95)
    
    matches = 0
    total = len(test_cases)
    
    for input_text in test_cases:
        # Pattern routing
        pattern_key, _ = route_input(input_text)
        
        # LLM routing
        llm_key, llm_meta = await route_input_llm(input_text)
        
        match = "✓" if pattern_key == llm_key else "✗"
        if pattern_key == llm_key:
            matches += 1
        
        # Truncate input for display
        display_input = (input_text[:47] + "...") if len(input_text) > 50 else input_text
        
        print(f"{display_input:<50} | {pattern_key:<15} | {llm_key:<15} | {match}")
    
    print("-" * 95)
    print(f"\nAgreement: {matches}/{total} ({matches/total*100:.0f}%)")
    
    print("\n" + "="*60)
    print("  Context-Aware Routing Example")
    print("="*60)
    
    # Demonstrate conversation context
    conversation = [
        {"role": "user", "content": "What's a good chest exercise?"},
        {"role": "assistant", "content": "Bench press is excellent for chest development."},
        {"role": "user", "content": "Can you add that to my routine?"},
    ]
    
    print("\nConversation history:")
    for msg in conversation:
        print(f"  {msg['role']}: {msg['content']}")
    
    print("\nLast message: 'Can you add that to my routine?'")
    
    # Pattern router (no context awareness)
    pattern_key, _ = route_input("Can you add that to my routine?")
    print(f"\nPattern router: {pattern_key}")
    
    # LLM router (with context)
    llm_key, llm_meta = await route_input_llm(
        "Can you add that to my routine?",
        context={"conversation_history": conversation}
    )
    print(f"LLM router (with context): {llm_key}")
    print(f"  Intent: {llm_meta.get('intent')}")
    
    print("\n" + "="*60)
    print("  Key Differences")
    print("="*60)
    
    print("""
Pattern-Based Router:
  ✓ Fast (<1ms)
  ✓ Deterministic
  ✓ No API costs
  ✗ Limited context awareness
  ✗ Requires regex maintenance
  
LLM-Based Router:
  ✓ Context-aware (uses conversation history)
  ✓ Natural language understanding
  ✓ Higher accuracy (~90%+)
  ✗ Slower (~500-1500ms)
  ✗ Requires API calls (~$0.0001/request)
    """)
    
    print("="*60)


async def main():
    """Run the comparison."""
    print("\nThis demo will make actual LLM API calls.")
    print("Make sure your OPENAI_API_KEY is set in .env\n")
    
    try:
        await compare_routers()
        print("\n[SUCCESS] Demo completed!")
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

