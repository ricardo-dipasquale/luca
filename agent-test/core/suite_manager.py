"""
Suite Manager - Gestión de suites de pruebas para agentes.

Maneja creación, modificación y consulta de suites de pruebas almacenadas
como archivos JSON en el filesystem.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..schemas import TestSuite, TestQuestion, AgentType, DifficultyLevel

class SuiteManager:
    """Gestor de suites de pruebas."""
    
    def __init__(self, suites_dir: Optional[str] = None):
        """
        Inicializar el gestor de suites.
        
        Args:
            suites_dir: Directorio donde almacenar las suites (default: agent-test/suites)
        """
        if suites_dir is None:
            # Get directory relative to this file
            current_dir = Path(__file__).parent.parent
            self.suites_dir = current_dir / "suites"
        else:
            self.suites_dir = Path(suites_dir)
        
        # Create directory if it doesn't exist
        self.suites_dir.mkdir(parents=True, exist_ok=True)
    
    def create_suite(self, name: str, agent_type: str, description: str = "") -> Path:
        """
        Crear una nueva suite de pruebas.
        
        Args:
            name: Nombre de la suite
            agent_type: Tipo de agente ('orchestrator', 'gapanalyzer', 'both')
            description: Descripción de la suite
            
        Returns:
            Path al archivo de la suite creada
            
        Raises:
            ValueError: Si la suite ya existe o parámetros inválidos
        """
        # Validate name
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("El nombre debe contener solo caracteres alfanuméricos, guiones y guiones bajos")
        
        # Check if suite already exists
        suite_file = self.suites_dir / f"{name}.json"
        if suite_file.exists():
            raise ValueError(f"La suite '{name}' ya existe")
        
        # Validate agent type
        try:
            agent_enum = AgentType(agent_type)
        except ValueError:
            raise ValueError(f"Tipo de agente inválido: {agent_type}")
        
        # Create suite object
        suite = TestSuite(
            name=name,
            description=description,
            agent_type=agent_enum,
            questions=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save to file
        self._save_suite(suite)
        
        return suite_file
    
    def add_question(self, suite_name: str, question_data: Dict[str, Any]) -> str:
        """
        Agregar una pregunta a una suite existente.
        
        Args:
            suite_name: Nombre de la suite
            question_data: Datos de la pregunta
            
        Returns:
            ID de la pregunta creada
            
        Raises:
            ValueError: Si la suite no existe o datos inválidos
        """
        # Load existing suite
        suite = self.get_suite(suite_name)
        
        # Generate question ID
        question_id = f"q_{uuid4().hex[:8]}"
        
        # Create question object
        question = TestQuestion(
            id=question_id,
            question=question_data['question'],
            expected_answer=question_data['expected_answer'],
            context=question_data.get('context'),
            subject=question_data.get('subject'),
            difficulty=DifficultyLevel(question_data.get('difficulty', 'medium')),
            metrics=question_data.get('metrics', {}),
            practice_id=question_data.get('practice_id'),
            exercise_section=question_data.get('exercise_section'),
            tags=question_data.get('tags', []),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add to suite
        suite_obj = TestSuite(**suite)
        suite_obj.questions.append(question)
        suite_obj.updated_at = datetime.now()
        
        # Save updated suite
        self._save_suite(suite_obj)
        
        return question_id
    
    def get_suite(self, name: str) -> Dict[str, Any]:
        """
        Obtener datos de una suite.
        
        Args:
            name: Nombre de la suite
            
        Returns:
            Datos de la suite como diccionario
            
        Raises:
            ValueError: Si la suite no existe
        """
        suite_file = self.suites_dir / f"{name}.json"
        if not suite_file.exists():
            raise ValueError(f"La suite '{name}' no existe")
        
        with open(suite_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_suites(self) -> List[Dict[str, Any]]:
        """
        Listar todas las suites disponibles.
        
        Returns:
            Lista de información básica de cada suite
        """
        suites = []
        
        for suite_file in self.suites_dir.glob("*.json"):
            try:
                with open(suite_file, 'r', encoding='utf-8') as f:
                    suite_data = json.load(f)
                
                suite_info = {
                    'name': suite_data['name'],
                    'description': suite_data.get('description', ''),
                    'agent_type': suite_data['agent_type'],
                    'question_count': len(suite_data.get('questions', [])),
                    'created': suite_data.get('created_at', ''),
                    'modified': suite_data.get('updated_at', ''),
                    'file_path': str(suite_file)
                }
                
                suites.append(suite_info)
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ Error leyendo suite {suite_file}: {e}")
                continue
        
        # Sort by modification date (most recent first)
        suites.sort(key=lambda x: x.get('modified', ''), reverse=True)
        
        return suites
    
    def update_suite(self, name: str, updates: Dict[str, Any]) -> None:
        """
        Actualizar una suite existente.
        
        Args:
            name: Nombre de la suite
            updates: Diccionario con campos a actualizar
            
        Raises:
            ValueError: Si la suite no existe
        """
        # Load existing suite
        suite_data = self.get_suite(name)
        suite = TestSuite(**suite_data)
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(suite, field):
                setattr(suite, field, value)
        
        suite.updated_at = datetime.now()
        
        # Save updated suite
        self._save_suite(suite)
    
    def delete_suite(self, name: str) -> bool:
        """
        Eliminar una suite.
        
        Args:
            name: Nombre de la suite
            
        Returns:
            True si se eliminó exitosamente
        """
        suite_file = self.suites_dir / f"{name}.json"
        if suite_file.exists():
            suite_file.unlink()
            return True
        return False
    
    def update_question(self, suite_name: str, question_id: str, updates: Dict[str, Any]) -> None:
        """
        Actualizar una pregunta específica en una suite.
        
        Args:
            suite_name: Nombre de la suite
            question_id: ID de la pregunta
            updates: Campos a actualizar
            
        Raises:
            ValueError: Si la suite o pregunta no existe
        """
        suite_data = self.get_suite(suite_name)
        suite = TestSuite(**suite_data)
        
        # Find and update question
        question_found = False
        for question in suite.questions:
            if question.id == question_id:
                for field, value in updates.items():
                    if hasattr(question, field):
                        setattr(question, field, value)
                question.updated_at = datetime.now()
                question_found = True
                break
        
        if not question_found:
            raise ValueError(f"Pregunta '{question_id}' no encontrada en suite '{suite_name}'")
        
        suite.updated_at = datetime.now()
        self._save_suite(suite)
    
    def remove_question(self, suite_name: str, question_id: str) -> bool:
        """
        Eliminar una pregunta de una suite.
        
        Args:
            suite_name: Nombre de la suite
            question_id: ID de la pregunta
            
        Returns:
            True si se eliminó exitosamente
        """
        suite_data = self.get_suite(suite_name)
        suite = TestSuite(**suite_data)
        
        # Find and remove question
        original_count = len(suite.questions)
        suite.questions = [q for q in suite.questions if q.id != question_id]
        
        if len(suite.questions) < original_count:
            suite.updated_at = datetime.now()
            self._save_suite(suite)
            return True
        
        return False
    
    def import_suite(self, file_path: str) -> str:
        """
        Importar una suite desde un archivo JSON.
        
        Args:
            file_path: Path al archivo JSON
            
        Returns:
            Nombre de la suite importada
            
        Raises:
            ValueError: Si el archivo es inválido
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"Archivo no encontrado: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            suite_data = json.load(f)
        
        # Validate suite data
        try:
            suite = TestSuite(**suite_data)
        except Exception as e:
            raise ValueError(f"Formato de suite inválido: {e}")
        
        # Check if suite already exists
        existing_file = self.suites_dir / f"{suite.name}.json"
        if existing_file.exists():
            # Generate unique name
            counter = 1
            while True:
                new_name = f"{suite.name}_imported_{counter}"
                new_file = self.suites_dir / f"{new_name}.json"
                if not new_file.exists():
                    suite.name = new_name
                    break
                counter += 1
        
        # Save imported suite
        self._save_suite(suite)
        
        return suite.name
    
    def export_suite(self, name: str, output_path: str) -> None:
        """
        Exportar una suite a un archivo JSON.
        
        Args:
            name: Nombre de la suite
            output_path: Path donde guardar el archivo
        """
        suite_data = self.get_suite(name)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(suite_data, f, indent=2, ensure_ascii=False, default=str)
    
    def validate_suite(self, name: str) -> Dict[str, Any]:
        """
        Validar una suite y reportar posibles problemas.
        
        Args:
            name: Nombre de la suite
            
        Returns:
            Diccionario con resultado de validación
        """
        try:
            suite_data = self.get_suite(name)
            suite = TestSuite(**suite_data)
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {
                    'name': suite.name,
                    'agent_type': suite.agent_type,
                    'question_count': len(suite.questions),
                    'subjects': list(set(q.subject for q in suite.questions if q.subject))
                }
            }
            
            # Validate questions
            if not suite.questions:
                validation_result['warnings'].append("Suite no tiene preguntas")
            
            question_ids = set()
            for question in suite.questions:
                # Check for duplicate IDs
                if question.id in question_ids:
                    validation_result['errors'].append(f"ID de pregunta duplicado: {question.id}")
                    validation_result['valid'] = False
                question_ids.add(question.id)
                
                # Check for empty questions
                if not question.question.strip():
                    validation_result['errors'].append(f"Pregunta vacía: {question.id}")
                    validation_result['valid'] = False
                
                if not question.expected_answer.strip():
                    validation_result['warnings'].append(f"Respuesta esperada vacía: {question.id}")
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Error validando suite: {e}"],
                'warnings': [],
                'summary': {}
            }
    
    def _save_suite(self, suite: TestSuite) -> None:
        """
        Guardar suite al filesystem.
        
        Args:
            suite: Objeto TestSuite a guardar
        """
        suite_file = self.suites_dir / f"{suite.name}.json"
        
        # Convert to dict for JSON serialization
        suite_dict = suite.model_dump()
        
        # Custom serialization for datetime objects
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(suite_file, 'w', encoding='utf-8') as f:
            json.dump(suite_dict, f, indent=2, ensure_ascii=False, default=serialize_datetime)
    
    def get_suite_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas generales de todas las suites.
        
        Returns:
            Diccionario con estadísticas
        """
        suites = self.list_suites()
        
        if not suites:
            return {
                'total_suites': 0,
                'total_questions': 0,
                'agent_types': {},
                'subjects': {},
                'difficulty_levels': {}
            }
        
        stats = {
            'total_suites': len(suites),
            'total_questions': sum(s['question_count'] for s in suites),
            'agent_types': {},
            'subjects': {},
            'difficulty_levels': {}
        }
        
        # Count by agent type
        for suite_info in suites:
            agent_type = suite_info['agent_type']
            stats['agent_types'][agent_type] = stats['agent_types'].get(agent_type, 0) + 1
        
        # Detailed analysis requires loading each suite
        for suite_info in suites:
            try:
                suite_data = self.get_suite(suite_info['name'])
                
                # Count subjects and difficulty levels
                for question in suite_data.get('questions', []):
                    subject = question.get('subject', 'Sin materia')
                    difficulty = question.get('difficulty', 'medium')
                    
                    stats['subjects'][subject] = stats['subjects'].get(subject, 0) + 1
                    stats['difficulty_levels'][difficulty] = stats['difficulty_levels'].get(difficulty, 0) + 1
                    
            except Exception:
                continue
        
        return stats