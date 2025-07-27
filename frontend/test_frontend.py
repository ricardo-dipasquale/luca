#!/usr/bin/env python3
"""
Test script for LUCA Frontend components.

This script tests the basic functionality of auth, chat, and utils modules.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_auth():
    """Test authentication functionality."""
    print("🔐 Testing Authentication...")
    
    try:
        from auth import authenticate_user, get_user_conversations, create_conversation
        
        # Test authentication with test user
        user = authenticate_user("visitante@uca.edu.ar", "visitante!")
        if user:
            print(f"✅ Authentication successful: {user.get('email')}")
        else:
            print("❌ Authentication failed")
            return False
            
        # Test conversation loading
        conversations = get_user_conversations("visitante@uca.edu.ar")
        print(f"✅ Loaded {len(conversations)} conversations")
        
        # Test conversation creation
        conv_id = create_conversation(
            "visitante@uca.edu.ar", 
            "Test Conversation", 
            "Bases de Datos Relacionales"
        )
        if conv_id:
            print(f"✅ Created conversation: {conv_id}")
        else:
            print("❌ Failed to create conversation")
            
        return True
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return False

def test_utils():
    """Test utility functions."""
    print("\n🛠 Testing Utilities...")
    
    try:
        from utils import get_subjects_from_kg, format_timestamp, validate_email
        
        # Test subject loading
        subjects = get_subjects_from_kg()
        print(f"✅ Loaded {len(subjects)} subjects: {subjects[:3]}...")
        
        # Test email validation
        valid_email = validate_email("test@uca.edu.ar")
        invalid_email = validate_email("test@gmail.com")
        
        if valid_email and not invalid_email:
            print("✅ Email validation working correctly")
        else:
            print("❌ Email validation failed")
            
        # Test timestamp formatting
        from datetime import datetime
        formatted = format_timestamp(datetime.now())
        print(f"✅ Timestamp formatting: {formatted}")
        
        return True
        
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app initialization."""
    print("\n🌐 Testing Flask App...")
    
    try:
        from flask_app import app
        
        # Test app configuration
        print("✅ Flask app imported successfully")
        print(f"✅ App configured with secret key: {'Yes' if app.secret_key else 'No'}")
        
        # Test if routes are registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/login', '/logout', '/chat', '/conversations', '/subjects']
        
        missing_routes = [route for route in expected_routes if route not in routes]
        if not missing_routes:
            print("✅ All expected routes registered")
        else:
            print(f"❌ Missing routes: {missing_routes}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def test_neo4j_connection():
    """Test Neo4j connection and user data."""
    print("\n🗄 Testing Neo4j Connection...")
    
    try:
        from kg.connection import KGConnection
        
        kg_connection = KGConnection()
        
        # Test basic query
        result = kg_connection.execute_query(
            "MATCH (u:Usuario {email: $email}) RETURN u.email as email",
            {"email": "visitante@uca.edu.ar"}
        )
        
        if result:
            print(f"✅ Neo4j connection successful, found user: {result[0]['email']}")
        else:
            print("❌ User not found in Neo4j")
            
        kg_connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j test failed: {e}")
        return False

def test_dependencies():
    """Test required dependencies."""
    print("\n📦 Testing Dependencies...")
    
    # Test Flask dependencies (required)
    try:
        import flask
        from flask_cors import CORS
        print("✅ Flask and Flask-CORS")
        flask_available = True
    except ImportError as e:
        print(f"❌ Flask dependencies missing: {e}")
        print("💡 Install with: pip install flask flask-cors")
        flask_available = False
    
    # Test other required modules
    required_modules = [
        "asyncio", 
        "aiohttp",
        "neo4j",
        "langchain"
    ]
    
    success = flask_available
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - Missing!")
            success = False
    
    return success

def main():
    """Run all tests."""
    print("🎓 LUCA Frontend Test Suite")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Neo4j Connection", test_neo4j_connection),
        ("Authentication", test_auth),
        ("Utilities", test_utils),
        ("Flask App", test_flask_app)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Flask Frontend is ready to run.")
        print("\nTo start the Flask application:")
        print("  cd frontend")
        print("  python run.py")
        print("  # OR")
        print("  python run_flask.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)