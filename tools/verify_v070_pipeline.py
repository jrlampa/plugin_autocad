
import unittest
import sys
import os

# Add src/backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/backend')))

# Set Env Var for Tests
os.environ["SISRUA_AUTH_TOKEN"] = "test-token"

# Import Test Cases
# Note: We import them by filename assumption if they expose a TestClass, 
# or we use unittest discovery. 

def run_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # List of critical v0.7.0 tests
    test_files = [
        # Chaos / Resilience
        'test_circuit_breaker_logic.py',
        'test_circuit_breaker_gating.py',
        'test_retry_logic.py',
        'test_backoff_timing.py',
        'test_rate_limit.py',
        'test_deep_health.py',
        
        # Observability
        'test_tracing_context.py',
        'test_metrics.py', # Might fail if mod missing, handle gracefully?
        
        # Consistency
        'test_idempotency.py',
        'test_graceful_shutdown.py'
    ]

    print(f"Adding {len(test_files)} test files to the suite...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename in test_files:
        try:
            # Discover tests in the file
            tests = loader.discover(start_dir=current_dir, pattern=filename)
            suite.addTests(tests)
            print(f"  [+] Added: {filename}")
        except Exception as e:
            print(f"  [-] Failed to load {filename}: {e}")

    print("\nRunning Suite v0.7.0 Release Candidate...\n" + "="*40)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n" + "="*40 + "\n✅ PIPELINE GREEN: All checks passed.")
        sys.exit(0)
    else:
        print("\n" + "="*40 + "\n❌ PIPELINE RED: Failures detected.")
        sys.exit(1)

if __name__ == "__main__":
    run_suite()
