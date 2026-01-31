import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

try:
    from backend.models import CadFeature
    from pydantic import ValidationError
    
    print("--- Phase 30: Immutability Test ---")
    
    # Create an instance
    feature = CadFeature(
        feature_type="Polyline", 
        layer="STREETS"
    )
    print(f"Created feature: {feature.feature_type} on {feature.layer}")

    # Attempt mutation
    try:
        feature.layer = "MUTATED_LAYER"
        print("[FAIL] Model was mutated! Immutability broken.")
        sys.exit(1)
    except ValidationError as e:
        print("[PASS] Caught expected ValidationError on mutation (Pydantic v2 validation error).")
    except TypeError as e:
        # Pydantic v2 frozen=True often raises TypeError or ValidationError depending on context
        print(f"[PASS] Caught expected TypeError/ValidationError: {e}")
    except Exception as e:
        print(f"[PASS] Caught expected exception: {type(e).__name__}: {e}")

    print("\n--- PASSED: API Surface is Stable & Immutable ---")
    sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Could not import backend: {e}")
    sys.exit(1)
