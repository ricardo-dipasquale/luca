#!/usr/bin/env python3
"""
Debug version of LUCA Frontend to test orchestrator integration.
"""

import streamlit as st
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chat import get_orchestrator_client

st.set_page_config(page_title="LUCA Debug", layout="wide")

st.title("🔍 LUCA Frontend Debug")

# Test message input
test_message = st.text_area(
    "Test message:",
    value="No entiendo el ejercicio 1.d de la práctica 2 sobre LEFT JOIN",
    height=100
)

subject = st.selectbox(
    "Subject:",
    ["Bases de Datos Relacionales", "Otra Materia"]
)

if st.button("Test Orchestrator"):
    st.write("🚀 Starting test...")
    
    try:
        # Create client
        client = get_orchestrator_client()
        st.write("✅ Client created")
        
        # Test streaming
        progress = st.empty()
        result_container = st.empty()
        
        async def test_streaming():
            chunks = []
            try:
                async for chunk in client.stream_message(
                    test_message,
                    "debug_session",
                    subject
                ):
                    chunks.append(chunk)
                    progress.write(f"📦 Chunk {len(chunks)}: {chunk.get('content', 'No content')[:100]}...")
                    
                    if chunk.get('is_task_complete'):
                        result_container.success("✅ Complete!")
                        result_container.write(f"**Final response:** {chunk.get('content', 'No content')}")
                        break
                        
                return chunks
            except Exception as e:
                st.error(f"Error in streaming: {e}")
                return []
        
        # Run async function
        chunks = asyncio.run(test_streaming())
        
        st.write(f"📊 Total chunks received: {len(chunks)}")
        
        # Show all chunks
        with st.expander("All chunks"):
            for i, chunk in enumerate(chunks):
                st.json({f"chunk_{i}": chunk})
                
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# Direct test
st.markdown("---")
st.markdown("### 🧪 Direct Test")

if st.button("Direct Orchestrator Test"):
    try:
        from orchestrator.agent_executor import OrchestratorAgentExecutor
        
        executor = OrchestratorAgentExecutor()
        st.write("✅ Direct executor created")
        
        async def direct_test():
            chunks = []
            async for chunk in executor.stream(
                request={'message': test_message},
                context={
                    'session_id': 'debug_direct',
                    'user_id': 'debug_user',
                    'educational_subject': subject
                }
            ):
                chunks.append(chunk)
                st.write(f"Direct chunk: {chunk.get('content', 'No content')[:100]}...")
                if chunk.get('is_task_complete'):
                    break
            return chunks
        
        chunks = asyncio.run(direct_test())
        st.success(f"✅ Direct test completed with {len(chunks)} chunks")
        
    except Exception as e:
        st.error(f"Direct test error: {e}")
        import traceback
        st.code(traceback.format_exc())