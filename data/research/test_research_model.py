#!/usr/bin/env python3
"""
Test script for the research_model Django management command.
This script demonstrates how to use the new research model command.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Test the research_model command."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    manage_py_path = project_root / "manage.py"
    
    # Configuration file path
    config_path = project_root / "data" / "data" / "research" / "config" / "research_model.yml"
    
    print("=" * 80)
    print("RESEARCH MODEL COMMAND TEST")
    print("=" * 80)
    
    # Check if manage.py exists
    if not manage_py_path.exists():
        print(f"❌ manage.py not found at {manage_py_path}")
        return False
    
    # Check if config file exists
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        print("Please create the configuration file first.")
        return False
    
    print(f"✅ Found manage.py at: {manage_py_path}")
    print(f"✅ Found config file at: {config_path}")
    
    # Build the command
    cmd = [
        sys.executable,
        str(manage_py_path),
        "research_model",
        "--config",
        str(config_path)
    ]
    
    print(f"\n🚀 Running command:")
    print(f"   {' '.join(cmd)}")
    print("\n" + "=" * 80)
    
    try:
        # Run the command
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        # Print output
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Check return code
        if result.returncode == 0:
            print("\n✅ Research model command completed successfully!")
            return True
        else:
            print(f"\n❌ Research model command failed with return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n❌ Error running command: {e}")
        return False

def check_prerequisites():
    """Check if prerequisites are met."""
    print("Checking prerequisites...")
    
    # Check if we're in the right directory
    project_root = Path(__file__).parent.parent.parent.parent
    manage_py = project_root / "manage.py"
    
    if not manage_py.exists():
        print("❌ manage.py not found. Please run this script from the project root.")
        return False
    
    # Check if Django is available
    try:
        import django
        print(f"✅ Django {django.get_version()} is available")
    except ImportError:
        print("❌ Django is not installed")
        return False
    
    # Check if required packages are available
    required_packages = ['sklearn', 'pandas', 'numpy', 'joblib', 'yaml']
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} is not installed")
            return False
    
    return True

if __name__ == "__main__":
    print("Research Model Command Test")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please install required packages.")
        sys.exit(1)
    
    # Run the test
    success = main()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("\nNext steps:")
        print("1. Check the output files in the configured output directory")
        print("2. Review the research results JSON file")
        print("3. Use the best trained model for your anomaly detection tasks")
    else:
        print("\n💥 Test failed!")
        print("\nTroubleshooting:")
        print("1. Check that your CSV files exist and are accessible")
        print("2. Verify the configuration file paths are correct")
        print("3. Ensure you have sufficient disk space for output files")
        print("4. Check the Django logs for more detailed error information")
    
    sys.exit(0 if success else 1) 