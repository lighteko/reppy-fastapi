"""Example API client usage with requests."""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api/v1"


def example_mode_a():
    """Example Mode A: Route and execute."""
    print("\n=== Mode A: Route and Execute ===\n")
    
    payload = {
        "input": "I want to generate a new workout program for hypertrophy",
        "user_id": "user-123",
        "context": {
            "user_profile": {
                "goal": "HYPERTROPHY",
                "experience_level": "INTERMEDIATE",
                "unit_system": "CM_KG",
                "body_weight": 75.0,
                "height": 180.0,
                "sex": "MALE",
            },
            "job_context": {
                "program_name": "Summer Gains 2025",
                "start_date": "2025-11-01",
                "goal_date": "2025-12-31",
                "additional_info": "Focus on compound movements",
            },
            "available_context": {
                "exercises": [
                    {"exercise_code": "BARBELL_BENCH_PRESS", "main_muscle_code": "CHEST"},
                    {"exercise_code": "BARBELL_SQUAT", "main_muscle_code": "LEGS"},
                    {"exercise_code": "BARBELL_DEADLIFT", "main_muscle_code": "BACK"},
                ],
                "set_types": [
                    {"set_type_code": "NORMAL"},
                    {"set_type_code": "WARMUP"},
                    {"set_type_code": "DROPSET"},
                ],
            },
        },
    }
    
    response = requests.post(f"{BASE_URL}/route", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Success: {result['success']}")
        print(f"Prompt used: {result['prompt_key']}")
        print(f"\nData preview: {json.dumps(result['data'], indent=2)[:500]}...")
    else:
        print(f"Error {response.status_code}: {response.text}")


def example_mode_b():
    """Example Mode B: Direct execution."""
    print("\n=== Mode B: Direct Execute ===\n")
    
    payload = {
        "prompt_key": "chat_response",
        "input": "What's a good alternative to bench press if I have shoulder pain?",
        "user_id": "user-123",
        "context": {
            "user_profile": {
                "username": "Alex",
                "experience_level": "INTERMEDIATE",
                "goal": "HYPERTROPHY",
            },
            "conversation_history": [
                {"role": "user", "content": "What's a good alternative to bench press if I have shoulder pain?"},
            ],
        },
    }
    
    response = requests.post(f"{BASE_URL}/run", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Success: {result['success']}")
        print(f"\nReply: {result['data']['reply']}")
        if result['data'].get('suggested_questions'):
            print(f"\nSuggested questions:")
            for q in result['data']['suggested_questions']:
                print(f"  - {q}")
    else:
        print(f"Error {response.status_code}: {response.text}")


def example_list_prompts():
    """Example listing prompts."""
    print("\n=== List Prompts ===\n")
    
    response = requests.get(f"{BASE_URL}/prompts")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Available prompts ({len(result['prompts'])}):")
        for prompt in result['prompts']:
            print(f"  - {prompt}")
    else:
        print(f"Error {response.status_code}: {response.text}")


def example_health_check():
    """Example health check."""
    print("\n=== Health Check ===\n")
    
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Overall status: {result['status']}")
        print(f"\nServices:")
        for service, status in result['services'].items():
            print(f"  {service}: {status['status']}")
    else:
        print(f"Error {response.status_code}: {response.text}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("  Reppy RAG Pipeline - API Client Examples")
    print("="*60)
    
    try:
        example_list_prompts()
        example_health_check()
        
        # Uncomment to test actual execution (requires full setup)
        # example_mode_a()
        # example_mode_b()
        
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Could not connect to API server.")
        print("Make sure the server is running: python src/app.py")
    
    print("\n" + "="*60)
    print("  Examples complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

