"""
Orchestrator Agent - Main Entry Point

CLI and server entry point for the Orchestrator Agent, supporting both
standalone execution and A2A framework integration.
"""

import asyncio
import logging
import sys
from typing import Optional

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from .agent_executor import OrchestratorAgentExecutor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']


class OrchestratorA2AExecutor(AgentExecutor):
    """Thin A2A-protocol wrapper around OrchestratorAgentExecutor."""

    def __init__(self):
        self._executor = OrchestratorAgentExecutor()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)  # type: ignore[arg-type]
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)

        try:
            async for item in self._executor.stream(
                request={'message': query},
                context={'session_id': task.contextId, 'user_id': 'a2a_user'},
            ):
                is_complete = item.get('is_task_complete', False)
                needs_input = item.get('require_user_input', False)

                if needs_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(item['content'], task.contextId, task.id),
                        final=True,
                    )
                    break
                elif is_complete:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='orchestrator_response',
                    )
                    await updater.complete()
                    break
                else:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(item['content'], task.contextId, task.id),
                    )
        except Exception as e:
            logger.error(f'Orchestrator streaming error: {e}')
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())


@click.command()
@click.option('--host', default='localhost', help='Host to bind the server')
@click.option('--port', default=10001, help='Port to bind the server')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--test-message', help='Test the agent with a direct message')
@click.option('--session-id', help='Session ID for testing')
def main(host: str, port: int, debug: bool, test_message: Optional[str], session_id: Optional[str]):
    """Orchestrator Agent - Educational Conversation Manager"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if test_message:
        asyncio.run(_test_agent(test_message, session_id))
    else:
        _run_server(host, port)


async def _test_agent(message: str, session_id: Optional[str] = None):
    executor = OrchestratorAgentExecutor()
    print(f"Testing Orchestrator | message={message!r} | session={session_id or 'test_session'}")
    async for chunk in executor.stream(
        request={'message': message},
        context={'session_id': session_id or 'test_session', 'user_id': 'test_user'},
    ):
        if chunk.get('is_task_complete'):
            print(f"\nFinal response:\n{chunk.get('content', '')}")
            break
        else:
            print(f"  {chunk.get('content', 'Processing...')}")


def _run_server(host: str, port: int):
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id='educational_conversation',
        name='Educational Conversation Orchestrator',
        description='Manages educational conversations, classifies student intent, and coordinates specialized agents',
        tags=['education', 'orchestrator', 'conversation', 'learning'],
        examples=[
            '¿Qué es un LEFT JOIN?',
            'No entiendo el ejercicio 1.a de la práctica 2',
            '¿Cuáles son las formas normales en bases de datos?',
        ],
    )
    agent_card = AgentCard(
        name='Orchestrator Agent',
        description='Educational AI that manages multi-turn conversations, classifies intent, and coordinates the LUCA agent ecosystem',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )

    httpx_client = httpx.AsyncClient()
    request_handler = DefaultRequestHandler(
        agent_executor=OrchestratorA2AExecutor(),
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(httpx_client),
    )
    server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    logger.info(f'Starting Orchestrator Agent server on {host}:{port}')
    uvicorn.run(server.build(), host=host, port=port)


if __name__ == '__main__':
    main()
