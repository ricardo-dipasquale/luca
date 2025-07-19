"""
Local runner for GapAnalyzer agent debugging.

This script allows running the GapAnalyzer agent locally without the A2A framework
for debugging and development purposes. It provides a simple CLI interface to
interact with the agent directly.
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional
from uuid import uuid4

from gapanalyzer.agent import GapAnalyzerAgent
from gapanalyzer.schemas import StudentContext


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
            logger.info("GapAnalyzer agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    def create_sample_context(self, question: str) -> StudentContext:
        """
        Create a sample context for testing.
        
        Args:
            question: Student's question
            
        Returns:
            StudentContext with sample data
        """
        return StudentContext(
            student_question=question,
            conversation_history=[],
            subject_name="Bases de Datos Relacionales",
            practice_context="""
            Práctica: 2 - Algebra Relacional: Resolución de ejercicios en Algebra Relacional. Existen preguntas conceptuales que están relacionados.
            
            Objetivo: Que los alumnos sean capaces de resolver situaciones problemáticas con álgebra relacional utilizando los preceptos dados en clase.
            
            Temas cubiertos:
            - Modelo Relacional
            - Algebra relacional: Operaciones, Práctica
            - Lenguajes relacionalmente completos
            - Consultas Algebra relacional
            """,
            exercise_context="""
            Ejercicio: 1.d - Nombre de los clientes que no han comprado nada
            
            Enunciado: Dado el siguiente esquema relacional de base de datos, resolver en álgebra relacional. Las claves de denotan con "(clave)":
            - CLIENTES (Nº Cliente (clave), Nombre, Dirección, Teléfono, Ciudad)
            - PRODUCTO(Cod Producto (clave), Descripción, Precio)
            - VENTA(Cod Producto, Nº Cliente, Cantidad, Id Venta (clave))
            """,
            solution_context="""
            Solución esperada: [π_{Nombre} (π_{Nº Cliente,Nombre} (CLIENTES) − π_{Nº Cliente,Nombre} (CLIENTES ⋈_{CLIENTES.Nº Cliente=VENTA.Nº Cliente} VENTA))]
            """,
            tips_context="""
            Tips nivel práctica:
            - Pensar bien qué operación (o juego de operaciones) es central en la resolución del ejercicio.
            - No confundir la semántica de las operaciones: Por ejemplo, si un problema tiene en su esencia la resolución de una diferencia de conjuntos, se espera que que el alumno utilice la diferencia de conjuntos y no otros caminos como por ejemplo la selección sobre un subconjunto del producto cartesiano, la selección de los outer join nulos, etc.
            - La notación que vamos a usar para álgebra relacional se muestra a continuación: π_{Nombre} (σ_{Ciudad= ′Buenos Aires′} (CLIENTES)) donde se quiso aplicar la proyección por el campo Nombre a la Selección con el filtro Ciudad='Buenos Aires' a la relación CLIENTES", "En este curso no utilizamos el operador Gamma (γ) para las funciones de agregación, utilizamos la F gótica (F) con la siguiente notación _{camposGroup}F_{funcionesAgregadas} (Relacion)
            - Hacer énfasis en que las operaciones de conjuntos como la diferencia de conjuntos, la unión o la intersección requieren que los dos conjuntos o relaciones tengan el mismo esquema o cabecera
            - Siempre que se haga una intersección, diferencia, o cociente de conjunto, verificar que se estén utilizando los campos clave, ya que al poder incluir valores repetidos, el resultado puede ser incorrecto si se usan campos que no tienen restricción de unicidad.
            - Tener en cuenta que los alumnos pueden llegar al mismo resultado descomponiendo las partes, es decir ir haciendo asignaciones a Relaciones parciales y expresando la solución en función de las Relaciones parciales, una vez que lleguen a un buen resultado así, es conveniente sugerirles como práctica adicional que intenten consolidar una única sentencia de Algebra Relacional para que vean cómo quedaría.
            - En una suceción de operaciones de junta, cuando en alguna de las relaciones se aplica una selección, preferimos que la selección se aplique al conjunto de las juntas completo, ya que luego cuando los alumnos representan en SQL tienden a hacer sub-queries dentro de las juntas, lo que puede ser contraproducente. Igualmente damos por válida en Algebra Relacional cualquiera de las dos maneras.
            - Desaconsejamos el uso de la junta natural (NATURAL JOIN) por lo que expresaremos todas las recomendaciones y soluciones especificando el criterio de junta. El motivo para desaconsejar el uso de Natural Join es el de mantenibilidad de los sistemas: Hoy funciona, pero no sabemos si mañana se introducen campos nuevos en las relaciones, lo que destruiría el buen funcionamiento de las expresiones AR/SQL)
            
            Tips nivel ejercicio:
            - Tener en cuenta que puede haber varias respuestas similares y están bien
            - Los alumnos tienden a simplificar y a hacer una diferencia de conjuntos utilizando únicamente la proyección por el nombre del cliente. Esto presenta un problema porque en ningún lugar dijimos que el Nombre es único. Si el alumno aclara que modifica el esquema relacional agregando una restricción de unicidad en la relación Cliente por el campo Nombre, lo consideramos una respuesta correcta, caso contrario tiene que incluir el Identificador de Cliente (Nº Cliente) en la diferencia de conjuntos-
            """
        )
    
    def create_custom_context(self) -> StudentContext:
        """
        Create a custom context based on user input.
        
        Returns:
            StudentContext with user-provided data
        """
        print("\n=== CONFIGURACIÓN DE CONTEXTO PERSONALIZADO ===")
        
        question = input("Pregunta del estudiante: ").strip()
        if not question:
            question = "No sé cómo hacer bien un left join que traiga de clientes todos los registros y que del lado de ventas traiga los que tienen nulo, aśi me quedo con los clientes que no compraron cosas, no?"
        
        subject = input("Materia (default: Bases de Datos Relacionales): ").strip()
        if not subject:
            subject = "Bases de Datos Relacionales"
        
        practice = input("Contexto de práctica (default: usar ejemplo): ").strip()
        if not practice:
            practice = "Práctica sobre normalización de bases de datos"
        
        exercise = input("Contexto de ejercicio (default: usar ejemplo): ").strip()
        if not exercise:
            exercise = "Ejercicio de normalización de tablas"
        
        solution = input("Contexto de solución (opcional): ").strip()
        tips = input("Tips del profesor (opcional): ").strip()
        
        return StudentContext(
            student_question=question,
            conversation_history=[],
            subject_name=subject,
            practice_context=practice,
            exercise_context=exercise,
            solution_context=solution or "No se proporcionó solución esperada",
            tips_context=tips or "No se proporcionaron tips adicionales"
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
            
            async for chunk in self.agent.stream(context.student_question, self.context_id):
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
    
    async def interactive_mode(self):
        """Run the agent in interactive mode for continuous testing."""
        print("\n🔍 MODO INTERACTIVO - GapAnalyzer Local Runner")
        print("Escribe 'exit' para salir, 'help' para ayuda")
        
        while True:
            print("\n" + "-" * 50)
            print("OPCIONES:")
            print("1. Usar contexto de ejemplo")
            print("2. Crear contexto personalizado")
            print("3. Análisis rápido (sin streaming)")
            print("4. Mostrar configuración actual")
            print("5. Ayuda")
            print("exit. Salir")
            
            choice = input("\nSelecciona una opción: ").strip().lower()
            
            if choice in ['exit', 'quit', 'q']:
                print("👋 ¡Hasta luego!")
                break
            elif choice == '1':
                question = input("Pregunta del estudiante (o Enter para usar ejemplo): ").strip()
                if not question:
                    question = "No sé cómo hacer bien un left join que traiga de clientes todos los registros y que del lado de ventas traiga los que tienen nulo, así me quedo con los clientes que no compraron cosas, no?"

                context = self.create_sample_context(question)
                result = await self.run_analysis(context, stream=True)
                self.print_result(result)
                
            elif choice == '2':
                context = self.create_custom_context()
                result = await self.run_analysis(context, stream=True)
                self.print_result(result)
                
            elif choice == '3':
                question = input("Pregunta del estudiante: ").strip()
                if not question:
                    question = "¿Cuál es la diferencia entre 2FN y 3FN?"
                
                context = self.create_sample_context(question)
                result = await self.run_analysis(context, stream=False)
                self.print_result(result)
                
            elif choice == '4':
                print(f"\n📋 CONFIGURACIÓN ACTUAL:")
                print(f"   • Context ID: {self.context_id}")
                print(f"   • Agent type: {type(self.agent).__name__}")
                print(f"   • LLM model: {getattr(self.agent.llm, 'model_name', 'Unknown')}")
                
            elif choice == '5' or choice == 'help':
                print(f"\n📖 AYUDA:")
                print(f"   • Opción 1: Usa un contexto predefinido de normalización")
                print(f"   • Opción 2: Te permite crear tu propio contexto paso a paso")
                print(f"   • Opción 3: Análisis directo sin mostrar progreso")
                print(f"   • Streaming: Muestra el progreso del análisis en tiempo real")
                print(f"   • Non-streaming: Ejecuta todo el análisis y muestra resultado final")
                
            else:
                print("❌ Opción no válida. Escribe 'help' para ver las opciones.")


async def main():
    """Main entry point for the local runner."""
    try:
        runner = LocalGapAnalyzerRunner()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == '--interactive' or sys.argv[1] == '-i':
                await runner.interactive_mode()
            elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
                print_help()
            else:
                # Single question mode
                question = " ".join(sys.argv[1:])
                context = runner.create_sample_context(question)
                result = await runner.run_analysis(context)
                runner.print_result(result)
        else:
            # Default to interactive mode
            await runner.interactive_mode()
            
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
    python -m gapanalyzer.local_runner [OPTIONS] [QUESTION]

OPTIONS:
    -i, --interactive    Modo interactivo con menú de opciones
    -h, --help          Muestra esta ayuda

EXAMPLES:
    # Modo interactivo
    python -m gapanalyzer.local_runner --interactive
    
    # Pregunta directa
    python -m gapanalyzer.local_runner "¿Cómo normalizo esta tabla?"
    
    # Sin argumentos (modo interactivo por defecto)
    python -m gapanalyzer.local_runner

CARACTERÍSTICAS:
    • Debugging local sin framework A2A
    • Streaming de progreso en tiempo real
    • Contexto personalizable o predefinido
    • Análisis completo de gaps educativos
    • Integración con observabilidad Langfuse
    """)


if __name__ == "__main__":
    asyncio.run(main())