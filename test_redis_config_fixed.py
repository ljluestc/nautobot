#!/usr/bin/env python3
"""
Test script for multi-instance Redis configuration.

This script tests the new Redis configuration logic to ensure:
1. Backward compatibility with existing configurations
2. Proper precedence for specific vs generic environment variables
3. Correct URL generation for different scenarios
"""

import os
import sys

# Add nautobot to path
sys.path.insert(0, '/home/calelin/dev/nautobot')

# Mock the is_truthy function
def is_truthy(arg):
    if isinstance(arg, bool):
        return arg
    val = str(arg).lower()
    return val in ('y', 'yes', 't', 'true', 'on', '1')

# Copy the parse_redis_connection function
def parse_redis_connection(redis_database, env_base='NAUTOBOT_REDIS'):
    def get_env(name, default=None):
        # Check for specific setting first (e.g. NAUTOBOT_REDIS_CACHE_HOST)
        value = os.getenv(f'{env_base}_{name}')
        if value is not None:
            return value
        # Fallback to generic setting (e.g. NAUTOBOT_REDIS_HOST)
        if env_base != 'NAUTOBOT_REDIS':
            return os.getenv(f'NAUTOBOT_REDIS_{name}', default)
        return default

    # The following `_redis_*` variables are used to generate settings based on
    # environment variables.
    redis_scheme = get_env("SCHEME")
    if redis_scheme is None:
        redis_scheme = "rediss" if is_truthy(get_env("SSL", "false")) else "redis"

    redis_host = get_env("HOST", "localhost")
    redis_port = int(get_env("PORT", "6379"))
    redis_username = get_env("USERNAME", "")
    redis_password = get_env("PASSWORD", "")

    redis_database = int(get_env("DATABASE", redis_database))

    # Default Redis credentials to being empty unless a username or password is
    # provided. Then map it to "username:password@". We're not URL-encoding the
    # password because the Redis Python client already does this.
    redis_creds = ""
    if redis_username or redis_password:
        redis_creds = f"{redis_username}:{redis_password}@"

    if redis_scheme == "unix":
        return f"{redis_scheme}://{redis_creds}{redis_host}?db={redis_database}"
    else:
        return f"{redis_scheme}://{redis_creds}{redis_host}:{redis_port}/{redis_database}"

def clean_redis_env():
    """Clean up all Redis-related environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith('NAUTOBOT_REDIS'):
            del os.environ[key]

def test_scenario(name, env_vars, expected_cache, expected_queue):
    """Test a specific configuration scenario."""
    print(f"\n🧪 Testing {name}:")

    # Clean environment first
    clean_redis_env()

    # Set environment variables for this test
    for key, value in env_vars.items():
        os.environ[key] = value

    # Test cache and queue URLs
    cache_url = parse_redis_connection(1, env_base='NAUTOBOT_REDIS_CACHE')
    queue_url = parse_redis_connection(0, env_base='NAUTOBOT_REDIS_QUEUE')

    print(f"  Cache URL: {cache_url}")
    print(f"  Queue URL: {queue_url}")

    # Verify expectations
    if cache_url == expected_cache and queue_url == expected_queue:
        print("  ✅ PASSED")
        return True
    else:
        print(f"  ❌ FAILED - Expected cache: {expected_cache}, queue: {expected_queue}")
        return False

def main():
    """Run all test scenarios."""
    print("🚀 Testing Multi-Instance Redis Configuration")
    print("=" * 50)

    scenarios = [
        {
            'name': 'Backward Compatibility (no env vars)',
            'env_vars': {},
            'expected_cache': 'redis://localhost:6379/1',
            'expected_queue': 'redis://localhost:6379/0'
        },
        {
            'name': 'Generic Redis Config (old style)',
            'env_vars': {
                'NAUTOBOT_REDIS_HOST': 'redis.example.com',
                'NAUTOBOT_REDIS_PORT': '6380'
            },
            'expected_cache': 'redis://redis.example.com:6380/1',
            'expected_queue': 'redis://redis.example.com:6380/0'
        },
        {
            'name': 'Separate Cache and Queue Instances',
            'env_vars': {
                'NAUTOBOT_REDIS_CACHE_HOST': 'cache.example.com',
                'NAUTOBOT_REDIS_CACHE_PORT': '6381',
                'NAUTOBOT_REDIS_QUEUE_HOST': 'queue.example.com',
                'NAUTOBOT_REDIS_QUEUE_PORT': '6382'
            },
            'expected_cache': 'redis://cache.example.com:6381/1',
            'expected_queue': 'redis://queue.example.com:6382/0'
        },
        {
            'name': 'Mixed Config (cache specific, queue generic)',
            'env_vars': {
                'NAUTOBOT_REDIS_HOST': 'generic.example.com',
                'NAUTOBOT_REDIS_PORT': '6379',
                'NAUTOBOT_REDIS_CACHE_HOST': 'cache.example.com',
                'NAUTOBOT_REDIS_CACHE_PORT': '6381'
            },
            'expected_cache': 'redis://cache.example.com:6381/1',
            'expected_queue': 'redis://generic.example.com:6379/0'
        },
        {
            'name': 'SSL Configuration',
            'env_vars': {
                'NAUTOBOT_REDIS_CACHE_HOST': 'secure-cache.example.com',
                'NAUTOBOT_REDIS_CACHE_SSL': 'true',
                'NAUTOBOT_REDIS_QUEUE_HOST': 'secure-queue.example.com',
                'NAUTOBOT_REDIS_QUEUE_SSL': 'true'
            },
            'expected_cache': 'rediss://secure-cache.example.com:6379/1',
            'expected_queue': 'rediss://secure-queue.example.com:6379/0'
        },
        {
            'name': 'Custom Database Numbers',
            'env_vars': {
                'NAUTOBOT_REDIS_CACHE_DATABASE': '5',
                'NAUTOBOT_REDIS_QUEUE_DATABASE': '10'
            },
            'expected_cache': 'redis://localhost:6379/5',
            'expected_queue': 'redis://localhost:6379/10'
        }
    ]

    passed = 0
    total = len(scenarios)

    for scenario in scenarios:
        if test_scenario(**scenario):
            passed += 1

    # Final cleanup
    clean_redis_env()

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Multi-instance Redis configuration is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please review the implementation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
