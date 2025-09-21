import logging

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    # --8<-- [start:A2ACardResolver]

    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        # --8<-- [end:A2ACardResolver]

        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}'
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('Successfully fetched public agent card:')
            logger.info(
                _public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = _public_card
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

            if _public_card.supportsAuthenticatedExtendedCard:
                try:
                    logger.info(
                        '\nPublic card supports authenticated extended card. '
                        'Attempting to fetch from: '
                        f'{base_url}{EXTENDED_AGENT_CARD_PATH}'
                    )
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    logger.info(
                        'Successfully fetched authenticated extended agent card:'
                    )
                    logger.info(
                        _extended_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card_to_use = (
                        _extended_card  # Update to use the extended card
                    )
                    logger.info(
                        '\nUsing AUTHENTICATED EXTENDED agent card for client '
                        'initialization.'
                    )
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,
                    )
            elif (
                _public_card
            ):  # supportsAuthenticatedExtendedCard is False or None
                logger.info(
                    '\nPublic card does not indicate support for an extended card. Using public card.'
                )

        except Exception as e:
            logger.error(
                f'Critical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                'Failed to fetch the public agent card. Cannot continue.'
            ) from e

        # --8<-- [start:send_message]
        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info('A2AClient initialized.')

        # Example with structured StudentContext for gap analysis
        student_context_json = '''{
            "student_question": "No entiendo por qué mi consulta SQL con LEFT JOIN no me trae los clientes que no han comprado nada",
            "conversation_history": [
                {
                    "role": "student",
                    "content": "Estoy trabajando en el ejercicio 1.d de la práctica 2"
                },
                {
                    "role": "assistant",
                    "content": "Te ayudo con el ejercicio 1.d. ¿Podrías mostrarme tu consulta actual?"
                },
                {
                    "role": "student",
                    "content": "Mi consulta devuelve filas duplicadas y no los resultados esperados"
                }
            ],
            "subject_name": "Bases de Datos Relacionales",
            "practice_context": "Práctica: 2 - Algebra Relacional: Resolución de ejercicios en Algebra Relacional. Existen preguntas conceptuales que están relacionados. Objetivo: Que los alumnos sean capaces de resolver situaciones problemáticas con álgebra relacional utilizando los preceptos dados en clase. Temas cubiertos: - Modelo Relacional - Algebra relacional: Operaciones, Práctica - Lenguajes relacionalmente completos - Consultas Algebra relacional",
            "exercise_context": "Ejercicio: 1.d - Nombre de los clientes que no han comprado nada. Enunciado: Dado el siguiente esquema relacional de base de datos, resolver en álgebra relacional. Las claves de denotan con (clave): - CLIENTES (Nº Cliente (clave), Nombre, Dirección, Teléfono, Ciudad) - PRODUCTO(Cod Producto (clave), Descripción, Precio) - VENTA(Cod Producto, Nº Cliente, Cantidad, Id Venta (clave))",
            "solution_context": "Solución esperada: [π_{Nombre} (π_{Nº Cliente,Nombre} (CLIENTES) − π_{Nº Cliente,Nombre} (CLIENTES ⋈_{CLIENTES.Nº Cliente=VENTA.Nº Cliente} VENTA))]",
            "tips_context": "Tips nivel práctica: - Pensar bien qué operación (o juego de operaciones) es central en la resolución del ejercicio. - No confundir la semántica de las operaciones: Por ejemplo, si un problema tiene en su esencia la resolución de una diferencia de conjuntos, se espera que que el alumno utilice la diferencia de conjuntos y no otros caminos como por ejemplo la selección sobre un subconjunto del producto cartesiano, la selección de los outer join nulos, etc. Tips nivel ejercicio: - Tener en cuenta que puede haber varias respuestas similares y están bien - Los alumnos tienden a simplificar y a hacer una diferencia de conjuntos utilizando únicamente la proyección por el nombre del cliente. Esto presenta un problema porque en ningún lugar dijimos que el Nombre es único."
        }'''

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': student_context_json}
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:send_message]

        # --8<-- [start:Multiturn]
        send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {
                        'kind': 'text',
                        'text': 'How much is the exchange rate for 1 USD?',
                    }
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload_multiturn),
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        task_id = response.root.result.id
        contextId = response.root.result.contextId

        second_send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'CAD'}],
                'messageId': uuid4().hex,
                'taskId': task_id,
                'contextId': contextId,
            },
        }

        second_request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**second_send_message_payload_multiturn),
        )
        second_response = await client.send_message(second_request)
        print(second_response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:Multiturn]

        # --8<-- [start:send_message_streaming]

        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:send_message_streaming]


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
