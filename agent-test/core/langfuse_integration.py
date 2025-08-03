"""
Langfuse Integration - Gestión de datasets y traces en Langfuse.

Maneja la subida de suites como datasets y el tracking de ejecuciones
de pruebas como traces en Langfuse.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add project root to path for tools import
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langfuse import Langfuse
    from langfuse.model import CreateDatasetRequest, CreateDatasetItemRequest
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("⚠️ Langfuse no disponible. Instala con: pip install langfuse")

# Add parent directory to path for schemas import
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import TestSuite, TestRun, ExecutionResult

class LangfuseManager:
    """Gestor de integración con Langfuse."""
    
    def __init__(self):
        """Inicializar conexión a Langfuse."""
        if not LANGFUSE_AVAILABLE:
            raise ImportError("Langfuse no está disponible. Instala con: pip install langfuse")
        
        # Initialize Langfuse client
        self.client = Langfuse(
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY")
        )
        
        # Verify connection
        try:
            # Test connection by trying to access a non-existent dataset
            self.client.get_dataset("__connection_test__")
            print("✅ Conexión a Langfuse establecida")
        except Exception as e:
            if "not found" in str(e).lower():
                print("✅ Conexión a Langfuse establecida")
            else:
                print(f"⚠️ Error conectando a Langfuse: {e}")
                print("Verifica las variables de entorno LANGFUSE_* ")
    
    def upload_dataset(self, name: str, description: str, suite_data: Dict[str, Any]) -> str:
        """
        Subir una suite como dataset a Langfuse.
        
        Args:
            name: Nombre del dataset
            description: Descripción del dataset
            suite_data: Datos de la suite
            
        Returns:
            ID del dataset creado
            
        Raises:
            Exception: Si hay error subiendo el dataset
        """
        try:
            print(f"📤 Subiendo dataset '{name}' a Langfuse...")
            
            # Create dataset
            dataset = self.client.create_dataset(
                name=name,
                description=description,
                metadata={
                    "agent_type": suite_data.get("agent_type"),
                    "suite_version": suite_data.get("version", "1.0"),
                    "created_from": "luca-agent-testing",
                    "original_suite_name": suite_data.get("name"),
                    "question_count": len(suite_data.get("questions", [])),
                    "upload_timestamp": datetime.now().isoformat()
                }
            )
            
            # Add questions as dataset items
            questions = suite_data.get("questions", [])
            for i, question in enumerate(questions):
                item_input = {
                    "question": question["question"],
                    "context": question.get("context"),
                    "subject": question.get("subject"),
                    "difficulty": question.get("difficulty", "medium"),
                    "practice_id": question.get("practice_id"),
                    "exercise_section": question.get("exercise_section"),
                    "tags": question.get("tags", [])
                }
                
                item_expected_output = {
                    "expected_answer": question["expected_answer"],
                    "metrics": question.get("metrics", {}),
                    "evaluation_criteria": {
                        "should_contain": [],  # Can be filled based on expected_answer
                        "should_not_contain": [],
                        "max_length": None,
                        "min_length": None
                    }
                }
                
                self.client.create_dataset_item(
                    dataset_name=name,
                    input=item_input,
                    expected_output=item_expected_output,
                    metadata={
                        "question_id": question.get("id"),
                        "original_order": i + 1,
                        "created_at": question.get("created_at"),
                        "updated_at": question.get("updated_at")
                    }
                )
                
                print(f"   📝 Item {i+1}/{len(questions)} agregado")
            
            print(f"✅ Dataset '{name}' subido exitosamente")
            print(f"   ID: {dataset.id}")
            print(f"   Items: {len(questions)}")
            
            return dataset.id
            
        except Exception as e:
            print(f"❌ Error subiendo dataset: {e}")
            raise
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        Listar datasets en Langfuse.
        
        Returns:
            Lista de datasets con información básica
        """
        try:
            # Current Langfuse SDK doesn't have get_datasets (plural), only get_dataset (singular)
            # This is a limitation of the current API version
            print("⚠️ La versión actual de Langfuse no soporta listado de datasets")
            return []
            
        except Exception as e:
            print(f"❌ Error listando datasets: {e}")
            return []
    
    def get_dataset(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un dataset específico por nombre.
        
        Args:
            name: Nombre del dataset
            
        Returns:
            Información del dataset o None si no existe
        """
        try:
            dataset = self.client.get_dataset(name)
            if dataset:
                return {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "items": [
                        {
                            "id": item.id,
                            "input": item.input,
                            "expected_output": item.expected_output,
                            "metadata": item.metadata
                        }
                        for item in dataset.items
                    ],
                    "created_at": dataset.created_at.isoformat() if dataset.created_at else "",
                    "metadata": dataset.metadata or {}
                }
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo dataset '{name}': {e}")
            return None
    
    def create_test_run(self, run_data: TestRun, dataset_name: Optional[str] = None, 
                       run_name: Optional[str] = None) -> str:
        """
        Crear un run de prueba en Langfuse.
        
        Args:
            run_data: Datos del run de prueba
            dataset_name: Nombre del dataset asociado (opcional)
            run_name: Nombre personalizado para el run (opcional)
            
        Returns:
            ID del run creado en Langfuse
        """
        try:
            print(f"📈 Creando dataset run en Langfuse...")
            
            # Step 1: Ensure dataset exists and create base items only once
            actual_dataset_name = dataset_name or f"{run_data.suite_name}_dataset"
            try:
                dataset = self.client.get_dataset(actual_dataset_name)
                print(f"   📊 Dataset '{actual_dataset_name}' ya existe")
            except:
                # Dataset doesn't exist, create it with base items
                print(f"   📊 Creando dataset '{actual_dataset_name}' con items base...")
                dataset = self.client.create_dataset(
                    name=actual_dataset_name,
                    description=f"Dataset para suite {run_data.suite_name} - Agente {run_data.agent_type}",
                    metadata={
                        "suite_name": run_data.suite_name,
                        "agent_type": run_data.agent_type,
                        "created_by": "agent-test-framework"
                    }
                )
                
                # Create base dataset items only once
                for i, result in enumerate(run_data.results):
                    try:
                        base_item = self.client.create_dataset_item(
                            dataset_name=actual_dataset_name,
                            input={
                                "question": result.question_text,
                                "question_id": result.question_id,
                                "context": {
                                    "agent_type": run_data.agent_type,
                                    "suite_name": run_data.suite_name
                                }
                            },
                            expected_output={
                                "success": True,
                                "response_type": "educational_response",
                                "expected_quality_metrics": {
                                    "relevance_score": ">= 0.7",
                                    "educational_value": ">= 0.4",
                                    "response_completeness": ">= 0.8"
                                }
                            },
                            metadata={
                                "question_type": result.question_id.split('_')[0] if '_' in result.question_id else "general",
                                "created_for": "agent-testing"
                            }
                        )
                        print(f"      📝 Item base {i+1}/{len(run_data.results)} creado")
                    except Exception as e:
                        print(f"      ⚠️ Error creando item base {i+1}: {e}")
                
                # Re-fetch dataset to get items
                dataset = self.client.get_dataset(actual_dataset_name)
                        
            
            # Step 2: Create proper dataset run using item.run() context manager
            actual_run_name = run_name if run_name else f"TestRun-{run_data.suite_name}-{run_data.run_id[:8]}"
            print(f"   🏃 Creando dataset run: {actual_run_name}")
            
            # Process each dataset item with proper run context AND agent execution
            run_traces = []
            
            for i, (result, dataset_item) in enumerate(zip(run_data.results, dataset.items)):
                try:
                    print(f"   📊 Procesando question {i+1}/{len(run_data.results)} en dataset run...")
                    
                    with dataset_item.run(
                        run_name=actual_run_name,
                        run_description=f"Ejecución automatizada de suite {run_data.suite_name}",
                        run_metadata={
                            "agent_type": run_data.agent_type,
                            "suite_name": run_data.suite_name,
                            "run_id": run_data.run_id,
                            "question_index": i + 1,
                            "total_questions": len(run_data.results),
                            "execution_time": result.execution_time,
                            "success": result.success,
                            "timestamp": run_data.start_time.isoformat(),
                            "agent_test_mode": True  # Flag to indicate this is from agent testing
                        }
                    ) as root_span:
                        # Execute the agent with full LangGraph observability WITHIN the dataset item context
                        print(f"      🔍 Ejecutando agente con observabilidad completa dentro del dataset item...")
                        
                        try:
                            # Create CallbackHandler for LangGraph observability
                            from langfuse.langchain import CallbackHandler
                            langfuse_handler = CallbackHandler()
                            
                            # Import agent executor on demand
                            from orchestrator.agent_executor import OrchestratorAgentExecutor
                            agent_executor = OrchestratorAgentExecutor()
                            
                            # Prepare context for agent execution
                            question_context = {
                                'session_id': f"{run_data.session_id}_dataset_q{i+1}",
                                'user_id': 'agent_test_dataset_run',
                                'agent_test_mode': True,
                                'educational_subject': result.question_text.get('subject', 'Bases de Datos') if isinstance(result.question_text, dict) else 'Bases de Datos'
                            }
                            
                            # Execute agent with LangGraph callback - this creates the complete workflow trace
                            async def run_agent_in_dataset_context():
                                request = {'message': result.question_text}
                                final_response = ""
                                
                                async for chunk in agent_executor.stream(
                                    request=request, 
                                    context={**question_context, "config": {"callbacks": [langfuse_handler]}}
                                ):
                                    if chunk.get('is_task_complete'):
                                        final_response = chunk.get('content', '')
                                        break
                                
                                return final_response
                            
                            # Execute the agent within the dataset item context
                            import asyncio
                            agent_response = asyncio.run(run_agent_in_dataset_context())
                            
                            # Set the actual agent response as the output for this dataset item
                            root_span.update(output={"agent_response": agent_response})
                            
                            print(f"      ✅ Agente ejecutado con traza completa del workflow")
                            
                        except Exception as agent_error:
                            print(f"      ⚠️ Error ejecutando agente: {agent_error}")
                            # Still record the result but mark as error
                            root_span.update(output={"error": str(agent_error), "original_result": result.response})
                        
                        # Add evaluation scores based on metrics
                        if result.metrics:
                            # Educational quality scores
                            if "educational_value" in result.metrics:
                                root_span.score_trace(
                                    name="educational_value",
                                    value=result.metrics["educational_value"],
                                    comment="Automated evaluation of educational quality"
                                )
                            
                            if "relevance_score" in result.metrics:
                                root_span.score_trace(
                                    name="relevance_score", 
                                    value=result.metrics["relevance_score"],
                                    comment="Automated evaluation of response relevance"
                                )
                            
                            if "response_completeness" in result.metrics:
                                root_span.score_trace(
                                    name="response_completeness",
                                    value=result.metrics["response_completeness"],
                                    comment="Automated evaluation of response completeness"
                                )
                        
                        run_traces.append(root_span.trace_id)
                        print(f"      📊 Dataset item completado (trace: {root_span.trace_id[:8]}...)")
                        
                except Exception as e:
                    print(f"   ⚠️ Error procesando question {i+1}: {e}")
            
            # Flush to ensure data is sent to Langfuse
            self.client.flush()
            
            print(f"✅ Dataset run creado en Langfuse")
            print(f"   🏃 Run Name: {actual_run_name}")
            print(f"   📊 Dataset: {actual_dataset_name}")
            print(f"   📝 Preguntas procesadas: {len(run_traces)}")
            print(f"   🕒 Timestamp: {run_data.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Return run information
            return {
                'run_name': actual_run_name,
                'dataset_name': actual_dataset_name,
                'trace_ids': run_traces,
                'complete_execution': True  # Flag indicating agent execution happened within dataset context
            }
            
        except Exception as e:
            print(f"❌ Error creando run de prueba: {e}")
            raise
    
    def enhance_dataset_run_with_agent_traces(self, run_data: TestRun, dataset_run_info: dict, 
                                            agent_executor, test_context: dict) -> None:
        """
        Re-ejecutar agentes con observabilidad completa de LangGraph para mostrar cada nodo del workflow.
        
        Esta función ejecuta cada pregunta nuevamente con CallbackHandler habilitado para capturar
        la observabilidad completa de LangGraph, mostrando cada nodo del workflow con su input/output real.
        
        Args:
            run_data: Datos del run original
            dataset_run_info: Info del dataset run creado
            agent_executor: Ejecutor del agente (OrchestratorAgentExecutor o GapAnalyzerAgentExecutor)
            test_context: Contexto adicional de testing
        """
        try:
            print(f"🔍 Ejecutando agentes con observabilidad completa de LangGraph...")
            print(f"    Esto mostrará cada nodo del workflow con timing real y input/output detallado")
            
            for i, result in enumerate(run_data.results):
                try:
                    print(f"   🔍 Ejecutando question {i+1} con CallbackHandler habilitado...")
                    
                    # Configure Langfuse CallbackHandler for detailed LangGraph observability
                    from langfuse.langchain import CallbackHandler
                    
                    # Create a CallbackHandler that will capture REAL LangGraph execution details
                    langfuse_handler = CallbackHandler()
                    
                    # Prepare question context
                    question_context = {
                        'session_id': f"{run_data.session_id}_langgraph_q{i+1}",
                        'user_id': 'agent_test_langgraph_tracing',
                        'agent_test_mode': True,
                        'educational_subject': test_context.get('subject_name', 'Bases de Datos')
                    }
                    
                    # Execute with proper LangGraph observability
                    if hasattr(agent_executor, 'stream'):
                        # For Orchestrator-style agents
                        async def run_with_full_langgraph_observability():
                            request = {'message': result.question_text}
                            
                            # Execute with LangGraph callback - this will show every workflow node
                            final_response = ""
                            
                            async for chunk in agent_executor.stream(
                                request=request, 
                                context={**question_context, "config": {"callbacks": [langfuse_handler]}}
                            ):
                                if chunk.get('is_task_complete'):
                                    final_response = chunk.get('content', '')
                                    break
                            
                            return final_response
                        
                        # Run the async function to get real LangGraph traces
                        import asyncio
                        final_response = asyncio.run(run_with_full_langgraph_observability())
                        
                        # Check if trace was created
                        langgraph_trace_id = getattr(langfuse_handler, 'last_trace_id', None)
                        if langgraph_trace_id:
                            print(f"      ✅ LangGraph trace completa creada: {langgraph_trace_id[:8]}...")
                            print(f"         Esta traza muestra cada nodo del workflow con timing real")
                        else:
                            print(f"      ⚠️ No se detectó trace_id del CallbackHandler")
                    
                    print(f"   ✅ Question {i+1} ejecutada con observabilidad completa de LangGraph")
                    
                except Exception as e:
                    print(f"   ⚠️ Error ejecutando question {i+1} con observabilidad: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Flush to ensure all traces are sent to Langfuse
            self.client.flush()
            
            print(f"✅ Observabilidad completa de LangGraph completada")
            print(f"   Ahora deberías ver trazas detalladas en Langfuse mostrando cada nodo del workflow")
            
        except Exception as e:
            print(f"❌ Error en observabilidad de LangGraph: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - this is enhancement, not critical
    
    def create_trace_for_question(self, question_text: str, agent_response: str, 
                                 metadata: Dict[str, Any]) -> str:
        """
        Crear un trace individual para una pregunta ejecutada.
        
        Args:
            question_text: Texto de la pregunta
            agent_response: Respuesta del agente
            metadata: Metadata adicional
            
        Returns:
            ID del trace creado
        """
        try:
            # Create trace ID and start span for individual question
            trace_id = self.client.create_trace_id(seed=f"question-{uuid4().hex[:8]}")
            trace_context = {"trace_id": trace_id}
            
            span = self.client.start_span(
                name=f"agent-question-{uuid4().hex[:8]}",
                trace_context=trace_context,
                input={"question": question_text},
                output={"response": agent_response},
                metadata=metadata
            )
            
            # End the span immediately since this is a completed interaction
            span.end()
            
            # Flush to ensure data is sent to Langfuse
            self.client.flush()
            
            return trace_id
            
        except Exception as e:
            print(f"❌ Error creando trace: {e}")
            return ""
    
    def get_run_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener resultados de un run específico desde Langfuse.
        
        Args:
            run_id: ID del run en Langfuse
            
        Returns:
            Datos del run o None si no existe
        """
        try:
            # Note: This would require Langfuse API to support getting runs by ID
            # For now, we'll return None and rely on local storage
            print(f"⚠️ Recuperación de runs desde Langfuse no implementada aún")
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo run: {e}")
            return None
    
    def create_evaluation(self, trace_id: str, name: str, value: float, 
                         comment: Optional[str] = None) -> None:
        """
        Crear una evaluación para un trace específico.
        
        Args:
            trace_id: ID del trace
            name: Nombre de la evaluación
            value: Valor de la evaluación (0.0 - 1.0)
            comment: Comentario opcional
        """
        try:
            self.client.create_score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
            
        except Exception as e:
            print(f"❌ Error creando evaluación: {e}")
    
    def bulk_create_evaluations(self, evaluations: List[Dict[str, Any]]) -> None:
        """
        Crear múltiples evaluaciones en lote.
        
        Args:
            evaluations: Lista de evaluaciones con trace_id, name, value, comment
        """
        try:
            print(f"📊 Creando {len(evaluations)} evaluaciones...")
            
            for eval_data in evaluations:
                self.create_evaluation(
                    trace_id=eval_data["trace_id"],
                    name=eval_data["name"],
                    value=eval_data["value"],
                    comment=eval_data.get("comment")
                )
            
            print(f"✅ {len(evaluations)} evaluaciones creadas")
            
        except Exception as e:
            print(f"❌ Error creando evaluaciones en lote: {e}")
    
    def delete_dataset(self, name: str) -> bool:
        """
        Eliminar un dataset de Langfuse.
        
        Args:
            name: Nombre del dataset
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            # Note: Check if Langfuse API supports dataset deletion
            print(f"⚠️ Eliminación de datasets desde Langfuse no soportada por la API")
            return False
            
        except Exception as e:
            print(f"❌ Error eliminando dataset: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Obtener estado de la conexión a Langfuse.
        
        Returns:
            Información sobre el estado de la conexión
        """
        try:
            # Try to make a simple API call by testing dataset access
            self.client.get_dataset("__connection_test__")
            
            return {
                "connected": True,
                "host": os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
                "datasets_count": 0,  # Cannot count without get_datasets API
                "error": None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "host": os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
                "datasets_count": 0,
                "error": str(e)
            }

def check_langfuse_availability() -> bool:
    """
    Verificar si Langfuse está disponible y configurado.
    
    Returns:
        True si Langfuse está disponible
    """
    if not LANGFUSE_AVAILABLE:
        return False
    
    required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ Variables de entorno faltantes para Langfuse: {missing_vars}")
        return False
    
    return True