#!/usr/bin/env python3
"""
LUCA Agent Testing CLI

Sistema de línea de comandos para gestionar y ejecutar suites de pruebas
para los agentes educativos de LUCA.

Usage:
    python -m agent-test.cli suite create <name> [--agent=orchestrator|gapanalyzer]
    python -m agent-test.cli suite add-question <suite_name> --question="..." --expected="..." [--metrics="..."]
    python -m agent-test.cli suite list
    python -m agent-test.cli suite show <name>
    
    python -m agent-test.cli dataset upload <suite_name> [--name="..."]
    python -m agent-test.cli dataset list
    
    python -m agent-test.cli run <suite_name> [--agent=orchestrator|gapanalyzer] [--iterations=1]
    python -m agent-test.cli run-all [--iterations=1]
    
    python -m agent-test.cli results show <run_id>
    python -m agent-test.cli results list [--suite=<name>]
"""

import click
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root and current directory to path
project_root = Path(__file__).parent.parent
current_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

from core.suite_manager import SuiteManager
from core.langfuse_integration import LangfuseManager
from core.test_runner import TestRunner
from core.results_manager import ResultsManager
from schemas import AgentType, DifficultyLevel

@click.group()
def cli():
    """LUCA Agent Testing Framework - Sistema de evaluación para agentes educativos."""
    pass

@cli.group()
def suite():
    """Gestionar suites de pruebas."""
    pass

@suite.command()
@click.argument('name')
@click.option('--agent', type=click.Choice(['orchestrator', 'gapanalyzer', 'both']), 
              default='orchestrator', help='Tipo de agente a testear')
@click.option('--description', default='', help='Descripción de la suite')
def create(name: str, agent: str, description: str):
    """Crear una nueva suite de pruebas."""
    manager = SuiteManager()
    
    try:
        suite_path = manager.create_suite(name, agent, description)
        click.echo(f"✅ Suite '{name}' creada exitosamente en {suite_path}")
        click.echo(f"   Agente: {agent}")
        if description:
            click.echo(f"   Descripción: {description}")
    except Exception as e:
        click.echo(f"❌ Error creando suite: {e}")
        sys.exit(1)

@suite.command()
@click.argument('suite_name')
@click.option('--question', required=True, help='Pregunta de prueba')
@click.option('--expected', required=True, help='Respuesta esperada o criterios')
@click.option('--context', help='Contexto adicional para la pregunta')
@click.option('--metrics', help='Métricas específicas a evaluar (JSON)')
@click.option('--subject', help='Materia educativa')
@click.option('--difficulty', type=click.Choice(['easy', 'medium', 'hard']), 
              default='medium', help='Nivel de dificultad')
def add_question(suite_name: str, question: str, expected: str, context: str, 
                metrics: str, subject: str, difficulty: str):
    """Agregar una pregunta a una suite existente."""
    manager = SuiteManager()
    
    try:
        # Parse metrics if provided
        metrics_dict = {}
        if metrics:
            metrics_dict = json.loads(metrics)
        
        question_data = {
            'question': question,
            'expected_answer': expected,
            'context': context,
            'metrics': metrics_dict,
            'subject': subject,
            'difficulty': difficulty
        }
        
        manager.add_question(suite_name, question_data)
        click.echo(f"✅ Pregunta agregada a suite '{suite_name}'")
        
    except json.JSONDecodeError:
        click.echo("❌ Error: Formato JSON inválido en --metrics")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error agregando pregunta: {e}")
        sys.exit(1)

@suite.command()
def list():
    """Listar todas las suites disponibles."""
    manager = SuiteManager()
    suites = manager.list_suites()
    
    if not suites:
        click.echo("📭 No hay suites de pruebas disponibles.")
        return
    
    click.echo("📋 Suites de pruebas disponibles:")
    click.echo("")
    
    for suite_info in suites:
        click.echo(f"  🧪 {suite_info['name']}")
        click.echo(f"     Agente: {suite_info['agent_type']}")
        click.echo(f"     Preguntas: {suite_info['question_count']}")
        if suite_info['description']:
            click.echo(f"     Descripción: {suite_info['description']}")
        click.echo(f"     Modificada: {suite_info['modified']}")
        click.echo("")

@suite.command()
@click.argument('name')
def show(name: str):
    """Mostrar detalles de una suite específica."""
    manager = SuiteManager()
    
    try:
        suite_data = manager.get_suite(name)
        
        click.echo(f"🧪 Suite: {suite_data['name']}")
        click.echo(f"   Agente: {suite_data['agent_type']}")
        click.echo(f"   Descripción: {suite_data.get('description', 'Sin descripción')}")
        click.echo(f"   Creada: {suite_data['created_at']}")
        click.echo(f"   Modificada: {suite_data['updated_at']}")
        click.echo("")
        
        questions = suite_data['questions']
        click.echo(f"📝 Preguntas ({len(questions)}):")
        
        for i, q in enumerate(questions, 1):
            click.echo(f"   {i}. {q['question']}")
            click.echo(f"      Esperado: {q['expected_answer'][:100]}...")
            if q.get('subject'):
                click.echo(f"      Materia: {q['subject']}")
            click.echo(f"      Dificultad: {q.get('difficulty', 'medium')}")
            if q.get('metrics'):
                click.echo(f"      Métricas: {list(q['metrics'].keys())}")
            click.echo("")
            
    except Exception as e:
        click.echo(f"❌ Error mostrando suite: {e}")
        sys.exit(1)

@cli.group()
def dataset():
    """Gestionar datasets en Langfuse."""
    pass

@dataset.command()
@click.argument('suite_name')
@click.option('--name', help='Nombre del dataset en Langfuse (default: suite_name)')
@click.option('--description', help='Descripción del dataset')
def upload(suite_name: str, name: str, description: str):
    """Subir suite como dataset a Langfuse."""
    suite_manager = SuiteManager()
    langfuse_manager = LangfuseManager()
    
    try:
        # Get suite data
        suite_data = suite_manager.get_suite(suite_name)
        
        # Use suite name if no custom name provided
        dataset_name = name or suite_name
        dataset_description = description or suite_data.get('description', f'Dataset from suite {suite_name}')
        
        # Upload to Langfuse
        dataset_id = langfuse_manager.upload_dataset(
            name=dataset_name,
            description=dataset_description,
            suite_data=suite_data
        )
        
        click.echo(f"✅ Dataset '{dataset_name}' subido a Langfuse")
        click.echo(f"   ID: {dataset_id}")
        click.echo(f"   Items: {len(suite_data['questions'])}")
        
    except Exception as e:
        click.echo(f"❌ Error subiendo dataset: {e}")
        sys.exit(1)

@dataset.command()
def list():
    """Listar datasets en Langfuse."""
    langfuse_manager = LangfuseManager()
    
    try:
        datasets = langfuse_manager.list_datasets()
        
        if not datasets:
            click.echo("📭 No hay datasets en Langfuse.")
            return
        
        click.echo("📊 Datasets en Langfuse:")
        click.echo("")
        
        for dataset in datasets:
            click.echo(f"  📈 {dataset['name']}")
            click.echo(f"     ID: {dataset['id']}")
            click.echo(f"     Items: {dataset['item_count']}")
            if dataset.get('description'):
                click.echo(f"     Descripción: {dataset['description']}")
            click.echo(f"     Creado: {dataset['created_at']}")
            click.echo("")
            
    except Exception as e:
        click.echo(f"❌ Error listando datasets: {e}")
        sys.exit(1)

@cli.command()
@click.argument('suite_name')
@click.option('--agent', type=click.Choice(['orchestrator', 'gapanalyzer', 'both']), 
              help='Agente específico a testear (override suite default)')
@click.option('--iterations', default=1, help='Número de iteraciones por pregunta')
@click.option('--session-id', help='ID de sesión personalizada')
@click.option('--run-name', help='Nombre personalizado para este run (aparece en Langfuse)')
def run(suite_name: str, agent: str, iterations: int, session_id: str, run_name: str):
    """Ejecutar una suite de pruebas."""
    runner = TestRunner()
    
    try:
        click.echo(f"🚀 Ejecutando suite '{suite_name}'...")
        
        results = runner.run_suite(
            suite_name=suite_name,
            agent_override=agent,
            iterations=iterations,
            session_id=session_id,
            run_name=run_name
        )
        
        click.echo(f"✅ Ejecución completada")
        click.echo(f"   Run ID: {results['run_id']}")
        click.echo(f"   Preguntas procesadas: {results['total_questions']}")
        click.echo(f"   Tiempo total: {results['total_time']:.2f}s")
        click.echo(f"   Resultados en: {results['results_file']}")
        
        # Show basic metrics
        if results.get('summary'):
            summary = results['summary']
            click.echo("")
            click.echo("📊 Resumen de métricas:")
            for metric, value in summary.items():
                click.echo(f"   {metric}: {value}")
        
    except Exception as e:
        click.echo(f"❌ Error ejecutando suite: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.option('--iterations', default=1, help='Número de iteraciones por pregunta')
@click.option('--agent-filter', type=click.Choice(['orchestrator', 'gapanalyzer']), 
              help='Filtrar por tipo de agente')
@click.option('--run-name-prefix', help='Prefijo para nombres de runs (se agrega timestamp automáticamente)')
def run_all(iterations: int, agent_filter: str, run_name_prefix: str):
    """Ejecutar todas las suites disponibles."""
    suite_manager = SuiteManager()
    runner = TestRunner()
    
    try:
        suites = suite_manager.list_suites()
        
        if agent_filter:
            suites = [s for s in suites if s['agent_type'] == agent_filter or s['agent_type'] == 'both']
        
        if not suites:
            click.echo("📭 No hay suites para ejecutar.")
            return
        
        click.echo(f"🚀 Ejecutando {len(suites)} suites...")
        
        all_results = []
        
        for suite_info in suites:
            click.echo(f"   Ejecutando {suite_info['name']}...")
            
            # Generate run name with prefix and timestamp if provided
            suite_run_name = None
            if run_name_prefix:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suite_run_name = f"{run_name_prefix}_{suite_info['name']}_{timestamp}"
            
            results = runner.run_suite(
                suite_name=suite_info['name'],
                iterations=iterations,
                run_name=suite_run_name
            )
            
            all_results.append(results)
            click.echo(f"   ✅ {suite_info['name']} completada (Run ID: {results['run_id']})")
        
        click.echo("")
        click.echo(f"🎉 Todas las suites ejecutadas exitosamente!")
        click.echo(f"   Total de runs: {len(all_results)}")
        
        # Show summary
        total_questions = sum(r['total_questions'] for r in all_results)
        total_time = sum(r['total_time'] for r in all_results)
        
        click.echo(f"   Total de preguntas: {total_questions}")
        click.echo(f"   Tiempo total: {total_time:.2f}s")
        
    except Exception as e:
        click.echo(f"❌ Error ejecutando suites: {e}")
        sys.exit(1)

@cli.group()
def results():
    """Gestionar resultados de ejecuciones."""
    pass

@results.command()
@click.argument('run_id')
def show(run_id: str):
    """Mostrar detalles de una ejecución específica."""
    results_manager = ResultsManager()
    
    try:
        run_data = results_manager.get_run_results(run_id)
        
        click.echo(f"📊 Run: {run_data['run_id']}")
        click.echo(f"   Suite: {run_data['suite_name']}")
        click.echo(f"   Agente: {run_data['agent_type']}")
        click.echo(f"   Ejecutado: {run_data['timestamp']}")
        click.echo(f"   Duración: {run_data['total_time']:.2f}s")
        click.echo("")
        
        # Show results per question
        results_list = run_data['results']
        click.echo(f"📝 Resultados por pregunta ({len(results_list)}):")
        
        for i, result in enumerate(results_list, 1):
            click.echo(f"   {i}. {result['question'][:80]}...")
            click.echo(f"      Tiempo: {result['execution_time']:.2f}s")
            click.echo(f"      Estado: {'✅' if result['success'] else '❌'}")
            
            if result.get('metrics'):
                click.echo(f"      Métricas: {result['metrics']}")
            
            if not result['success'] and result.get('error'):
                click.echo(f"      Error: {result['error']}")
            
            click.echo("")
        
        # Show summary metrics
        if run_data.get('summary'):
            click.echo("📈 Resumen de métricas:")
            for metric, value in run_data['summary'].items():
                click.echo(f"   {metric}: {value}")
        
    except Exception as e:
        click.echo(f"❌ Error mostrando resultados: {e}")
        sys.exit(1)

@results.command()
@click.option('--suite', help='Filtrar por suite específica')
@click.option('--agent', type=click.Choice(['orchestrator', 'gapanalyzer']), 
              help='Filtrar por tipo de agente')
@click.option('--limit', default=10, help='Número máximo de resultados')
def list(suite: str, agent: str, limit: int):
    """Listar ejecuciones recientes."""
    results_manager = ResultsManager()
    
    try:
        runs = results_manager.list_runs(
            suite_filter=suite,
            agent_filter=agent,
            limit=limit
        )
        
        if not runs:
            click.echo("📭 No hay ejecuciones disponibles.")
            return
        
        click.echo("📋 Ejecuciones recientes:")
        click.echo("")
        
        for run in runs:
            click.echo(f"  🏃 {run['run_id']}")
            click.echo(f"     Suite: {run['suite_name']}")
            click.echo(f"     Agente: {run['agent_type']}")
            click.echo(f"     Ejecutado: {run['timestamp']}")
            click.echo(f"     Preguntas: {run['total_questions']}")
            click.echo(f"     Duración: {run['total_time']:.2f}s")
            
            if run.get('success_rate'):
                click.echo(f"     Éxito: {run['success_rate']:.1%}")
            
            click.echo("")
    
    except Exception as e:
        click.echo(f"❌ Error listando ejecuciones: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()