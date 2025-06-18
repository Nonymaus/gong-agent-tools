#!/usr/bin/env python3
"""
Test HAR compression functionality for Gong integration.

Demonstrates backwards compatibility with existing uncompressed HAR files
and the new compression feature.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from gong.authentication.har_storage import HARStorageConfig, HARStorageManager
from gong.authentication.auth_manager import GongAuthenticationManager


def test_har_compression():
    """Test HAR compression and backwards compatibility."""
    print("🧪 Testing HAR Compression for Gong Integration")
    print("=" * 50)
    
    # Create test HAR data
    test_har = {
        "log": {
            "version": "1.2",
            "creator": {
                "name": "Gong Test",
                "version": "1.0"
            },
            "entries": [
                {
                    "request": {
                        "method": "GET",
                        "url": "https://us-14496.app.gong.io/api/v1/users",
                        "headers": [
                            {"name": "Authorization", "value": "Bearer test_token"}
                        ]
                    },
                    "response": {
                        "status": 200,
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"}
                        ]
                    }
                }
            ]
        }
    }
    
    # Test 1: Save with compression enabled (default)
    print("\n📝 Test 1: Save HAR with compression (default)")
    storage_compressed = HARStorageManager()
    compressed_path = storage_compressed.save_har(
        har_data=test_har,
        session_name="test_compressed",
        metadata={"test": "compression_enabled"}
    )
    print(f"✅ Compressed HAR saved: {compressed_path}")
    print(f"   Size: {compressed_path.stat().st_size} bytes")
    
    # Test 2: Save without compression
    print("\n📝 Test 2: Save HAR without compression")
    config_uncompressed = HARStorageConfig(compression=False)
    storage_uncompressed = HARStorageManager(config_uncompressed)
    uncompressed_path = storage_uncompressed.save_har(
        har_data=test_har,
        session_name="test_uncompressed",
        metadata={"test": "compression_disabled"}
    )
    print(f"✅ Uncompressed HAR saved: {uncompressed_path}")
    print(f"   Size: {uncompressed_path.stat().st_size} bytes")
    
    # Compare sizes
    compression_ratio = 1 - (compressed_path.stat().st_size / uncompressed_path.stat().st_size)
    print(f"\n📊 Compression ratio: {compression_ratio:.1%} size reduction")
    
    # Test 3: Load compressed HAR
    print("\n📖 Test 3: Load compressed HAR")
    loaded_compressed = storage_compressed.load_har(compressed_path)
    print(f"✅ Loaded compressed HAR successfully")
    print(f"   Entries: {len(loaded_compressed['log']['entries'])}")
    
    # Test 4: Load uncompressed HAR
    print("\n📖 Test 4: Load uncompressed HAR")
    loaded_uncompressed = storage_uncompressed.load_har(uncompressed_path)
    print(f"✅ Loaded uncompressed HAR successfully")
    print(f"   Entries: {len(loaded_uncompressed['log']['entries'])}")
    
    # Test 5: Verify data integrity
    print("\n🔍 Test 5: Verify data integrity")
    if json.dumps(loaded_compressed, sort_keys=True) == json.dumps(loaded_uncompressed, sort_keys=True):
        print("✅ Data integrity verified - compressed and uncompressed match")
    else:
        print("❌ Data integrity check failed")
        return False
    
    # Test 6: Test GongAuthenticationManager with both formats
    print("\n🔐 Test 6: Test authentication manager compatibility")
    auth_manager = GongAuthenticationManager()
    
    # Try loading compressed HAR
    try:
        # Note: This will fail because we don't have valid JWT tokens, 
        # but it tests the compression handling
        auth_manager.extract_session_from_har(compressed_path)
    except Exception as e:
        if "No JWT tokens found" in str(e):
            print("✅ Compressed HAR loaded successfully (expected token error)")
        else:
            print(f"❌ Unexpected error with compressed HAR: {e}")
            return False
    
    # Try loading uncompressed HAR
    try:
        auth_manager.extract_session_from_har(uncompressed_path)
    except Exception as e:
        if "No JWT tokens found" in str(e):
            print("✅ Uncompressed HAR loaded successfully (expected token error)")
        else:
            print(f"❌ Unexpected error with uncompressed HAR: {e}")
            return False
    
    # Test 7: List HAR files
    print("\n📋 Test 7: List HAR files")
    har_files = storage_compressed.list_har_files()
    print(f"✅ Found {len(har_files)} HAR files:")
    for har_path, metadata in har_files[:3]:  # Show first 3
        print(f"   - {har_path.name} ({metadata.get('file_size_mb', 0):.1f}MB)")
    
    print("\n🎉 All tests passed! HAR compression is working correctly.")
    print("✨ Backwards compatibility confirmed - both formats work seamlessly.")
    
    # Cleanup test files
    print("\n🧹 Cleaning up test files...")
    compressed_path.unlink()
    uncompressed_path.unlink()
    compressed_path.with_suffix('.json').unlink()
    uncompressed_path.with_suffix('.json').unlink()
    
    return True


if __name__ == "__main__":
    success = test_har_compression()
    sys.exit(0 if success else 1)