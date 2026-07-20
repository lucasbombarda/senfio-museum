# Museu de Cheiros Desaparecidos API

Li as BRs, o contrato (`API.md`) e o backlog, confrontei com o código e corrigi
o que tinha de bugs reais, em commits pequenos com teste.
Prioridade: risco sobre volume.

## O que corrigi (3 fixes)

- **Trilha somente leitura (BR-005):** `StatusChangeViewSet` era gravável, virou
  `ReadOnlyModelViewSet`. Alinha com o contrato e a imutabilidade da trilha.
- **Disponibilidade + concorrência da reserva (BR-001):** a validação só barrava
  `checked_out`; troquei por `status != available`, que cobre quarentena, reserva
  ativa e aposentadoria. Adicionei `UniqueConstraint` parcial que garante uma
  única reserva ativa por cápsula mesmo sob concorrência.
- **Webhook idempotente (BR-003):** duplicava evento a cada request; agora tem
  `unique(source, event_id)` e retorna o existente sem reprocessar.

## O que construí (1 feature)

- **Endpoint de devolução (BR-006):** `POST /reservations/{id}/return/`. Só
  devolve reserva `checked_out`; sem dano a cápsula volta para `available`; com
  dano vai para `quarantine` e registra inspeção. Fecha o ciclo da reserva.

Tudo com teste, passando no `make ci-check`.

## O que ficou de fora (e por quê)

- **Auth + permissões (BR-004/008):** dependem de um mecanismo de autenticação
  que resolva a request para um perfil. Sem ele, só o caso "negado" é testável.
  Escopo maior, é o próximo pacote.
- **Expiração automática (BR-006):** é processo recorrente (cron), não endpoint.
- **Timeline, relatórios, paginação (BR-007/008):** backlog de menor risco.
