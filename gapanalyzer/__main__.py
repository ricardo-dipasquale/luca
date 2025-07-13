import logging
import os
import sys

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from gapanalyzer.agent import GapAnalyzerAgent
from gapanalyzer.agent_executor import GapAnalyzerAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """Starts the Gap Analyzer Agent server."""
    try:
        # Check for OpenAI API key (default provider)
        if not os.getenv('OPENAI_API_KEY'):
            raise MissingAPIKeyError(
                'OPENAI_API_KEY environment variable not set.'
            )

        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id='analyze_learning_gaps',
            name='Educational Gap Analyzer',
            description='Analyzes student questions about practice exercises to identify learning gaps and provide prioritized recommendations',
            tags=['education', 'learning analysis', 'gap analysis', 'pedagogical assessment'],
            examples=[
                'No entiendo por qué esta consulta SQL no devuelve los resultados esperados',
                'Tengo dudas sobre el ejercicio 3 de la práctica 2 de bases de datos',
                '¿Por qué mi JOIN no funciona correctamente?'
            ],
        )
        agent_card = AgentCard(
            name='Gap Analyzer Agent',
            description='Educational AI tutor that analyzes student questions to identify learning gaps and provides prioritized recommendations for improvement',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=GapAnalyzerAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=GapAnalyzerAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=GapAnalyzerAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_notifier=InMemoryPushNotifier(httpx_client),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
