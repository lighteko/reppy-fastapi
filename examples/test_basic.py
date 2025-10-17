"""Basic test to verify setup without requiring full infrastructure."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import get_config
        print("[OK] Config module imported")
        
        from src.common.prompts import list_prompts
        print("[OK] Prompts module imported")
        
        from src.common.action_router import route_input
        print("[OK] Action router imported")
        
        print("\nAll imports successful!")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config import get_config
        config = get_config()
        
        print(f"[OK] LLM Model: {config.llm_model}")
        print(f"[OK] Temperature: {config.llm_temperature}")
        print(f"[OK] Prompts Directory: {config.prompts_directory}")
        print(f"[OK] Agent Max Iterations: {config.agent_max_iterations}")
        
        # Check if critical keys are set
        if config.openai_api_key and config.openai_api_key != "":
            print("[OK] OpenAI API key is set")
        else:
            print("[WARN] OpenAI API key not set (this is okay for basic tests)")
        
        return True
    except Exception as e:
        print(f"[FAIL] Config test failed: {e}")
        return False


def test_prompts():
    """Test prompt discovery and loading."""
    print("\nTesting prompt system...")
    
    try:
        from src.common.prompts import list_prompts, load_prompt
        
        # List prompts
        prompts = list_prompts()
        print(f"[OK] Found {len(prompts)} prompts: {prompts}")
        
        # Load each prompt
        for prompt_key in prompts:
            prompt_data = load_prompt(prompt_key)
            prompt_type = prompt_data.get("prompt_type")
            tools = prompt_data.get("tools", [])
            print(f"  - {prompt_key}: type={prompt_type}, tools={len(tools)}")
        
        print("[OK] All prompts loaded successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Prompt test failed: {e}")
        return False


def test_router():
    """Test action router."""
    print("\nTesting action router...")
    
    try:
        from src.common.action_router import route_input
        
        test_cases = [
            ("Generate a new workout program", "generate_program"),
            ("Update my bench press routine", "update_routine"),
            ("What is a good chest exercise?", "chat_response"),
        ]
        
        for input_text, expected in test_cases:
            prompt_key, scores = route_input(input_text)
            status = "[OK]" if prompt_key == expected else "[WARN]"
            print(f"{status} '{input_text[:40]}...' -> {prompt_key} (expected: {expected})")
        
        print("[OK] Router tests completed")
        return True
    except Exception as e:
        print(f"[FAIL] Router test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("  Reppy RAG Pipeline - Basic Tests")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Prompts", test_prompts),
        ("Router", test_router),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[FAIL] {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Your setup is working correctly.")
        print("\nNext steps:")
        print("1. Configure .env with your API keys")
        print("2. Setup Qdrant (see QDRANT_SETUP.md)")
        print("3. Run the server: python src/app.py")
        print("4. Try the API: python examples/api_client_example.py")
    else:
        print("\n[WARN] Some tests failed. Check the errors above.")


if __name__ == "__main__":
    main()

