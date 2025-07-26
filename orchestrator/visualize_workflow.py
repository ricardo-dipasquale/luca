#!/usr/bin/env python3
"""
Workflow Visualization Tool for Orchestrator

This script generates a visual representation of the LangGraph workflow used in the
Orchestrator agent. It exports the graph structure as PNG/JPG images for documentation
and debugging purposes.

Usage:
    python visualize_workflow.py [--format png|jpg] [--output path]
    
Examples:
    python visualize_workflow.py
    python visualize_workflow.py --format jpg --output ./docs/workflow_diagram.jpg
    python -m orchestrator.visualize_workflow --format png
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.workflow import OrchestratorWorkflow
from orchestrator.schemas import ConversationContext, ConversationMemory, EducationalContext


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_context() -> ConversationContext:
    """Create a sample conversation context for workflow visualization."""
    # Create educational context
    educational_context = EducationalContext(
        current_subject="Bases de Datos Relacionales",
        current_practice=2,
        topics_discussed=["SQL", "JOIN", "Algebra Relacional"]
    )
    
    # Create conversation memory
    memory = ConversationMemory(
        session_id="demo_session",
        educational_context=educational_context
    )
    
    return ConversationContext(
        session_id="demo_session", 
        user_id="demo_user",
        current_message="No entiendo por qué mi consulta LEFT JOIN duplica registros en la práctica 2",
        memory=memory
    )


def generate_workflow_visualization(
    output_path: Optional[str] = None,
    format: str = "png",
    verbose: bool = False
) -> str:
    """
    Generate workflow visualization and save to file.
    
    Args:
        output_path: Optional custom output path
        format: Image format (png or jpg)
        verbose: Enable verbose logging
        
    Returns:
        Path to the generated image file
    """
    try:
        logger.info("Initializing Orchestrator workflow...")
        
        # Create workflow instance
        workflow = OrchestratorWorkflow()
        
        logger.info("Workflow initialized successfully")
        logger.info(f"Workflow nodes: {list(workflow.graph.nodes.keys())}")
        
        # Determine output path
        if output_path is None:
            current_dir = Path(__file__).parent
            output_path = current_dir / f"orchestrator_workflow.{format}"
        else:
            output_path = Path(output_path)
            
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating workflow visualization...")
        logger.info(f"Output path: {output_path}")
        
        # Create sample context for the workflow
        sample_context = create_sample_context()
        logger.info("Created sample conversation context for visualization")
        
        try:
            # Try to generate the graph visualization
            if hasattr(workflow.graph, 'get_graph'):
                # For newer versions of langgraph
                graph_representation = workflow.graph.get_graph()
                
                # Try to generate PNG/JPG
                if hasattr(graph_representation, 'draw_mermaid_png'):
                    logger.info("Using draw_mermaid_png method...")
                    image_data = graph_representation.draw_mermaid_png()
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                elif hasattr(graph_representation, 'draw_png'):
                    logger.info("Using draw_png method...")
                    image_data = graph_representation.draw_png()
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                else:
                    # Fallback to mermaid text representation
                    logger.warning("Direct image generation not available, creating mermaid diagram...")
                    mermaid_code = generate_mermaid_diagram(workflow)
                    mermaid_path = output_path.with_suffix('.mmd')
                    with open(mermaid_path, 'w', encoding='utf-8') as f:
                        f.write(mermaid_code)
                    logger.info(f"Mermaid diagram saved to: {mermaid_path}")
                    
                    # Try to convert mermaid to image if mmdc is available
                    try:
                        import subprocess
                        result = subprocess.run(
                            ['mmdc', '-i', str(mermaid_path), '-o', str(output_path)],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0:
                            logger.info("Successfully converted mermaid to image using mmdc")
                        else:
                            logger.warning(f"mmdc conversion failed: {result.stderr}")
                            return str(mermaid_path)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        logger.warning("mmdc not found or timed out. Install with: npm install -g @mermaid-js/mermaid-cli")
                        return str(mermaid_path)
                        
            else:
                logger.warning("get_graph method not available, creating manual diagram...")
                mermaid_code = generate_mermaid_diagram(workflow)
                mermaid_path = output_path.with_suffix('.mmd')
                with open(mermaid_path, 'w', encoding='utf-8') as f:
                    f.write(mermaid_code)
                return str(mermaid_path)
                
        except Exception as viz_error:
            logger.error(f"Direct visualization failed: {viz_error}")
            logger.info("Falling back to manual mermaid diagram generation...")
            
            # Generate manual mermaid diagram
            mermaid_code = generate_mermaid_diagram(workflow)
            mermaid_path = output_path.with_suffix('.mmd')
            with open(mermaid_path, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)
            
            logger.info(f"Mermaid diagram saved to: {mermaid_path}")
            logger.info("To convert to image, install mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
            logger.info(f"Then run: mmdc -i {mermaid_path} -o {output_path}")
            
            return str(mermaid_path)
        
        logger.info(f"Workflow visualization generated successfully: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate workflow visualization: {e}")
        raise


def generate_mermaid_diagram(workflow: OrchestratorWorkflow) -> str:
    """
    Generate a Mermaid diagram representation of the workflow.
    
    Args:
        workflow: The OrchestratorWorkflow instance
        
    Returns:
        Mermaid diagram code as string
    """
    mermaid_code = """graph TD
    %% Orchestrator Workflow - Educational Conversation Management
    
    Start([Input: Student Message + Session Context]) --> A[classify_intent]
    
    A --> A_Decision{Intent Classification}
    A_Decision -->|theoretical_question| H1[handle_theoretical_question]
    A_Decision -->|practical_general| H2[handle_practical_general]
    A_Decision -->|practical_specific| H3[handle_practical_specific]
    A_Decision -->|clarification| H4[handle_clarification]
    A_Decision -->|exploration| H5[handle_exploration]
    A_Decision -->|evaluation| H6[handle_evaluation]
    A_Decision -->|greeting/goodbye| H7[handle_social]
    A_Decision -->|off_topic| H8[handle_off_topic]
    A_Decision -->|error| Error[handle_error]
    
    %% All handlers flow to synthesis
    H1 --> D[synthesize_response]
    H2 --> D
    H3 --> D
    H4 --> D
    H5 --> D
    H6 --> D
    H7 --> D
    H8 --> D
    
    D --> E[update_memory]
    E --> End([Final Orchestrator Response])
    Error --> ErrorEnd([Error Response])
    
    %% Handler Details
    H1 -.-> H1_Agent[Knowledge Retrieval<br/>Theoretical Content]
    H2 -.-> H2_Agent[Knowledge Retrieval<br/>Practical Examples]
    H3 -.-> H3_Agent[GapAnalyzer<br/>Exercise-specific Analysis]
    H4 -.-> H4_Agent[Direct Response<br/>Conversation Context]
    H5 -.-> H5_Agent[Knowledge Retrieval +<br/>Exploratory Guidance]
    H6 -.-> H6_Agent[Direct Response<br/>Assessment Guidance]
    H7 -.-> H7_Agent[Direct Response<br/>Social Interaction]
    H8 -.-> H8_Agent[Clarification<br/>Educational Redirection]
    
    %% Styling
    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef handler fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef agent fill:#f1f8e9,stroke:#558b2f,stroke-width:1px,stroke-dasharray: 3 3
    
    class Start,End,ErrorEnd startEnd
    class A,D,E process
    class A_Decision decision
    class Error error
    class H1,H2,H3,H4,H5,H6,H7,H8 handler
    class H1_Agent,H2_Agent,H3_Agent,H4_Agent,H5_Agent,H6_Agent,H7_Agent,H8_Agent agent
    
    %% Node descriptions
    A -.->|"Analiza mensaje del estudiante<br/>Clasifica intención educativa<br/>Rutea directamente a handler"| A_Note[🎯 Intent Classification & Routing]
    D -.->|"Combina respuestas de handlers<br/>Crea respuesta educativa coherente<br/>Incluye orientación pedagógica"| D_Note[🔄 Response Synthesis]
    E -.->|"Actualiza memoria de conversación<br/>Mantiene contexto educativo<br/>Genera respuesta final"| E_Note[💾 Memory Update]
    
    H1 -.->|"Handler para preguntas teóricas<br/>Usa knowledge retrieval"| H1_Note[📚 Theoretical Handler]
    H2 -.->|"Handler para prácticas generales<br/>Usa knowledge retrieval con ejemplos"| H2_Note[🔧 Practical General Handler]
    H3 -.->|"Handler para ejercicios específicos<br/>Usa GapAnalyzer para análisis detallado"| H3_Note[🔍 Practical Specific Handler]
    H4 -.->|"Handler para clarificaciones<br/>Usa contexto de conversación"| H4_Note[💬 Clarification Handler]
    
    classDef note fill:#f8f9fa,stroke:#6c757d,stroke-width:1px,stroke-dasharray: 5 5
    class A_Note,D_Note,E_Note,H1_Note,H2_Note,H3_Note,H4_Note note
"""
    
    return mermaid_code


def print_workflow_info(workflow: OrchestratorWorkflow):
    """Print detailed information about the workflow structure."""
    print("\n" + "="*60)
    print("ORCHESTRATOR WORKFLOW INFORMATION")
    print("="*60)
    
    print(f"\n📊 WORKFLOW OVERVIEW:")
    print(f"   • Type: LangGraph StateGraph")
    print(f"   • State Model: WorkflowState (Pydantic)")
    print(f"   • Checkpointer: MemorySaver (for conversation continuity)")
    print(f"   • LLM: Observed LLM with Langfuse integration")
    print(f"   • Purpose: Educational conversation orchestration and multi-agent coordination")
    
    if hasattr(workflow.graph, 'nodes'):
        print(f"\n🔄 WORKFLOW NODES ({len(workflow.graph.nodes)}):")
        for i, node_name in enumerate(workflow.graph.nodes.keys(), 1):
            print(f"   {i}. {node_name}")
    
    print(f"\n➡️  WORKFLOW FLOW:")
    print(f"   1. classify_intent               → Analyzes student message and classifies educational intent")
    print(f"   2. handle_[intent_type]          → Intent-specific handlers (8 different handlers)")
    print(f"   3. synthesize_response           → Combines handler responses into coherent educational response")
    print(f"   4. update_memory                 → Updates conversation memory and educational context")
    print(f"   5. handle_error                  → Handles any workflow errors with educational fallbacks")
    print(f"\n🎯 INTENT-SPECIFIC HANDLERS:")
    print(f"   • handle_theoretical_question    → Knowledge retrieval for concepts and theory")
    print(f"   • handle_practical_general       → Knowledge retrieval for general practical questions")
    print(f"   • handle_practical_specific      → GapAnalyzer for specific exercise help")
    print(f"   • handle_clarification           → Direct response with conversation context")
    print(f"   • handle_exploration             → Knowledge retrieval + exploratory guidance")
    print(f"   • handle_evaluation              → Direct response with assessment guidance")
    print(f"   • handle_social                  → Direct response for greetings/goodbyes")
    print(f"   • handle_off_topic               → Clarification with educational redirection")
    
    print(f"\n🎯 INTENT CLASSIFICATION:")
    print(f"   • theoretical_question  → Conceptual questions requiring knowledge retrieval")
    print(f"   • practical_general     → General practical questions not tied to specific KG exercise")
    print(f"   • practical_specific    → Specific exercise/practice help mapped in KG requiring gap analysis")
    print(f"   • clarification         → Follow-up questions about previous responses")
    print(f"   • exploration           → Curious questions about related topics")
    print(f"   • evaluation            → Self-assessment and knowledge validation")
    print(f"   • greeting/goodbye      → Social interactions")
    print(f"   • off_topic            → Non-educational content requiring redirection")
    
    print(f"\n🤖 SPECIALIZED AGENTS:")
    print(f"   • gap_analyzer          → Educational gap analysis and learning assessment")
    print(f"   • knowledge_retrieval   → Knowledge graph search and theoretical content")
    print(f"   • direct_response       → Simple responses and social interactions")
    print(f"   • clarification         → Request clarification or redirect to education")
    
    print(f"\n🔀 CONDITIONAL LOGIC:")
    print(f"   • Intent classification → Route based on student needs and confidence")
    print(f"   • Agent routing         → Select optimal agent for specific intents")
    print(f"   • Error handling        → Robust error recovery with educational guidance")
    print(f"   • Context management    → Maintain educational conversation continuity")
    
    print(f"\n📈 FEATURES:")
    print(f"   • Multi-agent coordination with specialized educational roles")
    print(f"   • Intent-based routing for optimal educational assistance")
    print(f"   • Conversation memory with educational context persistence")
    print(f"   • Response synthesis from multiple knowledge sources")
    print(f"   • Full observability with Langfuse integration")
    print(f"   • Thread-based conversation continuity")
    print(f"   • Educational guidance and next steps suggestions")
    
    print(f"\n🎯 INPUT/OUTPUT:")
    print(f"   Input:  ConversationContext (message + session + memory)")
    print(f"   Output: OrchestratorResponse (synthesized response + educational guidance)")
    
    print(f"\n💾 MEMORY MANAGEMENT:")
    print(f"   • Session-based conversation tracking")
    print(f"   • Educational context (subject, practice, topics)")
    print(f"   • Intent and routing history")
    print(f"   • Multi-turn conversation support")


def main():
    """Main entry point for the visualization tool."""
    parser = argparse.ArgumentParser(
        description="Generate visual representation of Orchestrator workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python visualize_workflow.py
    python visualize_workflow.py --format jpg --output ./docs/
    python visualize_workflow.py --verbose --info-only
    python -m orchestrator.visualize_workflow --format png
        """
    )
    
    parser.add_argument(
        '--format', 
        choices=['png', 'jpg'], 
        default='png',
        help='Output image format (default: png)'
    )
    
    parser.add_argument(
        '--output', 
        type=str,
        help='Output file path (default: ./orchestrator_workflow.{format})'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--info-only',
        action='store_true', 
        help='Only print workflow information, do not generate visualization'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        logger.info("Starting Orchestrator workflow visualization...")
        
        # Create workflow instance
        workflow = OrchestratorWorkflow()
        
        # Print workflow information
        print_workflow_info(workflow)
        
        if args.info_only:
            logger.info("Info-only mode completed")
            return
        
        # Generate visualization
        output_path = generate_workflow_visualization(
            output_path=args.output,
            format=args.format,
            verbose=args.verbose
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"   Workflow visualization saved to: {output_path}")
        
        if output_path.endswith('.mmd'):
            print(f"\n💡 TIP: Install mermaid-cli to convert to image:")
            print(f"   npm install -g @mermaid-js/mermaid-cli")
            print(f"   mmdc -i {output_path} -o {output_path.replace('.mmd', f'.{args.format}')}")
        
    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()