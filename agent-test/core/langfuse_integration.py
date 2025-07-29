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

from ..schemas import TestSuite, TestRun, ExecutionResult

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
            # Test connection by trying to list datasets
            self.client.get_datasets()
            print("✅ Conexión a Langfuse establecida")
        except Exception as e:
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
            datasets = self.client.get_datasets()
            
            dataset_list = []
            for dataset in datasets.data:
                dataset_info = {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description or "",
                    "item_count": len(dataset.items) if hasattr(dataset, 'items') else 0,
                    "created_at": dataset.created_at.isoformat() if dataset.created_at else "",
                    "metadata": dataset.metadata or {}
                }
                dataset_list.append(dataset_info)
            
            return dataset_list
            
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
    
    def create_test_run(self, run_data: TestRun, dataset_name: Optional[str] = None) -> str:
        """
        Crear un run de prueba en Langfuse.
        
        Args:
            run_data: Datos del run de prueba
            dataset_name: Nombre del dataset asociado (opcional)
            
        Returns:
            ID del run creado en Langfuse
        """
        try:
            print(f"📈 Creando run de prueba en Langfuse...")
            
            # Create the run
            run = self.client.create_run(
                name=f"agent-test-{run_data.suite_name}-{run_data.run_id[:8]}",
                description=f"Ejecución de suite {run_data.suite_name} con agente {run_data.agent_type}",
                metadata={
                    "suite_name": run_data.suite_name,
                    "agent_type": run_data.agent_type,
                    "run_id": run_data.run_id,
                    "session_id": run_data.session_id,
                    "iterations": run_data.iterations,
                    "total_questions": run_data.total_questions,
                    "successful_questions": run_data.successful_questions,
                    "success_rate": run_data.get_success_rate(),
                    "total_time": run_data.total_time,
                    "average_time": run_data.get_average_execution_time(),
                    "start_time": run_data.start_time.isoformat(),
                    "end_time": run_data.end_time.isoformat(),
                    "dataset_name": dataset_name,
                    "summary_metrics": run_data.summary_metrics
                }
            )
            
            # Add individual question results as spans
            for i, result in enumerate(run_data.results):
                span = self.client.create_span(
                    name=f"question-{i+1}",
                    trace_id=run.id,  # Associate with the run
                    input={
                        "question": result.question_text,
                        "question_id": result.question_id,
                        "session_id": result.session_id
                    },
                    output={
                        "response": result.agent_response,
                        "success": result.success,
                        "execution_time": result.execution_time
                    },
                    metadata={
                        "metrics": result.metrics,
                        "agent_metadata": result.agent_metadata,
                        "error": result.error,
                        "timestamp": result.timestamp.isoformat()
                    }
                )
                
                # If there's a specific trace_id from the agent execution, link it
                if result.langfuse_trace_id:
                    span.metadata["original_trace_id"] = result.langfuse_trace_id
                
                print(f"   📊 Span {i+1}/{len(run_data.results)} creado")
            
            print(f"✅ Run de prueba creado en Langfuse")
            print(f"   ID: {run.id}")
            
            return run.id
            
        except Exception as e:
            print(f"❌ Error creando run de prueba: {e}")
            raise
    
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
            trace = self.client.create_trace(
                name=f"agent-question-{uuid4().hex[:8]}",
                input={"question": question_text},
                output={"response": agent_response},
                metadata=metadata
            )
            
            return trace.id
            
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
            # Try to make a simple API call
            datasets = self.client.get_datasets()
            
            return {
                "connected": True,
                "host": os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
                "datasets_count": len(datasets.data) if datasets else 0,
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