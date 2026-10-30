# Especificação Técnica: Ícones Rúnicos Game-Icons, Conduítes de Energia e Calibração de Nível por Aresta

**Data:** 26 de Outubro de 2026  
**Status:** Proposto / Em Aprovação  
**Contexto:** Árvore de Habilidades RPG (*Grimório & Forja Ancestral*)

---

## 1. Visão Geral e Objetivos

Este documento especifica três melhorias essenciais na usabilidade, imersão visual e profundidade pedagógica da Árvore de Habilidades:
1. **Ícones Rúnicos Autênticos (Game-Icons.net)**: Substituir emojis Unicode por 21 SVGs vetoriais de fantasia medieval renderizados em tons de bronze e ouro ancestral com auras de luz.
2. **Conduítes de Energia Rúnica no Canvas**: Eliminar o visual de fluxograma corporativo. As linhas curvas agora iniciam e terminam exatamente na borda externa dos medalhões (raio de 42px) com estilo de conduíte de éter luminoso (quando destrancadas) ou ferro forjado trancado, mantendo a linha limpa (sem badges flutuantes).
3. **Calibração de Nível Bloqueante por Aresta (A1, A3, B1...)**: Permitir que cada conexão defina individualmente qual nível o nó pai precisa ter para liberar o nó filho (ex: Nó C exige B no Nv. 1 e A no Nv. 3), acompanhado de um inspetor no Modo Forja para gerenciar as dependências.

---

## 2. Modelo de Dados & Domínio

### 2.1 Entidade `StudyEdge`
Em `src/domain/entities.py`:
```python
@dataclass
class StudyEdge:
    id: UUID = field(default_factory=uuid4)
    map_id: UUID = field(...)
    source_node_id: UUID = field(...)
    target_node_id: UUID = field(...)
    required_level: int = 1  # 1 a 6 (default: 1)
```

### 2.2 Regra de Domínio: `StudyTreeProgressionService.evaluate_unlock_status`
Em `src/domain/services.py`:
```python
@classmethod
def evaluate_unlock_status(
    cls,
    incoming_edges: Sequence[StudyEdge],
    prerequisites_levels: dict[UUID, int],
) -> bool:
    if not incoming_edges:
        return True

    for edge in incoming_edges:
        parent_level = prerequisites_levels.get(edge.source_node_id, 0)
        # O nó filho só destrava se o nó pai atingir o nível configurado nesta aresta
        if parent_level < edge.required_level:
            return False

    return True
```

### 2.3 Persistência (SQLAlchemy & Alembic)
- `StudyEdgeModel` em `src/adapters/persistence/models.py`:
  - `required_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)`
- Nova migração Alembic: `alembic/versions/e5f6a7b8c9d0_add_required_level_to_study_edges.py`.
- Mappers e Repositórios atualizados para serializar e salvar `required_level`.

---

## 3. Casos de Uso & Endpoints de API

### 3.1 DTOs
- `ConnectNodesDTO`: adicionado `required_level: int = 1`.
- `StudyEdgeDTO`: adicionado `required_level: int = 1`.
- `UpdateStudyEdgeDTO`: `required_level: int`.

### 3.2 Casos de Uso
- `ConnectStudyNodesUseCase`: persiste `required_level`.
- `UpdateStudyEdgeUseCase`: permite alterar o `required_level` de uma aresta existente.
- `GetStudyMapGraphUseCase`: retorna `required_level` de cada aresta.

### 3.3 Endpoints REST
- `POST /api/v1/study-maps/{map_id}/edges`: aceita `required_level` (default 1).
- `PATCH /api/v1/study-maps/{map_id}/edges/{edge_id}`: atualiza `required_level`.
- `DELETE /api/v1/study-maps/{map_id}/edges/{edge_id}`: remove a conexão.

---

## 4. Frontend & Design Visual

### 4.1 Ícones Game-Icons.net (21 Ícones Vetoriais)
Dicionário vetorial SVG embutido e estilizado com filtros dourados (`#f0c869` / `#c89b3c`):
- `calculator` -> Ábaco Arcano / Geometria Sagrada
- `trending-up` -> Flecha de Ascensão Mística
- `dice` -> Dado Poliédrico D20
- `activity` -> Pulso de Éter
- `brain` -> Runa da Mente / Intelecto
- `book` -> Grimório Ancestral com Fecho
- `code` -> Matriz Rúnica / Glifos
- `cpu` -> Núcleo de Golem / Engrenagem Mágica
- `database` -> Cofre de Cristais de Mana
- `globe` -> Orbe Planar
- `layers` -> Estratos Elementais
- `shield` -> Égide de Cavaleiro
- `terminal` -> Espelho de Vidência
- `zap` -> Raio Sagrado
- `award` -> Medalhão de Láurea
- `compass` -> Astrolábio Arcano
- `feather` -> Pena de Fênix
- `flame` -> Tocha Alquímica
- `key` -> Chave Esqueleto
- `scroll` -> Pergaminho Selado
- `sword` -> Espada Rúnica

### 4.2 Geometria dos Conduítes no Canvas (`study_canvas.js`)
- Cálculo trigonométrico do vetor diretor de $\vec{S}$ para $\vec{T}$:
  $$D = \sqrt{(tx - sx)^2 + (ty - sy)^2}$$
  $$ux = \frac{tx - sx}{D}, \quad uy = \frac{ty - sy}{D}$$
  $$\text{início} = (sx + 42 \cdot ux, \quad sy + 42 \cdot uy)$$
  $$\text{fim} = (tx - 42 \cdot ux, \quad ty - 42 \cdot uy)$$
- Linha limpa (sem rótulos poluindo o gráfico):
  - **Destrancado:** Traço contínuo dourado (`stroke-width: 3.5px`, gradiente `#f0c869` $\rightarrow$ `#c89b3c`, `drop-shadow(0 0 6px rgba(240, 200, 105, 0.7))`).
  - **Trancado:** Traço pontilhado em ferro forjado escuro (`#3b322c`, `stroke-dasharray: 6,6`).
  - **Terminador:** Losango rúnico sutil na ponta em contato com a borda.

### 4.3 Inspetor de Pré-requisitos (Modo Forja)
No painel lateral do **Modo Forja**:
- Seção **🔗 Pré-requisitos & Bloqueios do Nó**:
  - Lista todos os nós ancestrais que bloqueiam este nó.
  - Para cada nó ancestral: exibe o nome e um seletor:
    `Exigir: [ Nv. 1 | Nv. 2 | Nv. 3 | Nv. 4 ]`
  - Botão de lixeira para remover o pré-requisito.
  - Seletor `+ Adicionar Pré-requisito`: escolhe outro nó do mapa e o nível requerido.

### 4.4 Informação no Grimório do Nó (`node_grimoire.html`)
No cabeçalho do Grimório do Nó:
- Se estiver bloqueado, exibe os requisitos exatos:  
  `🔒 Selado — Requer: Álgebra Linear (Nv. 1), Fundamentos de Matemática (Nv. 3)`
