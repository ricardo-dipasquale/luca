"""
Results Manager - Gestión de resultados de ejecuciones de pruebas.

Maneja almacenamiento, consulta y análisis de resultados de ejecuciones
de suites de pruebas.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add parent directory to path for schemas import
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import TestRun, ExecutionResult

class ResultsManager:
    """Gestor de resultados de ejecuciones."""
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        Inicializar el gestor de resultados.
        
        Args:
            results_dir: Directorio donde almacenar resultados (default: agent-test/results)
        """
        if results_dir is None:
            # Get directory relative to this file
            current_dir = Path(__file__).parent.parent
            self.results_dir = current_dir / "results"
        else:
            self.results_dir = Path(results_dir)
        
        # Create directory structure
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / "runs").mkdir(exist_ok=True)
        (self.results_dir / "summaries").mkdir(exist_ok=True)
        (self.results_dir / "exports").mkdir(exist_ok=True)
    
    def save_run_results(self, run_data: TestRun) -> Path:
        """
        Guardar resultados de una ejecución.
        
        Args:
            run_data: Datos de la ejecución
            
        Returns:
            Path al archivo de resultados guardado
        """
        # Create filename with timestamp and run_id
        timestamp = run_data.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{run_data.suite_name}_{run_data.run_id}.json"
        file_path = self.results_dir / "runs" / filename
        
        # Convert to dict for JSON serialization
        run_dict = run_data.model_dump()
        
        # Custom serialization for datetime objects
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Save results
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(run_dict, f, indent=2, ensure_ascii=False, default=serialize_datetime)
        
        # Update index
        self._update_runs_index(run_data, file_path)
        
        print(f"💾 Resultados guardados en: {file_path}")
        return file_path
    
    def get_run_results(self, run_id: str) -> Dict[str, Any]:
        """
        Obtener resultados de una ejecución específica.
        
        Args:
            run_id: ID de la ejecución
            
        Returns:
            Datos de la ejecución
            
        Raises:
            ValueError: Si la ejecución no existe
        """
        # Search for the run in the index
        index = self._load_runs_index()
        
        run_info = None
        for run in index.get('runs', []):
            if run['run_id'] == run_id:
                run_info = run
                break
        
        if not run_info:
            raise ValueError(f"Ejecución '{run_id}' no encontrada")
        
        # Load the full results file
        results_file = Path(run_info['file_path'])
        if not results_file.exists():
            raise ValueError(f"Archivo de resultados no encontrado: {results_file}")
        
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_runs(self, suite_filter: Optional[str] = None, 
                  agent_filter: Optional[str] = None, 
                  limit: int = 10) -> List[Dict[str, Any]]:
        """
        Listar ejecuciones recientes.
        
        Args:
            suite_filter: Filtrar por suite específica
            agent_filter: Filtrar por tipo de agente
            limit: Número máximo de resultados
            
        Returns:
            Lista de información de ejecuciones
        """
        index = self._load_runs_index()
        runs = index.get('runs', [])
        
        # Apply filters
        if suite_filter:
            runs = [r for r in runs if r['suite_name'] == suite_filter]
        
        if agent_filter:
            runs = [r for r in runs if r['agent_type'] == agent_filter]
        
        # Sort by timestamp (most recent first) and limit
        runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return runs[:limit]
    
    def delete_run_results(self, run_id: str) -> bool:
        """
        Eliminar resultados de una ejecución.
        
        Args:
            run_id: ID de la ejecución
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            # Find run in index
            index = self._load_runs_index()
            runs = index.get('runs', [])
            
            run_to_delete = None
            for run in runs:
                if run['run_id'] == run_id:
                    run_to_delete = run
                    break
            
            if not run_to_delete:
                return False
            
            # Delete file
            results_file = Path(run_to_delete['file_path'])
            if results_file.exists():
                results_file.unlink()
            
            # Remove from index
            index['runs'] = [r for r in runs if r['run_id'] != run_id]
            index['updated_at'] = datetime.now().isoformat()
            
            self._save_runs_index(index)
            
            return True
            
        except Exception as e:
            print(f"❌ Error eliminando ejecución: {e}")
            return False
    
    def generate_suite_summary(self, suite_name: str) -> Dict[str, Any]:
        """
        Generar resumen de todas las ejecuciones de una suite.
        
        Args:
            suite_name: Nombre de la suite
            
        Returns:
            Resumen de ejecuciones de la suite
        """
        # Get all runs for the suite
        runs = self.list_runs(suite_filter=suite_name, limit=100)
        
        if not runs:
            return {
                'suite_name': suite_name,
                'total_runs': 0,
                'error': 'No se encontraron ejecuciones para esta suite'
            }
        
        # Load detailed results for analysis
        detailed_results = []
        for run_info in runs:
            try:
                run_data = self.get_run_results(run_info['run_id'])
                detailed_results.append(run_data)
            except Exception as e:
                print(f"⚠️ Error cargando run {run_info['run_id']}: {e}")
                continue
        
        # Calculate summary statistics
        summary = {
            'suite_name': suite_name,
            'total_runs': len(detailed_results),
            'date_range': {
                'first_run': min(r['start_time'] for r in detailed_results),
                'last_run': max(r['start_time'] for r in detailed_results)
            },
            'agent_types': {},
            'success_rates': [],
            'execution_times': [],
            'question_performance': {},
            'trends': {}
        }
        
        # Aggregate statistics
        for run_data in detailed_results:
            # Agent type distribution
            agent_type = run_data['agent_type']
            summary['agent_types'][agent_type] = summary['agent_types'].get(agent_type, 0) + 1
            
            # Success rates and times
            success_rate = run_data['successful_questions'] / run_data['total_questions']
            summary['success_rates'].append(success_rate)
            summary['execution_times'].append(run_data['total_time'])
            
            # Question-level performance
            for result in run_data.get('results', []):
                question_id = result['question_id']
                if question_id not in summary['question_performance']:
                    summary['question_performance'][question_id] = {
                        'attempts': 0,
                        'successes': 0,
                        'avg_time': 0,
                        'times': []
                    }
                
                perf = summary['question_performance'][question_id]
                perf['attempts'] += 1
                if result['success']:
                    perf['successes'] += 1
                perf['times'].append(result['execution_time'])
        
        # Calculate averages for question performance
        for question_id in summary['question_performance']:
            perf = summary['question_performance'][question_id]
            perf['success_rate'] = perf['successes'] / perf['attempts']
            perf['avg_time'] = sum(perf['times']) / len(perf['times'])
            del perf['times']  # Remove raw times to save space
        
        # Overall statistics
        if summary['success_rates']:
            summary['overall_success_rate'] = sum(summary['success_rates']) / len(summary['success_rates'])
            summary['avg_execution_time'] = sum(summary['execution_times']) / len(summary['execution_times'])
        
        # Save summary
        summary_file = self.results_dir / "summaries" / f"{suite_name}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        return summary
    
    def export_results(self, run_ids: List[str], format: str = "json") -> Path:
        """
        Exportar resultados de múltiples ejecuciones.
        
        Args:
            run_ids: Lista de IDs de ejecuciones
            format: Formato de exportación ('json', 'csv')
            
        Returns:
            Path al archivo exportado
        """
        if format not in ['json', 'csv']:
            raise ValueError(f"Formato no soportado: {format}")
        
        # Collect all results
        export_data = []
        for run_id in run_ids:
            try:
                run_data = self.get_run_results(run_id)
                export_data.append(run_data)
            except Exception as e:
                print(f"⚠️ Error cargando run {run_id}: {e}")
                continue
        
        # Generate export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.{format}"
        export_path = self.results_dir / "exports" / filename
        
        if format == "json":
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        elif format == "csv":
            # Flatten results for CSV
            self._export_to_csv(export_data, export_path)
        
        print(f"📊 Resultados exportados a: {export_path}")
        return export_path
    
    def get_performance_trends(self, suite_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Analizar tendencias de performance para una suite.
        
        Args:
            suite_name: Nombre de la suite
            days: Número de días hacia atrás a analizar
            
        Returns:
            Análisis de tendencias
        """
        # Get recent runs
        runs = self.list_runs(suite_filter=suite_name, limit=100)
        
        # Filter by date range
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        recent_runs = []
        
        for run_info in runs:
            try:
                run_timestamp = datetime.fromisoformat(run_info['timestamp']).timestamp()
                if run_timestamp >= cutoff_date:
                    recent_runs.append(run_info)
            except (ValueError, KeyError):
                continue
        
        if not recent_runs:
            return {
                'suite_name': suite_name,
                'period_days': days,
                'runs_analyzed': 0,
                'error': 'No hay ejecuciones recientes en el período especificado'
            }
        
        # Load detailed data
        trend_data = []
        for run_info in recent_runs:
            try:
                run_data = self.get_run_results(run_info['run_id'])
                trend_data.append({
                    'timestamp': run_data['start_time'],
                    'success_rate': run_data['successful_questions'] / run_data['total_questions'],
                    'avg_execution_time': run_data['total_time'] / run_data['total_questions'],
                    'total_time': run_data['total_time']
                })
            except Exception:
                continue
        
        # Sort by timestamp
        trend_data.sort(key=lambda x: x['timestamp'])
        
        # Calculate trends
        trends = {
            'suite_name': suite_name,
            'period_days': days,
            'runs_analyzed': len(trend_data),
            'success_rate_trend': self._calculate_trend([d['success_rate'] for d in trend_data]),
            'execution_time_trend': self._calculate_trend([d['avg_execution_time'] for d in trend_data]),
            'data_points': trend_data
        }
        
        return trends
    
    def _update_runs_index(self, run_data: TestRun, file_path: Path) -> None:
        """Actualizar índice de ejecuciones."""
        index = self._load_runs_index()
        
        run_info = {
            'run_id': run_data.run_id,
            'suite_name': run_data.suite_name,
            'agent_type': run_data.agent_type.value,
            'timestamp': run_data.start_time.isoformat(),
            'total_questions': run_data.total_questions,
            'successful_questions': run_data.successful_questions,
            'success_rate': run_data.get_success_rate(),
            'total_time': run_data.total_time,
            'file_path': str(file_path)
        }
        
        # Add to index
        if 'runs' not in index:
            index['runs'] = []
        
        # Remove any existing entry with same run_id
        index['runs'] = [r for r in index['runs'] if r['run_id'] != run_data.run_id]
        index['runs'].append(run_info)
        
        # Update metadata
        index['updated_at'] = datetime.now().isoformat()
        index['total_runs'] = len(index['runs'])
        
        self._save_runs_index(index)
    
    def _load_runs_index(self) -> Dict[str, Any]:
        """Cargar índice de ejecuciones."""
        index_file = self.results_dir / "runs_index.json"
        
        if not index_file.exists():
            return {
                'runs': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'total_runs': 0
            }
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Return empty index if file is corrupted
            return {
                'runs': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'total_runs': 0
            }
    
    def _save_runs_index(self, index: Dict[str, Any]) -> None:
        """Guardar índice de ejecuciones."""
        index_file = self.results_dir / "runs_index.json"
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False, default=str)
    
    def _export_to_csv(self, export_data: List[Dict[str, Any]], export_path: Path) -> None:
        """Exportar datos a formato CSV."""
        import csv
        
        if not export_data:
            return
        
        # Flatten data for CSV
        flattened_data = []
        for run_data in export_data:
            base_info = {
                'run_id': run_data['run_id'],
                'suite_name': run_data['suite_name'],
                'agent_type': run_data['agent_type'],
                'start_time': run_data['start_time'],
                'total_questions': run_data['total_questions'],
                'successful_questions': run_data['successful_questions'],
                'total_time': run_data['total_time']
            }
            
            # Add question-level results
            for result in run_data.get('results', []):
                row = base_info.copy()
                row.update({
                    'question_id': result['question_id'],
                    'question_text': result['question_text'][:100] + '...' if len(result['question_text']) > 100 else result['question_text'],
                    'question_success': result['success'],
                    'question_execution_time': result['execution_time'],
                    'question_error': result.get('error', ''),
                    'response_length': len(result.get('agent_response', ''))
                })
                
                # Add metrics
                for key, value in result.get('metrics', {}).items():
                    if isinstance(value, (str, int, float, bool)):
                        row[f'metric_{key}'] = value
                
                flattened_data.append(row)
        
        # Write CSV
        if flattened_data:
            fieldnames = flattened_data[0].keys()
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened_data)
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calcular tendencia simple de una serie de valores."""
        if len(values) < 2:
            return {'trend': 'insufficient_data', 'slope': 0, 'direction': 'stable'}
        
        # Simple linear regression
        n = len(values)
        x_values = list(range(n))
        
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine trend direction
        if abs(slope) < 0.001:  # Threshold for "stable"
            direction = 'stable'
        elif slope > 0:
            direction = 'improving'
        else:
            direction = 'declining'
        
        return {
            'trend': direction,
            'slope': slope,
            'direction': direction,
            'confidence': 'low' if n < 5 else 'medium' if n < 10 else 'high'
        }