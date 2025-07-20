"""
Local runner for GapAnalyzer agent debugging.

This script allows running the GapAnalyzer agent locally without the A2A framework
for debugging and development purposes. It takes a student question along with
practice and exercise identifiers to build a complete educational context from
the knowledge graph.
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional
from uuid import uuid4

from gapanalyzer.agent import GapAnalyzerAgent
from gapanalyzer.schemas import StudentContext
from kg import KGConnection, KGQueryInterface


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalGapAnalyzerRunner:
    """Local runner for debugging the GapAnalyzer agent."""
    
    def __init__(self):
        """Initialize the local runner."""
        try:
            self.agent = GapAnalyzerAgent()
            self.context_id = str(uuid4())
            # Initialize KG interface for data retrieval
            self.kg_connection = KGConnection()
            self.kg_interface = KGQueryInterface(self.kg_connection)
            logger.info("GapAnalyzer agent and KG interface initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent or KG interface: {e}")
            raise
    
    def close(self):
        """Close KG connection and cleanup resources."""
        try:
            if hasattr(self, 'kg_connection'):
                self.kg_connection.close()
                logger.info("KG connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing KG connection: {e}")
    
    def create_context_from_kg(self, question: str, practice_number: int, section_number: str, exercise_identifier: str) -> StudentContext:
        """
        Create a StudentContext using knowledge graph data.
        
        Args:
            question: Student's question
            practice_number: Practice number
            section_number: Section number (string, e.g., "1", "2")  
            exercise_identifier: Exercise identifier (string, e.g., 'd', 'a', 'b')
            
        Returns:
            StudentContext built from knowledge graph data
        """
        try:
            # Get practice details
            practice_details = self.kg_interface.get_practice_details(practice_number)
            if not practice_details:
                raise ValueError(f"Practice {practice_number} not found in knowledge graph")
            
            # Get exercise details
            exercise_details = self.kg_interface.get_exercise_details(practice_number, section_number, exercise_identifier)
            if not exercise_details:
                raise ValueError(f"Exercise {practice_number}.{section_number}.{exercise_identifier} not found in knowledge graph")
            
            # Get tips for the specific practice, section, and exercise
            practice_tips = self.kg_interface.get_practice_tips(practice_number, section_number, exercise_identifier)
            
            # Build subject name from practice details
            subject_name = practice_details["subjects"][0] if practice_details["subjects"] else "Materia Desconocida"
            
            # Build practice context
            practice_context_parts = []
            practice_context_parts.append(f"Práctica: {practice_details['number']} - {practice_details['name']}")
            if practice_details["description"]:
                practice_context_parts.append(f"Descripción: {practice_details['description']}")
            if practice_details["objectives"]:
                practice_context_parts.append(f"Objetivos: {practice_details['objectives']}")
            if practice_details["topics"]:
                practice_context_parts.append(f"Temas cubiertos: {', '.join(practice_details['topics'])}")
            
            practice_context = "\n\n".join(practice_context_parts)
            
            # Build exercise context
            exercise_context_parts = []
            exercise_context_parts.append(f"Ejercicio: {exercise_details['section_number']}.{exercise_details['exercise_number']}")
            exercise_context_parts.append(f"Sección: {exercise_details['section_statement']}")
            exercise_context_parts.append(f"Enunciado: {exercise_details['exercise_statement']}")
            
            exercise_context = "\n\n".join(exercise_context_parts)
            
            # Build solution context from exercise answers
            solution_context = ""
            if exercise_details["answers"]:
                solution_context = f"Soluciones esperadas:\n" + "\n".join([f"- {answer}" for answer in exercise_details["answers"]])
            else:
                solution_context = "No se encontraron soluciones en el grafo de conocimiento"
            
            # Build tips context
            tips_context_parts = []
            if practice_tips:
                # Group tips by level
                practice_level_tips = [tip for tip in practice_tips if tip["level"] == "practice"]
                section_level_tips = [tip for tip in practice_tips if tip["level"] == "section" and tip["section_number"] == section_number]
                exercise_level_tips = [tip for tip in practice_tips if tip["level"] == "exercise" and 
                                     tip["section_number"] == section_number and str(tip["exercise_number"]) == exercise_identifier]
                
                if practice_level_tips:
                    tips_context_parts.append("Tips nivel práctica:")
                    for tip in practice_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
                
                if section_level_tips:
                    tips_context_parts.append(f"\nTips nivel sección {section_number}:")
                    for tip in section_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
                
                if exercise_level_tips:
                    tips_context_parts.append(f"\nTips nivel ejercicio {section_number}.{exercise_identifier}:")
                    for tip in exercise_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
            
            tips_context = "\n".join(tips_context_parts) if tips_context_parts else "No se encontraron tips específicos para este ejercicio"
            
            logger.info(f"Successfully built context from KG for practice {practice_number}, exercise {section_number}.{exercise_identifier}")
            
            return StudentContext(
                student_question=question,
                conversation_history=[],
                subject_name=subject_name,
                practice_context=practice_context,
                exercise_context=exercise_context,
                solution_context=solution_context,
                tips_context=tips_context
            )
            
        except Exception as e:
            logger.error(f"Failed to create context from KG: {e}")
            # Fallback to a basic context
            return StudentContext(
                student_question=question,
                conversation_history=[],
                subject_name="Materia Desconocida",
                practice_context=f"Error: No se pudo cargar el contexto de la práctica {practice_number}",
                exercise_context=f"Error: No se pudo cargar el contexto del ejercicio {section_number}.{exercise_identifier}",
                solution_context="Error: No se pudieron cargar las soluciones",
                tips_context="Error: No se pudieron cargar los tips"
            )
    
    
    async def run_analysis(self, context: StudentContext, stream: bool = True) -> Dict[str, Any]:
        """
        Run gap analysis with the given context.
        
        Args:
            context: Student context for analysis
            stream: Whether to show streaming output
            
        Returns:
            Final analysis result
        """
        print(f"\n=== INICIANDO ANÁLISIS DE GAPS ===")
        print(f"Pregunta: {context.student_question}")
        print(f"Materia: {context.subject_name}")
        print("=" * 50)
        
        if stream:
            print("\n=== PROGRESO DEL ANÁLISIS ===")
            final_result = None
            
            async for chunk in self.agent.stream(context, self.context_id):
                if chunk.get('is_task_complete', False):
                    final_result = chunk
                    print(f"\n✅ {chunk.get('content', 'Análisis completado')}")
                else:
                    print(f"🔄 {chunk.get('content', 'Procesando...')}")
            
            return final_result
        else:
            # Non-streaming analysis (direct workflow call)
            result = await self.agent.workflow.run_analysis(context, self.context_id)
            formatted_response = self.agent.format_gap_analysis_response(result)
            
            return {
                'is_task_complete': True,
                'content': formatted_response,
                'structured_response': result
            }
    
    def print_result(self, result: Dict[str, Any]):
        """
        Print the analysis result in a formatted way.
        
        Args:
            result: Analysis result from the agent
        """
        print("\n" + "=" * 60)
        print("RESULTADO DEL ANÁLISIS")
        print("=" * 60)
        
        content = result.get('content', 'No se pudo obtener resultado')
        print(content)
        
        # Print structured response if available
        structured = result.get('structured_response')
        if structured and hasattr(structured, 'detailed_analysis'):
            analysis = structured.detailed_analysis
            print(f"\n📊 ESTADÍSTICAS:")
            print(f"   • Gaps encontrados: {len(analysis.identified_gaps)}")
            print(f"   • Confianza: {analysis.confidence_score:.1%}")
            print(f"   • Iteraciones de feedback: {getattr(analysis, 'feedback_iterations', 0)}")
            print("-------------------------")
            print(f"\n Summary: {structured.detailed_analysis.summary}")
            if structured.detailed_analysis.educational_context:
                print(f"\n Contexto Educativo/Teórico: {structured.detailed_analysis.educational_context}")
            if structured.detailed_analysis.identified_gaps:
                print("\nGaps identificados:")
                for gap in structured.detailed_analysis.identified_gaps:
                    print(f"  - {gap.title}: {gap.description}")
                    print(f"    Categoría: {gap.category.value} | Severidad: {gap.severity.value}")
                    if gap.evidence:
                        print(f"    Evidencia: {gap.evidence}")
                    if gap.affected_concepts:
                        print(f"    Conceptos afectados: {', '.join(gap.affected_concepts)}")
                    print()

            if structured.detailed_analysis.prioritized_gaps:
                print("\nGaps priorizados:")
                for pg in structured.detailed_analysis.prioritized_gaps:
                    gap = pg.gap
                    eval = pg.evaluation
                    
                    print(f"  - {gap.title}: {gap.description}")
                    print(f"    Categoría: {gap.category.value} | Severidad: {gap.severity.value} | Rank: {pg.rank}")
                    print(f"    Prioridad: {eval.priority_score:.2f} | Relevancia pedagógica: {eval.pedagogical_relevance:.2f}")
                    if gap.evidence:
                        print(f"    Evidencia: {gap.evidence}")
                    if gap.affected_concepts:
                        print(f"    Conceptos afectados: {', '.join(gap.affected_concepts)}")
                    print()
            if hasattr(structured.detailed_analysis, 'recommendations') and structured.detailed_analysis.recommendations:
                print("\nRecomendaciones generales:")
                for action in structured.detailed_analysis.recommendations:
                    print(f"  - {action}")
            


def parse_exercise_code(exercise_code: str) -> tuple[int, str]:
    """
    Parse exercise code in format S.E (section.exercise).
    
    Args:
        exercise_code: Exercise code like "1.d" or "2.a"
        
    Returns:
        Tuple of (section_number, exercise_identifier)
        where section_number is str and exercise_identifier is string
        
    Raises:
        ValueError: If the format is invalid
    """
    try:
        parts = exercise_code.split('.')
        if len(parts) != 2:
            raise ValueError("Exercise code must be in format S.E (e.g., '1.d', '2.a')")
        
        section_number = parts[0]  # Keep as string
        exercise_identifier = parts[1].strip()
        
        if not exercise_identifier:
            raise ValueError("Exercise identifier cannot be empty")
        
        return section_number, exercise_identifier
    except ValueError as e:
        if "invalid literal for int()" in str(e):
            raise ValueError(f"Section number must be an integer in exercise code '{exercise_code}'")
        raise ValueError(f"Invalid exercise code '{exercise_code}': {e}")


async def main():
    """Main entry point for the local runner."""
    try:
        # Check if required arguments were provided
        if len(sys.argv) < 3:
            print_help()
            sys.exit(1)
        
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print_help()
            return
        
        # Parse arguments
        practice_code = sys.argv[1]
        exercise_code = sys.argv[2]
        question = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        
        if not question:
            print("❌ Error: Se requiere una pregunta")
            print_help()
            sys.exit(1)
        
        # Parse practice and exercise codes
        try:
            practice_number = int(practice_code)
        except ValueError:
            print(f"❌ Error: Código de práctica inválido '{practice_code}'. Debe ser un número entero.")
            sys.exit(1)
        
        try:
            section_num, exercise_id = parse_exercise_code(exercise_code)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        
        # Initialize runner and create context from KG
        print(f"🔍 Inicializando análisis para práctica {practice_number}, ejercicio {exercise_code}")
        print(f"📝 Pregunta: {question}")
        print("-" * 50)
        
        runner = None
        try:
            runner = LocalGapAnalyzerRunner()
            context = runner.create_context_from_kg(question, practice_number, section_num, exercise_id)
            result = await runner.run_analysis(context)
            runner.print_result(result)
        finally:
            if runner:
                runner.close()
            
    except KeyboardInterrupt:
        print("\n\n👋 Análisis interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en el runner local: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def print_help():
    """Print help information."""
    print("""
🔍 GapAnalyzer Local Runner - Herramienta de debugging

USAGE:
    python -m gapanalyzer.local_runner PRACTICE_NUMBER EXERCISE_CODE "QUESTION"

ARGUMENTS:
    PRACTICE_NUMBER     Número de la práctica (ej: 2)
    EXERCISE_CODE       Código del ejercicio en formato S.E (ej: 1.d)
    QUESTION           Pregunta del estudiante (entre comillas)

OPTIONS:
    -h, --help          Muestra esta ayuda

EXAMPLES:
    # Análisis para práctica 2, ejercicio 1.d
    python -m gapanalyzer.local_runner 2 1.d "¿Cómo funciona un LEFT JOIN?"
    
    # Análisis para práctica 1, ejercicio 2.a
    python -m gapanalyzer.local_runner 1 2.a "No entiendo la normalización de esta tabla"

FORMATO DE CÓDIGOS:
    • PRACTICE_NUMBER: Número entero (ej: 1, 2, 3)
    • EXERCISE_CODE: Formato S.E donde:
      - S = Número de sección (entero)
      - E = Identificador de ejercicio (string)
      (ej: 1.d = Sección 1, Ejercicio d)

CARACTERÍSTICAS:
    • Debugging local sin framework A2A
    • Streaming de progreso en tiempo real
    • Contexto cargado automáticamente desde knowledge graph
    • Análisis completo de gaps educativos con contexto real
    • Integración con observabilidad Langfuse
    """)


if __name__ == "__main__":
    asyncio.run(main())