"""
Test Runner - Ejecutor de suites de pruebas contra agentes.

Ejecuta preguntas de suites contra Orchestrator y GapAnalyzer,
recolecta métricas y genera reportes de resultados.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.agent_executor import OrchestratorAgentExecutor
from gapanalyzer.agent_executor import GapAnalyzerAgentExecutor

# Add agent-test directory to path for schemas import
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import TestSuite, TestRun, ExecutionResult, AgentType, OrchestratorMetrics, GapAnalyzerMetrics

# Import from current directory
sys.path.insert(0, str(Path(__file__).parent))
from suite_manager import SuiteManager
from results_manager import ResultsManager
from metrics_collector import MetricsCollector
from langfuse_integration import LangfuseManager, check_langfuse_availability

class TestRunner:
    """Ejecutor de suites de pruebas."""
    
    def __init__(self):
        """Inicializar el ejecutor de pruebas."""
        self.suite_manager = SuiteManager()
        self.results_manager = ResultsManager()
        self.metrics_collector = MetricsCollector()
        
        # Initialize agents
        self.orchestrator = OrchestratorAgentExecutor()
        self.gapanalyzer = GapAnalyzerAgentExecutor()
        
        # Initialize Langfuse if available
        self.langfuse_enabled = check_langfuse_availability()
        if self.langfuse_enabled:
            try:
                self.langfuse_manager = LangfuseManager()
                print("✅ Langfuse habilitado para tracking")
            except Exception as e:
                print(f"⚠️ Error inicializando Langfuse: {e}")
                self.langfuse_enabled = False
        else:
            print("ℹ️ Langfuse no disponible - solo almacenamiento local")
    
    def run_suite(self, suite_name: str, agent_override: Optional[str] = None, 
                  iterations: int = 1, session_id: Optional[str] = None,
                  run_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Ejecutar una suite de pruebas.
        
        Args:
            suite_name: Nombre de la suite a ejecutar
            agent_override: Override del tipo de agente (opcional)
            iterations: Número de iteraciones por pregunta
            session_id: ID de sesión personalizada
            run_name: Nombre personalizado para el run (aparece en Langfuse)
            
        Returns:
            Resultados de la ejecución
        """
        # Load suite
        suite_data = self.suite_manager.get_suite(suite_name)
        suite = TestSuite(**suite_data)
        
        # Determine agent type
        agent_type = AgentType(agent_override) if agent_override else suite.agent_type
        
        # Generate run ID and session if not provided
        run_id = f"run_{uuid4().hex[:12]}"
        if not session_id:
            session_id = f"test_session_{uuid4().hex[:8]}"
        
        print(f"🚀 Ejecutando suite '{suite_name}'")
        print(f"   Agente: {agent_type.value}")
        print(f"   Preguntas: {len(suite.questions)}")
        print(f"   Iteraciones: {iterations}")
        print(f"   Run ID: {run_id}")
        print(f"   Session ID: {session_id}")
        
        # Initialize run data
        start_time = datetime.now()
        results = []
        
        try:
            # Execute questions
            if agent_type == AgentType.BOTH:
                # Execute with both agents
                results = self._run_with_both_agents(suite, iterations, session_id)
            else:
                # Execute with single agent
                results = self._run_with_single_agent(suite, agent_type, iterations, session_id)
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            # Calculate summary metrics
            successful_questions = sum(1 for r in results if r.success)
            summary_metrics = self.metrics_collector.calculate_summary_metrics(results)
            
            # Create run data
            run_data = TestRun(
                run_id=run_id,
                suite_name=suite_name,
                agent_type=agent_type,
                iterations=iterations,
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                total_time=total_time,
                results=results,
                total_questions=len(results),
                successful_questions=successful_questions,
                summary_metrics=summary_metrics
            )
            
            # Save results locally
            results_file = self.results_manager.save_run_results(run_data)
            
            # Upload to Langfuse if enabled
            langfuse_run_info = None
            if self.langfuse_enabled:
                try:
                    langfuse_run_info = self.langfuse_manager.create_test_run(
                        run_data, 
                        dataset_name=f"{suite_name}_dataset",
                        run_name=run_name
                    )
                    run_data.langfuse_run_id = langfuse_run_info.get('run_name') if langfuse_run_info else None
                    
                    # Check if complete execution already happened within dataset context
                    if langfuse_run_info and langfuse_run_info.get('complete_execution'):
                        print(f"✅ Ejecución completa de agentes ya realizada dentro del contexto del dataset")
                        print(f"   Las trazas completas del workflow están disponibles en Langfuse")
                    else:
                        print(f"⚠️ Dataset run creado sin ejecución completa de agentes")
                    
                except Exception as e:
                    print(f"⚠️ Error subiendo a Langfuse: {e}")
            
            print(f"✅ Suite ejecutada exitosamente")
            print(f"   Tiempo total: {total_time:.2f}s")
            print(f"   Éxito: {successful_questions}/{len(results)} ({run_data.get_success_rate():.1%})")
            
            return {
                'run_id': run_id,
                'suite_name': suite_name,
                'agent_type': agent_type.value,
                'total_questions': len(results),
                'successful_questions': successful_questions,
                'success_rate': run_data.get_success_rate(),
                'total_time': total_time,
                'average_time': run_data.get_average_execution_time(),
                'results_file': str(results_file),
                'summary': summary_metrics,
                'langfuse_run_id': langfuse_run_info.get('run_name') if langfuse_run_info else None
            }
            
        except Exception as e:
            print(f"❌ Error ejecutando suite: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _run_with_single_agent(self, suite: TestSuite, agent_type: AgentType, 
                              iterations: int, session_id: str) -> List[ExecutionResult]:
        """Ejecutar suite con un solo agente."""
        results = []
        
        for i, question in enumerate(suite.questions):
            print(f"📝 Pregunta {i+1}/{len(suite.questions)}: {question.question[:80]}...")
            
            # Execute multiple iterations if requested
            question_results = []
            for iteration in range(iterations):
                iteration_session = f"{session_id}_q{i+1}_iter{iteration+1}"
                
                try:
                    result = asyncio.run(self._execute_question(
                        question, agent_type, iteration_session
                    ))
                    question_results.append(result)
                    
                except Exception as e:
                    error_result = ExecutionResult(
                        question_id=question.id,
                        question_text=question.question,
                        success=False,
                        error=str(e),
                        execution_time=0.0,
                        session_id=iteration_session
                    )
                    question_results.append(error_result)
            
            # If multiple iterations, aggregate results
            if iterations == 1:
                results.extend(question_results)
            else:
                # Create aggregated result
                aggregated_result = self._aggregate_question_results(question_results)
                results.append(aggregated_result)
        
        return results
    
    def _run_with_both_agents(self, suite: TestSuite, iterations: int, 
                             session_id: str) -> List[ExecutionResult]:
        """Ejecutar suite con ambos agentes."""
        results = []
        
        for i, question in enumerate(suite.questions):
            print(f"📝 Pregunta {i+1}/{len(suite.questions)} (ambos agentes): {question.question[:80]}...")
            
            # Execute with Orchestrator
            try:
                orchestrator_result = asyncio.run(self._execute_question(
                    question, AgentType.ORCHESTRATOR, f"{session_id}_q{i+1}_orchestrator"
                ))
                orchestrator_result.agent_metadata['agent_used'] = 'orchestrator'
                results.append(orchestrator_result)
            except Exception as e:
                error_result = ExecutionResult(
                    question_id=f"{question.id}_orchestrator",
                    question_text=question.question,
                    success=False,
                    error=str(e),
                    execution_time=0.0,
                    session_id=f"{session_id}_q{i+1}_orchestrator"
                )
                error_result.agent_metadata['agent_used'] = 'orchestrator'
                results.append(error_result)
            
            # Execute with GapAnalyzer (if applicable)
            if question.practice_id:  # Only run GapAnalyzer for questions with practice context
                try:
                    gapanalyzer_result = asyncio.run(self._execute_question(
                        question, AgentType.GAPANALYZER, f"{session_id}_q{i+1}_gapanalyzer"
                    ))
                    gapanalyzer_result.agent_metadata['agent_used'] = 'gapanalyzer'
                    results.append(gapanalyzer_result)
                except Exception as e:
                    error_result = ExecutionResult(
                        question_id=f"{question.id}_gapanalyzer",
                        question_text=question.question,
                        success=False,
                        error=str(e),
                        execution_time=0.0,
                        session_id=f"{session_id}_q{i+1}_gapanalyzer"
                    )
                    error_result.agent_metadata['agent_used'] = 'gapanalyzer'
                    results.append(error_result)
        
        return results
    
    async def _execute_question(self, question, agent_type: AgentType, 
                               session_id: str) -> ExecutionResult:
        """Ejecutar una pregunta individual contra un agente."""
        start_time = time.time()
        
        try:
            # Prepare context
            context = {
                'session_id': session_id,
                'user_id': 'test_runner'
            }
            
            if question.subject:
                context['educational_subject'] = question.subject
            
            # Execute based on agent type
            if agent_type == AgentType.ORCHESTRATOR:
                response = await self._execute_with_orchestrator(question, context)
            elif agent_type == AgentType.GAPANALYZER:
                response = await self._execute_with_gapanalyzer(question, context)
            else:
                raise ValueError(f"Tipo de agente no soportado: {agent_type}")
            
            execution_time = time.time() - start_time
            
            # Collect metrics
            metrics = self.metrics_collector.collect_question_metrics(
                question, response, agent_type, execution_time
            )
            
            # Create trace in Langfuse if enabled
            langfuse_trace_id = None
            if self.langfuse_enabled:
                try:
                    langfuse_trace_id = self.langfuse_manager.create_trace_for_question(
                        question.question,
                        response.get('content', ''),
                        {
                            'agent_type': agent_type.value,
                            'session_id': session_id,
                            'subject': question.subject,
                            'difficulty': question.difficulty.value,
                            'execution_time': execution_time,
                            'metrics': metrics
                        }
                    )
                except Exception as e:
                    print(f"⚠️ Error creando trace en Langfuse: {e}")
            
            return ExecutionResult(
                question_id=question.id,
                question_text=question.question,
                success=True,
                agent_response=response.get('content', ''),
                execution_time=execution_time,
                session_id=session_id,
                metrics=metrics,
                agent_metadata=response.get('metadata', {}),
                langfuse_trace_id=langfuse_trace_id
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                question_id=question.id,
                question_text=question.question,
                success=False,
                error=str(e),
                execution_time=execution_time,
                session_id=session_id
            )
    
    async def _execute_with_orchestrator(self, question, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar pregunta con Orchestrator."""
        request = {'message': question.question}
        
        # Collect streaming response
        final_response = ""
        metadata = {}
        
        async for chunk in self.orchestrator.stream(request=request, context=context):
            if chunk.get('is_task_complete'):
                final_response = chunk.get('content', '')
                metadata = chunk.get('metadata', {})
                break
        
        return {
            'content': final_response,
            'metadata': metadata
        }
    
    async def _execute_with_gapanalyzer(self, question, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar pregunta con GapAnalyzer."""
        # GapAnalyzer requires practice_id and exercise_section
        if not question.practice_id:
            raise ValueError("GapAnalyzer requiere practice_id en la pregunta")
        
        # Create message with practice context
        message_content = f"practice_id:{question.practice_id}|exercise_section:{question.exercise_section or '1.a'}|query:{question.question}"
        
        # Execute using agent's stream method
        try:
            # Use the agent's stream method and collect the final response
            context_id = context.get('session_id', 'test_session')
            
            final_response = ""
            async for chunk in self.gapanalyzer.agent.stream(question.question, context_id):
                if chunk.get('is_task_complete', False):
                    final_response = chunk.get('content', '')
                    break
                elif chunk.get('content'):
                    # This is a progress update, we can ignore or log it
                    pass
            
            if not final_response:
                # If we didn't get a final response, try to get the last content
                final_response = chunk.get('content', 'No response generated')
            
            return {
                'content': final_response,
                'metadata': {'agent': 'gapanalyzer', 'practice_id': question.practice_id}
            }
        except Exception as e:
            # If that fails, try simple text response
            print(f"⚠️ GapAnalyzer execution failed, using fallback: {e}")
            return {
                'content': f"Error executing GapAnalyzer: {str(e)}",
                'metadata': {'error': True}
            }
    
    def _aggregate_question_results(self, results: List[ExecutionResult]) -> ExecutionResult:
        """Agregar resultados de múltiples iteraciones de una pregunta."""
        if not results:
            raise ValueError("No hay resultados para agregar")
        
        # Use first result as base
        base_result = results[0]
        
        # Calculate aggregated metrics
        successful_runs = [r for r in results if r.success]
        success_rate = len(successful_runs) / len(results)
        avg_execution_time = sum(r.execution_time for r in results) / len(results)
        
        # Aggregate responses (could be improved with more sophisticated logic)
        aggregated_response = ""
        if successful_runs:
            # Use the response from the first successful run
            aggregated_response = successful_runs[0].agent_response
        
        # Aggregate metrics
        aggregated_metrics = {}
        if successful_runs:
            # Average numeric metrics
            for result in successful_runs:
                for key, value in result.metrics.items():
                    if isinstance(value, (int, float)):
                        aggregated_metrics[key] = aggregated_metrics.get(key, 0) + value
            
            # Average the values
            for key in aggregated_metrics:
                aggregated_metrics[key] /= len(successful_runs)
        
        # Add iteration metadata
        aggregated_metrics['iterations_run'] = len(results)
        aggregated_metrics['iterations_successful'] = len(successful_runs)
        aggregated_metrics['success_rate'] = success_rate
        
        return ExecutionResult(
            question_id=base_result.question_id,
            question_text=base_result.question_text,
            success=success_rate > 0,  # Consider successful if at least one iteration succeeded
            agent_response=aggregated_response,
            execution_time=avg_execution_time,
            session_id=base_result.session_id,
            metrics=aggregated_metrics,
            agent_metadata={
                'aggregated_from_iterations': len(results),
                'individual_results': [
                    {
                        'success': r.success,
                        'execution_time': r.execution_time,
                        'error': r.error
                    }
                    for r in results
                ]
            }
        )
    
    def validate_suite_for_agent(self, suite_name: str, agent_type: AgentType) -> Dict[str, Any]:
        """
        Validar si una suite es compatible con un tipo de agente.
        
        Args:
            suite_name: Nombre de la suite
            agent_type: Tipo de agente
            
        Returns:
            Resultado de validación
        """
        suite_data = self.suite_manager.get_suite(suite_name)
        suite = TestSuite(**suite_data)
        
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'compatible_questions': 0,
            'total_questions': len(suite.questions)
        }
        
        for question in suite.questions:
            question_valid = True
            
            if agent_type == AgentType.GAPANALYZER:
                # GapAnalyzer requires practice_id
                if not question.practice_id:
                    validation_result['warnings'].append(
                        f"Pregunta '{question.id}' no tiene practice_id para GapAnalyzer"
                    )
                    question_valid = False
            
            if question_valid:
                validation_result['compatible_questions'] += 1
        
        if validation_result['compatible_questions'] == 0:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"Ninguna pregunta es compatible con {agent_type.value}"
            )
        
        return validation_result