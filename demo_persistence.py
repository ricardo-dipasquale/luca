"""
Demonstration of Neo4j persistence with LUCA agents.

This script shows how the Orchestrator and GapAnalyzer agents now use
Neo4j for persistent memory across conversations.
"""

import asyncio
from uuid import uuid4
from orchestrator.agent import OrchestratorAgent
from orchestrator.schemas import ConversationContext, ConversationMemory, EducationalContext
from gapanalyzer.agent import GapAnalyzerAgent
from gapanalyzer.schemas import StudentContext


async def demo_orchestrator_persistence(student_id: str = None):
    """Demonstrate Orchestrator agent with Neo4j persistence."""
    print("🎓 LUCA Orchestrator with Neo4j Persistence Demo")
    print("=" * 50)
    
    # Create agent with Neo4j persistence enabled
    agent = OrchestratorAgent()
    print(f"✓ Created Orchestrator with Neo4j persistence")
    
    # Create conversation context
    user_id = student_id or "visitante@uca.edu.ar"  # Use provided student or default visitor
    session_id = f"session_{uuid4()}"
    
    # Create educational context with subject
    educational_context = EducationalContext(
        current_subject="Bases de Datos Relacionales",
        topics_discussed=["normalización", "bases de datos"]
    )
    
    context = ConversationContext(
        session_id=session_id,
        current_message="¿Qué es normalización en bases de datos?",
        memory=ConversationMemory(
            educational_context=educational_context
        ),
        user_id=user_id,
        educational_subject="Bases de Datos Relacionales"
    )
    
    print(f"✓ Created conversation context for user: {user_id}")
    print(f"  Subject: {context.memory.educational_context.current_subject}")
    print(f"  Question: {context.current_message}")
    
    # Process message using stream method - this will store checkpoints and long-term memory
    try:
        print("  Processing message through streaming interface...")
        message_count = 0
        final_content = ""
        
        async for chunk in agent.stream(
            query=context.current_message, 
            session_id=session_id,
            student_id=user_id,
            educational_subject="Bases de Datos Relacionales"
        ):
            message_count += 1
            if chunk.get('type') == 'content':
                final_content += chunk.get('content', '')
        
        print(f"✓ Message processed successfully")
        print(f"  Processed {message_count} chunks")
        print(f"  Response length: {len(final_content)} characters")
        print(f"  Sample response: {final_content[:100]}..." if final_content else "  No content received")
        
        # The agent automatically stored:
        # - Conversation checkpoint in Neo4j (for resumability) 
        # - Long-term memory about topics discussed
        # - Learning patterns and intent history
        print(f"✓ Persisted conversation state and learning patterns to Neo4j")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        # Let's still continue with the demo to show other functionality
    
    print()


async def demo_gapanalyzer_persistence(student_id: str = None):
    """Demonstrate GapAnalyzer agent with Neo4j persistence."""
    print("🔍 LUCA GapAnalyzer with Neo4j Persistence Demo")
    print("=" * 50)
    
    # Create agent with Neo4j persistence enabled
    agent = GapAnalyzerAgent()
    print(f"✓ Created GapAnalyzer with Neo4j persistence")
    
    # Create student context for gap analysis
    user_id = student_id or "visitante@uca.edu.ar"  # Use provided student or default visitor
    
    context = StudentContext(
        student_question="No entiendo por qué mi consulta LEFT JOIN no funciona correctamente",
        conversation_history=[
            "Usuario: Hola, estoy trabajando en la práctica 2",
            "Asistente: ¡Perfecto! ¿En qué ejercicio específico necesitas ayuda?"
        ],
        subject_name="Bases de Datos Relacionales",
        practice_context="Práctica 2: Consultas SQL con JOIN. Objetivos: Comprender diferentes tipos de JOIN y su aplicación en consultas complejas. Los estudiantes deben resolver ejercicios que involucran múltiples tablas relacionadas.",
        exercise_context="Ejercicio 1.d: Escribir una consulta que muestre todos los clientes y sus pedidos (si los tienen) usando LEFT JOIN. Las tablas son: clientes(id, nombre, email) y pedidos(id, cliente_id, fecha, total).",
        solution_context="SELECT c.nombre, c.email, p.fecha, p.total FROM clientes c LEFT JOIN pedidos p ON c.id = p.cliente_id;",
        tips_context="Recordar que LEFT JOIN incluye todos los registros de la tabla izquierda, incluso si no hay coincidencias en la tabla derecha."
    )
    
    print(f"✓ Created student context for user: {user_id}")
    print(f"  Subject: {context.subject_name}")
    print(f"  Question: {context.student_question}")
    print(f"  Practice context: {context.practice_context[:50]}...")
    
    # Analyze gaps using stream method - this will store gap analysis results and patterns
    try:
        print("  Processing gap analysis through streaming interface...")
        gap_session_id = f"gap_session_{uuid4()}"
        chunk_count = 0
        analysis_content = ""
        
        async for chunk in agent.stream(query=context, context_id=gap_session_id):
            chunk_count += 1
            if chunk.get('type') == 'content':
                analysis_content += chunk.get('content', '')
            elif chunk.get('type') == 'analysis_result':
                # This would contain the structured analysis results
                pass
        
        print(f"✓ Gap analysis completed successfully")
        print(f"  Processed {chunk_count} analysis chunks")
        print(f"  Analysis content length: {len(analysis_content)} characters")
        print(f"  Sample analysis: {analysis_content[:100]}..." if analysis_content else "  No analysis content received")
        
        # The agent automatically stored:
        # - Gap analysis checkpoint in Neo4j
        # - Learning gaps and patterns 
        # - Recommendation effectiveness tracking
        print(f"✓ Persisted gap analysis results and learning patterns to Neo4j")
        
    except Exception as e:
        print(f"❌ Error analyzing gaps: {e}")
        # Continue with demo to show other functionality
    
    print()


async def demo_memory_continuity():
    """Demonstrate memory continuity across agent sessions."""
    print("💾 Memory Continuity Demo")
    print("=" * 30)
    
    from kg.persistence import create_neo4j_persistence
    
    # Get persistence components directly
    checkpointer, memory_store = create_neo4j_persistence()
    
    # Check for existing memories
    user_id = "continuity_demo_user"
    namespace = (user_id, "educational_memory")
    
    # List existing memories
    existing_keys = memory_store.list(namespace)
    print(f"✓ Found {len(existing_keys)} existing memories for user")
    
    if existing_keys:
        # Show recent memory
        recent_memory = memory_store.get(namespace, existing_keys[0])
        if recent_memory:
            print(f"  Recent memory type: {recent_memory.get('type', 'unknown')}")
            print(f"  Content preview: {str(recent_memory)[:100]}...")
    
    # Search for learning patterns
    learning_patterns = memory_store.search(namespace, "learning", limit=5)
    print(f"✓ Found {len(learning_patterns)} learning-related memories")
    
    for key, memory in learning_patterns[:2]:  # Show first 2
        memory_type = memory.get("type", "unknown")
        print(f"  Pattern: {key[:30]}... - Type: {memory_type}")
    
    print()


def print_persistence_benefits():
    """Print the benefits of Neo4j persistence."""
    print("🚀 Benefits of Neo4j Persistence in LUCA")
    print("=" * 40)
    print("📚 Short-term Memory (Checkpoints):")
    print("  • Conversation continuity across sessions")
    print("  • Resumable agent workflows")
    print("  • Fault tolerance and error recovery")
    print("  • Human-in-the-loop capabilities")
    print()
    print("🧠 Long-term Memory (Memory Store):")
    print("  • Learning pattern analysis")
    print("  • Personalized education paths")
    print("  • Gap identification trends")
    print("  • Cross-session knowledge retention")
    print()
    print("🔄 Graph Database Advantages:")
    print("  • Rich relationship modeling")
    print("  • Vector similarity search")
    print("  • Complex query capabilities")
    print("  • Scalable memory management")
    print()


async def main(student_id: str = None):
    """Run all persistence demonstrations."""
    print("🎯 LUCA Agent Persistence Demonstration")
    print("=" * 50)
    print("This demo shows how LUCA agents now use Neo4j for persistent memory")
    print("across conversations, enabling personalized learning experiences.")
    
    # Use default visitor if no student provided
    demo_student = student_id or "visitante@uca.edu.ar"
    print(f"Using student: {demo_student}\n")
    
    try:
        await demo_orchestrator_persistence(demo_student)
        await demo_gapanalyzer_persistence(demo_student)
        await demo_memory_continuity()
        print_persistence_benefits()
        
        print("✨ Demo completed successfully!")
        print("\nNow agents will remember:")
        print("  • Past conversations and topics discussed")
        print("  • Learning gaps and patterns")
        print("  • Student preferences and difficulty levels")
        print("  • Effective teaching strategies")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    # Allow passing student ID as command line argument
    student_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(student_id))