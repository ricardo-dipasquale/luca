#!/usr/bin/env python3
"""
Workflow Visualization Tool for GapAnalyzer

This script generates a visual representation of the LangGraph workflow used in the
GapAnalyzer agent. It exports the graph structure as PNG/JPG images for documentation
and debugging purposes.

Usage:
    python visualize_workflow.py [--format png|jpg] [--output path]
    
Examples:
    python visualize_workflow.py
    python visualize_workflow.py --format jpg --output ./docs/workflow_diagram.jpg
    python -m gapanalyzer.visualize_workflow --format png
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gapanalyzer.workflow import GapAnalysisWorkflow
from gapanalyzer.schemas import StudentContext


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_context() -> StudentContext:
    """Create a sample student context for workflow visualization."""
    return StudentContext(
        student_question="No entiendo por qué mi consulta SQL con LEFT JOIN no funciona correctamente",
        conversation_history=[],
        subject_name="Bases de Datos Relacionales",
        practice_context="""
        Práctica: 2 - Algebra Relacional: Resolución de ejercicios en Algebra Relacional.
        
        Objetivo: Que los alumnos sean capaces de resolver situaciones problemáticas 
        con álgebra relacional utilizando los preceptos dados en clase.
        
        Temas cubiertos:
        - Modelo Relacional
        - Algebra relacional: Operaciones, Práctica
        - Lenguajes relacionalmente completos
        - Consultas Algebra relacional
        """,
        exercise_context="""
        Ejercicio: 1.d - Nombre de los clientes que no han comprado nada
        
        Enunciado: Dado el siguiente esquema relacional de base de datos, resolver en álgebra relacional.
        Las claves se denotan con "(clave)":
        - CLIENTES (Nº Cliente (clave), Nombre, Dirección, Teléfono, Ciudad)
        - PRODUCTO(Cod Producto (clave), Descripción, Precio)
        - VENTA(Cod Producto, Nº Cliente, Cantidad, Id Venta (clave))
        """,
        solution_context="""
        Solución esperada: [π_{Nombre} (π_{Nº Cliente,Nombre} (CLIENTES) − π_{Nº Cliente,Nombre} 
        (CLIENTES ⋈_{CLIENTES.Nº Cliente=VENTA.Nº Cliente} VENTA))]
        """,
        tips_context="""
        Tips nivel práctica:
        - Pensar bien qué operación (o juego de operaciones) es central en la resolución del ejercicio.
        - No confundir la semántica de las operaciones.
        
        Tips nivel ejercicio:
        - Tener en cuenta que puede haber varias respuestas similares y están bien
        - Los alumnos tienden a simplificar y a hacer una diferencia de conjuntos utilizando únicamente 
        la proyección por el nombre del cliente.
        """
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
        logger.info("Initializing GapAnalysis workflow...")
        
        # Create workflow instance
        workflow = GapAnalysisWorkflow()
        
        logger.info("Workflow initialized successfully")
        logger.info(f"Workflow nodes: {list(workflow.graph.nodes.keys())}")
        
        # Determine output path
        if output_path is None:
            current_dir = Path(__file__).parent
            output_path = current_dir / f"gap_analysis_workflow.{format}"
        else:
            output_path = Path(output_path)
            
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating workflow visualization...")
        logger.info(f"Output path: {output_path}")
        
        # Create sample context for the workflow
        sample_context = create_sample_context()
        logger.info("Created sample student context for visualization")
        
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


def generate_mermaid_diagram(workflow: GapAnalysisWorkflow) -> str:
    """
    Generate a Mermaid diagram representation of the workflow.
    
    Args:
        workflow: The GapAnalysisWorkflow instance
        
    Returns:
        Mermaid diagram code as string
    """
    mermaid_code = """graph TD
    %% GapAnalyzer Workflow - Educational Gap Analysis
    
    Start([Input: Student Question + Context]) --> A[validate_context]
    
    A --> A_Decision{Context Valid?}
    A_Decision -->|No| Error[handle_error]
    A_Decision -->|Yes| B[analyze_gaps]
    
    B --> C[evaluate_gaps]
    C --> D[prioritize_gaps]
    
    D --> D_Decision{Should Do Feedback?}
    D_Decision -->|No| F[generate_response]
    D_Decision -->|Yes| E[feedback_analysis]
    D_Decision -->|Error| Error
    
    E --> E_Decision{Feedback Decision}
    E_Decision -->|Retry| B
    E_Decision -->|Complete| F
    E_Decision -->|Error| Error
    
    F --> End([Final Gap Analysis Result])
    Error --> ErrorEnd([Error Response])
    
    %% Styling
    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class Start,End,ErrorEnd startEnd
    class A,B,C,D,E,F process
    class A_Decision,D_Decision,E_Decision decision
    class Error error
    
    %% Node descriptions
    A -.->|"Valida contexto educativo<br/>Determina si necesita teoría adicional"| A_Note[📋 Context Validation]
    B -.->|"Identifica gaps específicos<br/>usando LLM con contexto completo"| B_Note[🔍 Gap Identification]
    C -.->|"Evalúa relevancia pedagógica<br/>e impacto en el aprendizaje"| C_Note[⚖️ Gap Evaluation]
    D -.->|"Prioriza gaps y genera<br/>recomendaciones específicas"| D_Note[📊 Gap Prioritization]
    E -.->|"Analiza calidad del análisis<br/>y determina si necesita iteración"| E_Note[🔄 Feedback Analysis]
    F -.->|"Crea respuesta estructurada<br/>con gaps priorizados y recomendaciones"| F_Note[📝 Response Generation]
    
    classDef note fill:#f8f9fa,stroke:#6c757d,stroke-width:1px,stroke-dasharray: 5 5
    class A_Note,B_Note,C_Note,D_Note,E_Note,F_Note note
"""
    
    return mermaid_code


def print_workflow_info(workflow: GapAnalysisWorkflow):
    """Print detailed information about the workflow structure."""
    print("\n" + "="*60)
    print("GAPANALYZER WORKFLOW INFORMATION")
    print("="*60)
    
    print(f"\n📊 WORKFLOW OVERVIEW:")
    print(f"   • Type: LangGraph StateGraph")
    print(f"   • State Model: WorkflowState (Pydantic)")
    print(f"   • Checkpointer: MemorySaver (for conversation continuity)")
    print(f"   • LLM: Observed LLM with Langfuse integration")
    
    if hasattr(workflow.graph, 'nodes'):
        print(f"\n🔄 WORKFLOW NODES ({len(workflow.graph.nodes)}):")
        for i, node_name in enumerate(workflow.graph.nodes.keys(), 1):
            print(f"   {i}. {node_name}")
    
    print(f"\n➡️  WORKFLOW FLOW:")
    print(f"   1. validate_context    → Validates educational context")
    print(f"   2. analyze_gaps        → Identifies learning gaps using LLM")
    print(f"   3. evaluate_gaps       → Evaluates pedagogical relevance")
    print(f"   4. prioritize_gaps     → Ranks gaps and generates recommendations")
    print(f"   5. feedback_analysis   → (Optional) Improves analysis quality")
    print(f"   6. generate_response   → Creates final structured response")
    print(f"   7. handle_error        → Handles any workflow errors")
    
    print(f"\n🔀 CONDITIONAL LOGIC:")
    print(f"   • Context validation → Continue or handle error")
    print(f"   • Feedback loop      → Based on confidence and iteration count") 
    print(f"   • Error handling     → Robust error recovery")
    
    print(f"\n📈 FEATURES:")
    print(f"   • Multi-iteration feedback for quality improvement")
    print(f"   • Structured gap analysis with severity and category")
    print(f"   • Pedagogical evaluation with confidence scoring")
    print(f"   • Specific actionable recommendations")
    print(f"   • Full observability with Langfuse integration")
    print(f"   • Conversation continuity with thread management")
    
    print(f"\n🎯 INPUT/OUTPUT:")
    print(f"   Input:  StudentContext (question + educational context)")
    print(f"   Output: GapAnalysisResult (prioritized gaps + recommendations)")


def main():
    """Main entry point for the visualization tool."""
    parser = argparse.ArgumentParser(
        description="Generate visual representation of GapAnalyzer workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python visualize_workflow.py
    python visualize_workflow.py --format jpg --output ./docs/
    python visualize_workflow.py --verbose --info-only
    python -m gapanalyzer.visualize_workflow --format png
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
        help='Output file path (default: ./gap_analysis_workflow.{format})'
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
        logger.info("Starting GapAnalyzer workflow visualization...")
        
        # Create workflow instance
        workflow = GapAnalysisWorkflow()
        
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