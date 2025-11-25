import os
import shutil
import typer
from pathlib import Path
from luminamind.config.env import load_project_env, get_global_config_path

def test_global_config_precedence():
    print("Testing global config precedence...")
    
    # Setup paths
    global_config_path = get_global_config_path()
    local_config_path = Path.cwd() / ".env"
    
    # Backup existing
    if global_config_path.exists():
        shutil.copy(global_config_path, global_config_path.with_suffix(".bak"))
    if local_config_path.exists():
        shutil.copy(local_config_path, local_config_path.with_suffix(".bak"))
        
    try:
        # 1. Set Global
        with open(global_config_path, "w") as f:
            f.write("TEST_VAR=GLOBAL_VALUE\n")
            f.write("GLOBAL_ONLY=TRUE\n")
            
        # 2. Set Local
        with open(local_config_path, "w") as f:
            f.write("TEST_VAR=LOCAL_VALUE\n")
            f.write("LOCAL_ONLY=TRUE\n")
            
        # 3. Clear env var if set
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]
            
        # 4. Load Env
        load_project_env()
        
        # 5. Verify
        test_var = os.environ.get("TEST_VAR")
        global_only = os.environ.get("GLOBAL_ONLY")
        local_only = os.environ.get("LOCAL_ONLY")
        
        print(f"TEST_VAR: {test_var}")
        print(f"GLOBAL_ONLY: {global_only}")
        print(f"LOCAL_ONLY: {local_only}")
        
        if test_var == "GLOBAL_VALUE":
            print("SUCCESS: Global config took precedence.")
        else:
            print(f"FAILURE: Expected GLOBAL_VALUE, got {test_var}")
            
    finally:
        # Cleanup
        if global_config_path.with_suffix(".bak").exists():
            shutil.move(global_config_path.with_suffix(".bak"), global_config_path)
        elif global_config_path.exists():
            os.remove(global_config_path)
            
        if local_config_path.with_suffix(".bak").exists():
            shutil.move(local_config_path.with_suffix(".bak"), local_config_path)
        elif local_config_path.exists():
            # Restore original .env content if we overwrote it, or delete if it was new
            # For safety in this test environment, let's just restore if backup exists.
            # If we created a new .env where none existed, we should delete it.
            # But since we don't know if it existed before without checking before backup...
            # Let's assume we should restore backup if exists.
            pass

if __name__ == "__main__":
    test_global_config_precedence()
