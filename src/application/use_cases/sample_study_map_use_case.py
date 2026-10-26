"""Caso de uso para geração automática da Árvore Modelo de Matemática Aplicada & Computacional."""

from typing import Any
from uuid import UUID

from src.application.ports.repositories import (
    IFlashcardRepository,
    IKnowledgeSourceRepository,
    INodeContentRepository,
    IQuestionRepository,
    IStudyEdgeRepository,
    IStudyMapRepository,
    IStudyNodeRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import (
    Flashcard,
    KnowledgeSource,
    Question,
    StudyEdge,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
)


class CreateSampleMathStudyMapUseCase:
    """Cria uma Árvore de Conhecimento RPG completa com nós, pré-requisitos, materiais, flashcards e perguntas."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        edge_repo: IStudyEdgeRepository,
        content_repo: INodeContentRepository,
        source_repo: IKnowledgeSourceRepository,
        question_repo: IQuestionRepository,
        flashcard_repo: IFlashcardRepository,
        subject_repo: ISubjectRepository,
        topic_repo: ITopicRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.edge_repo = edge_repo
        self.content_repo = content_repo
        self.source_repo = source_repo
        self.question_repo = question_repo
        self.flashcard_repo = flashcard_repo
        self.subject_repo = subject_repo
        self.topic_repo = topic_repo

    def execute(self, user_id: UUID) -> StudyMap:
        # 1. Cria Matéria e Tópicos no domínio para garantir integridade referencial
        subject = Subject(
            owner_id=user_id,
            name="Matemática Aplicada & Computacional",
        )
        self.subject_repo.save(subject)

        # 2. Mapa de Estudos Raiz
        study_map = self.map_repo.save(
            StudyMap(
                owner_id=user_id,
                title="Matemática Aplicada & Computacional",
                description=(
                    "Trilha estruturada em grafo RPG cobrindo Álgebra Linear Computacional, "
                    "Cálculo Diferencial Vetorial, Simulação Estocástica de Monte Carlo, "
                    "Equações Diferenciais Ordinárias (EDOs) e Otimização para Machine Learning."
                ),
                is_public=False,
            )
        )

        # 3. Especificação didática dos 5 Nós e seus conteúdos
        nodes_spec: list[dict[str, Any]] = [
            {
                "key": "linear_algebra",
                "title": "Álgebra Linear Computacional",
                "description": "Vetores, matrizes, transformações lineares, eliminação gaussiana e decomposições matriciais (LU, QR, SVD).",
                "pos_x": 120.0,
                "pos_y": 260.0,
                "icon": "calculator",
                "theory_content": (
                    "# Álgebra Linear Computacional\n\n"
                    "A Álgebra Linear Computacional é a espinha dorsal da computação científica moderna e dos "
                    "motores de Inteligência Artificial. Diferente da abordagem puramente teórica, a vertente computacional "
                    "investiga a representação vetorial em memória, condicionamento numérico e estabilidade de algoritmos.\n\n"
                    "## 1. Espaços Vetoriais e Transformações Lineares\n"
                    "Um espaço vetorial $\\mathbb{R}^n$ fornece o alicerce para armazenar tensores de parâmetros e características. "
                    "Toda transformação linear $T: \\mathbb{R}^n \\to \\mathbb{R}^m$ é unicamente parametrizada por uma matriz "
                    "$A \\in \\mathbb{R}^{m \\times n}$. Transformações ortogonais ($Q^T Q = I$) preservam comprimentos e ângulos euclidianos.\n\n"
                    "## 2. Condicionamento Numérico e Estabilidade\n"
                    "Ao resolver o sistema linear fundamental $Ax = b$, a sensibilidade da solução a perturbações é descrita pelo "
                    "**Número de Condição**: $\\kappa(A) = ||A|| \\cdot ||A^{-1}||$. Matrizes mal-condicionadas exigem cuidados "
                    "com erros de arredondamento e técnicas de regularização.\n\n"
                    "## 3. Fatorações Matriciais Essenciais\n"
                    "- **Decomposição LU ($PA = LU$):** Transforma a resolução em etapas de substituição direta e retrosubstituição $\\mathcal{O}(n^2)$.\n"
                    "- **Fatoração QR ($A = QR$):** Viabiliza problemas de mínimos quadrados com colunas ortonormais.\n"
                    "- **Decomposição em Valores Singulares (SVD, $A = U \\Sigma V^T$):** Permite aproximações de posto baixo e análise espectral profunda."
                ),
                "material": (
                    "Fundamentos de Álgebra Linear Computacional e Fatorações",
                    "A álgebra linear computacional constitui a espinha dorsal da computação científica moderna e do aprendizado de máquina. Aborda a representação de dados em espaços vetoriais euclidianos, condicionamento numérico e resolução eficiente de sistemas lineares Ax = b.",
                ),
                "flashcards": [
                    (
                        "O que caracteriza uma matriz ortogonal Q e qual sua propriedade em relação à transposta?",
                        "Uma matriz quadrada Q é ortogonal se Qᵀ·Q = Q·Qᵀ = I, ou seja, Q⁻¹ = Qᵀ. Ela preserva comprimentos euclidianos e ângulos (isometria).",
                    ),
                    (
                        "O que representa o posto (rank) de uma matriz?",
                        "O número máximo de vetores-linha ou vetores-coluna linearmente independentes na matriz, determinando a dimensionalidade de sua imagem.",
                    ),
                    (
                        "Qual é a principal vantagem prática da Decomposição LU na resolução de sistemas lineares A·x = b?",
                        "Após o custo inicial O(n³) da fatoração, permite resolver múltiplos sistemas para diferentes vetores b em tempo O(n²) por substituição direta e retrosubstituição.",
                    ),
                ],
                "questions": [
                    (
                        "Considere a matriz A de dimensões 3x3 com det(A) ≠ 0. O que se pode afirmar sobre as soluções do sistema linear homogêneo A·x = 0?",
                        "Possui apenas a solução trivial x = (0, 0, 0)ᵀ. Como o determinante é não nulo, a matriz é invertível e o núcleo (kernel) contém unicamente o vetor nulo.",
                    ),
                    (
                        "Na decomposição QR de uma matriz real A com m >= n e colunas linearmente independentes, quais propriedades estruturais possuem as matrizes Q e R?",
                        "A matriz Q possui colunas ortonormais (Qᵀ·Q = I) e R é uma matriz triangular superior com elementos diagonais estritamente positivos.",
                    ),
                    (
                        "O que mede o número de condição cond(A) = ||A|| · ||A⁻¹|| de uma matriz e como ele afeta a resolução numérica de sistemas lineares?",
                        "Mede a sensibilidade da solução x a pequenas perturbações na matriz A ou no vetor b. Um número de condição elevado indica mau condicionamento, significando que pequenos erros de arredondamento podem gerar grandes variações na resposta calculada.",
                    ),
                ],
            },
            {
                "key": "vector_calculus",
                "title": "Cálculo Vetorial & Otimização por Gradiente",
                "description": "Derivadas parciais, vetor gradiente, matriz Hessiana, aproximações de Taylor multivariadas e algoritmos de gradiente descendente.",
                "pos_x": 420.0,
                "pos_y": 130.0,
                "icon": "trending-up",
                "theory_content": (
                    "# Cálculo Vetorial & Otimização por Gradiente\n\n"
                    "O Cálculo Multivariado estende noções diferenciais para hipersuperfícies em $\\mathbb{R}^n$, "
                    "estabelecendo a fundação indispensável para compreender a descida de encosta em modelos de aprendizado profundo.\n\n"
                    "## 1. O Gradiente e a Direção de Máxima Subida\n"
                    "Para uma função escalar $f: \\mathbb{R}^n \\to \\mathbb{R}$, o vetor gradiente $\\nabla f(x)$ reúne todas as "
                    "derivadas parciais de primeira ordem:\n"
                    "$$\\nabla f(x) = \\left[ \\frac{\\partial f}{\\partial x_1}, \\dots, \\frac{\\partial f}{\\partial x_n} \\right]^T$$\n"
                    "Ele aponta precisamente na direção de maior taxa de crescimento instantâneo da função escalar.\n\n"
                    "## 2. A Matriz Hessiana e Curvatura Local\n"
                    "A análise de segunda ordem emprega a matriz Hessiana simétrica $H(x)$, cujas entradas são $H_{ij} = \\frac{\\partial^2 f}{\\partial x_i \\partial x_j}$. "
                    "Seus autovalores determinam se um ponto crítico é um mínimo estrito (definida positiva), máximo estrito (definida negativa) ou ponto de sela (indefinida).\n\n"
                    "## 3. Dinâmica do Gradiente Descendente\n"
                    "A descida é governada pelo passo iterativo $x^{(k+1)} = x^{(k)} - \\alpha \\nabla f(x^{(k)})$, onde $\\alpha > 0$ é a taxa de aprendizado. "
                    "Em escala massiva, o Gradiente Estocástico (SGD) calcula estimativas ruidosas e eficientes sobre amostras reduzidas (mini-batches)."
                ),
                "material": (
                    "Cálculo Diferencial Multivariado e Métodos de Gradiente",
                    "Estudo de superfícies multidimensionais, aproximações locais de primeira e segunda ordem via Taylor e técnicas de descida de encosta para minimização de funções de perda.",
                ),
                "flashcards": [
                    (
                        "Em que direção aponta o vetor gradiente ∇f(x) em um ponto de uma função escalar diferenciável?",
                        "Aponta na direção de maior taxa de crescimento instantâneo (máxima subida) de f. Seu módulo ||∇f(x)|| representa essa taxa máxima.",
                    ),
                    (
                        "O que a matriz Hessiana H(x) revela sobre a curvatura de uma função multivariada duas vezes diferenciável?",
                        "Contém as derivadas parciais de segunda ordem. Se H(x*) for definida positiva em um ponto crítico, o ponto é um mínimo local estrito; se for semidefinida negativa, é um máximo local.",
                    ),
                    (
                        "Como a taxa de aprendizado (learning rate α) afeta o comportamento do Gradiente Descendente?",
                        "Se for excessivamente alta, causa oscilações e divergência; se for muito baixa, torna a convergência extremamente lenta e propensa a estagnar.",
                    ),
                ],
                "questions": [
                    (
                        "Dada a função escalar f(x, y) = x² + 3y² - 4x + 2y, determine o ponto crítico (x*, y*) e utilize a matriz Hessiana para classificá-lo.",
                        "As derivadas parciais são ∂f/∂x = 2x - 4 e ∂f/∂y = 6y + 2. Igualando a zero, obtemos o ponto crítico (2, -1/3). A matriz Hessiana é H = diag(2, 6), cujos autovalores são positivos (2 e 6). Portanto, o ponto (2, -1/3) é um mínimo local estrito.",
                    ),
                    (
                        "Se em um ponto crítico de uma função duas vezes diferenciável a matriz Hessiana possui autovalores reais com sinais mistos (positivos e negativos), qual é a natureza desse ponto crítico?",
                        "É um ponto de sela (indefinido), pois a função curva para cima ao longo das direções associadas aos autovalores positivos e curva para baixo nas direções dos autovalores negativos.",
                    ),
                    (
                        "Por que a versão estocástica do gradiente descendente (SGD) é amplamente empregada no treinamento de modelos com grandes bases de dados em comparação ao gradiente exato (Batch)?",
                        "Porque o SGD calcula estimativas do gradiente utilizando pequenos subconjuntos de dados (mini-batches), reduzindo drasticamente a carga computacional e uso de memória por iteração, além de adicionar ruído estocástico que ajuda a escapar de pontos de sela.",
                    ),
                ],
            },
            {
                "key": "probability_monte_carlo",
                "title": "Probabilidade & Simulação de Monte Carlo",
                "description": "Variáveis aleatórias contínuas, distribuições conjuntas, Lei Forte dos Grandes Números, Teorema Central do Limite e integração estocástica.",
                "pos_x": 420.0,
                "pos_y": 390.0,
                "icon": "dice",
                "theory_content": (
                    "# Probabilidade & Simulação de Monte Carlo\n\n"
                    "A probabilidade formaliza o raciocínio sob incerteza e fornece os teoremas assintóticos que garantem "
                    "a convergência de métodos numéricos estocásticos.\n\n"
                    "## 1. Leis Limite Fundamentais\n"
                    "- **Lei Forte dos Grandes Números (LFGN):** A média amostral de variáveis i.i.d. converge quase certamente para o valor esperado $\\mu$.\n"
                    "- **Teorema Central do Limite (TCL):** Assegura normalidade assintótica $\\mathcal{N}(0, 1)$ para a soma padronizada de amostras i.i.d., "
                    "permitindo a derivação de intervalos de confiança empíricos rigorosos.\n\n"
                    "## 2. Integração Estocástica de Monte Carlo\n"
                    "O estimador empírico de Monte Carlo aproxima $\\mathbb{E}[g(X)] = \\int g(x)p(x)dx$ via:\n"
                    "$$\\hat{I}_N = \\frac{1}{N} \\sum_{i=1}^N g(X_i), \\quad X_i \\sim p(x)$$\n"
                    "Sua taxa de erro padrão converge a $\\mathcal{O}(N^{-1/2})$, sendo estritamente invariante em relação à "
                    "dimensão $d$ do integrando, superando a maldição da dimensionalidade de métodos de quadratura determinísticos.\n\n"
                    "## 3. Amostragem Avançada: Importance Sampling e MCMC\n"
                    "Técnicas de redução de variância concentram amostras nas regiões de maior densidade e impacto do integrando, "
                    "enquanto algoritmos de Cadeias de Markov Monte Carlo (MCMC, como Metropolis-Hastings) viabilizam a exploração "
                    "de distribuições com constante de partição desconhecida."
                ),
                "material": (
                    "Modelagem Estocástica e Métodos de Monte Carlo",
                    "Fundamentação teórica de processos estocásticos, amostragem pseudoaleatória, métodos de redução de variância e integração numérica em espaços de alta dimensão.",
                ),
                "flashcards": [
                    (
                        "O que assegura a Lei Forte dos Grandes Números para variáveis aleatórias i.i.d. com esperança finita μ?",
                        "Que a média amostral converge quase certamente para o valor esperado μ à medida que o número de amostras n tende ao infinito.",
                    ),
                    (
                        "Qual é a taxa assintótica de convergência do erro padrão no Método de Integração de Monte Carlo em relação ao número N de amostras?",
                        "A taxa é O(1/√N), sendo notável por independer da dimensionalidade d do espaço de integração.",
                    ),
                    (
                        "Qual o objetivo principal da técnica de Amostragem por Importância (Importance Sampling)?",
                        "Reduzir a variância do estimador amostrando de uma distribuição instrumental que concentra amostras nas regiões de maior contribuição do integrando.",
                    ),
                ],
                "questions": [
                    (
                        "Por que o Método de Monte Carlo se torna superior aos métodos de quadratura determinística (como regra de Simpson ou dos trapézios) em dimensões elevadas (d > 4)?",
                        "Porque métodos determinísticos em grade sofrem com a maldição da dimensionalidade, onde o número de avaliações escala exponencialmente como O(N^(1/d)) para atingir uma precisão dada. Já o Monte Carlo mantém taxa de erro O(N^(-1/2)) invariante em relação à dimensão d.",
                    ),
                    (
                        "Seja X uma variável aleatória com esperança μ e variância σ². Pela Desigualdade de Chebyshev, qual é o limite superior para a probabilidade de X se desviar de sua média por 3 ou mais desvios padrão?",
                        "O limite superior é P(|X - μ| ≥ 3σ) ≤ 1/(3²) = 1/9 ≈ 11,11%, válido para qualquer distribuição que possua variância finita.",
                    ),
                    (
                        "No algoritmo de Metropolis-Hastings (MCMC), por que o cálculo da constante de normalização da distribuição alvo não é necessário?",
                        "Porque a razão de aceitação depende apenas do quociente das densidades não normalizadas P(x')/P(x), de modo que a constante de partição/evidência cancela algebricamente.",
                    ),
                ],
            },
            {
                "key": "odes_numerical",
                "title": "Equações Diferenciais (EDOs) & Modelagem",
                "description": "Problemas de valor inicial (PVI), estabilidade numérica, esquemas explícitos vs implícitos, método de Runge-Kutta 4 (RK4) e sistemas dinâmicos.",
                "pos_x": 720.0,
                "pos_y": 110.0,
                "icon": "activity",
                "theory_content": (
                    "# Equações Diferenciais (EDOs) & Modelagem Numérica\n\n"
                    "As Equações Diferenciais Ordinárias (EDOs) modelam a evolução temporal de fenômenos físicos, dinâmicas químicas "
                    "e redes neurais contínuas (Neural ODEs).\n\n"
                    "## 1. Problemas de Valor Inicial (PVI)\n"
                    "Um PVI é expresso por $\\frac{dy}{dt} = f(t, y)$ com condição inicial $y(t_0) = y_0$. Sob condições de continuidade "
                    "Lipschitziana, o Teorema de Picard-Lindelöf assegura a existência e unicidade local da trajetória.\n\n"
                    "## 2. Métodos de Discretização e Erro de Truncamento\n"
                    "- **Erro de Truncamento Local (LTE):** Erro gerado em um único passo temporal de tamanho $h$.\n"
                    "- **Erro de Truncamento Global (GTE):** Discrepância cumulativa ao longo da simulação.\n"
                    "- **Método de Runge-Kutta 4 (RK4):** Padrão de referência para EDOs não-rígidas com precisão global $\\mathcal{O}(h^4)$, "
                    "ponderando quatro inclinações intermediárias no intervalo $[t_n, t_n + h]$.\n\n"
                    "## 3. Rigidez (Stiffness) e Métodos Implícitos\n"
                    "Sistemas com escalas temporais muito díspares (autovalores do Jacobiano com grande amplitude de magnitudes negativas) "
                    "exigem esquemas implícitos $A$-estáveis (como Euler Implícito ou BDF), garantindo estabilidade incondicional mesmo para passos temporais expressivos."
                ),
                "material": (
                    "Análise Numérica de Equações Diferenciais Ordinárias",
                    "Técnicas de discretização temporal para modelagem de dinâmicas físicas e biológicas, condições de estabilidade e tratamento de sistemas stiff.",
                ),
                "flashcards": [
                    (
                        "Por que o Método de Runge-Kutta de 4ª ordem (RK4) é amplamente utilizado como padrão para integração de EDOs não-rígidas?",
                        "Porque alcança erro de truncamento local de ordem O(h⁵) e global O(h⁴) com apenas quatro avaliações da derivada por passo temporal, oferecendo ótimo balanço entre custo e precisão.",
                    ),
                    (
                        "O que caracteriza uma equação diferencial 'stiff' (rígida) na análise numérica?",
                        "A presença de escalas temporais drasticamente divergentes (autovalores do Jacobiano com magnitudes muito distintas), exigindo passos infinitesimais para estabilidade em esquemas explícitos.",
                    ),
                    (
                        "Qual é a principal vantagem dos métodos implícitos (como Euler Implícito) em EDOs rígidas?",
                        "Possuem estabilidade incondicional (A-estabilidade), permitindo passos temporais muito maiores guiados pela precisão desejada e não pela restrição de estabilidade.",
                    ),
                ],
                "questions": [
                    (
                        "Dado o PVI dy/dt = -50y com y(0) = 1, qual é a condição no passo temporal h > 0 para que o método de Euler Explícito seja numericamente estável?",
                        "A equação linear de teste dy/dt = λy com λ = -50 possui fator de amplificação R(hλ) = 1 + hλ = 1 - 50h. Para estabilidade, exige-se |1 - 50h| < 1, o que implica 0 < 50h < 2 <=> h < 0.04.",
                    ),
                    (
                        "Em sistemas lineares autônomos dX/dt = A·X, qual é a condição necessária e suficiente sobre os autovalores da matriz A para que a origem seja um ponto de equilíbrio assintoticamente estável?",
                        "Todos os autovalores de A devem possuir parte real estritamente negativa (Re(λ_i) < 0 para todo i). Isso garante que os modos exponenciais e^(λ_i·t) decaiam assintoticamente para zero quando t -> ∞.",
                    ),
                    (
                        "Explique a diferença entre erro de truncamento local e erro de truncamento global na resolução numérica de um PVI.",
                        "O erro de truncamento local é o erro introduzido em uma única iteração de tamanho h, assumindo solução prévia exata. O erro de truncamento global é a discrepância acumulada entre a solução numérica e a analítica ao final do intervalo integrado.",
                    ),
                ],
            },
            {
                "key": "optimization_ml",
                "title": "Otimização Numérica & Machine Learning",
                "description": "Mínimos Quadrados, Regularização L1/L2 (Lasso e Ridge), Otimização Convexa, Backpropagation e otimizadores adaptativos (Adam).",
                "pos_x": 740.0,
                "pos_y": 350.0,
                "icon": "brain",
                "theory_content": (
                    "# Otimização Numérica & Machine Learning\n\n"
                    "A otimização matemática constitui o núcleo algorítmico do treinamento de modelos preditivos "
                    "e redes neurais profundas.\n\n"
                    "## 1. Otimização Convexa e Garantias Globais\n"
                    "Em problemas convexos, a propriedade determinante é que **qualquer mínimo local é garantidamente um mínimo global**. "
                    "Isso confere previsibilidade e estabilidade teórica a algoritmos de convergência.\n\n"
                    "## 2. Mínimos Quadrados e Regularização Espectral\n"
                    "A minimização da perda quadrática $||Xw - y||_2^2$ gera a solução analítica via Equações Normais $w^* = (X^T X)^{-1} X^T y$.\n"
                    "- **Regularização Ridge ($L_2$):** Penaliza $||w||_2^2$, contornando mau-condicionamento de $X^T X$ e estabilizando parâmetros.\n"
                    "- **Regularização Lasso ($L_1$):** Penaliza $||w||_1$, induzindo esparsidade geométrica exata e operando seleção automática de variáveis.\n\n"
                    "## 3. Backpropagation e Métodos Adaptativos de Segunda Ordem\n"
                    "O algoritmo de Backpropagation calcula recursivamente gradientes em redes neurais aplicando a regra da cadeia multivariada "
                    "com programação dinâmica. Otimizadores modernos como o **Adam** combinam médias móveis de primeiro e segundo momento, "
                    "ajustando a taxa de aprendizado individualmente por peso e acelerando a convergência em topologias não-convexas."
                ),
                "material": (
                    "Otimização Matemática em Inteligência Artificial e Ciência de Dados",
                    "Integração de cálculo vetorial, probabilidade e álgebra matricial para ajuste de modelos estatísticos e treinamento de redes neurais profundas.",
                ),
                "flashcards": [
                    (
                        "Por que problemas de otimização convexa são centrais no design de modelos de aprendizado de máquina?",
                        "Porque em conjuntos e funções convexas, qualquer mínimo local é garantidamente um mínimo global, tornando a convergência previsível e confiável.",
                    ),
                    (
                        "Qual a diferença estrutural nas soluções promovidas pela regularização L1 (Lasso) vs L2 (Ridge)?",
                        "A penalização L1 induz soluções esparsas zerando pesos irrelevantes (seleção de variáveis), enquanto L2 encolhe suavemente todos os pesos sem zerá-los.",
                    ),
                    (
                        "Como o otimizador Adam combina as vantagens do Momentum e do RMSprop?",
                        "Mantém estimativas de médias móveis do primeiro momento (direção média dos gradientes) e do segundo momento não centrado (escala adaptativa da taxa de aprendizado por parâmetro).",
                    ),
                ],
                "questions": [
                    (
                        "Na formulação matricial de Mínimos Quadrados Ordinários (OLS) com custo J(w) = ||Xw - y||², derive a expressão analítica das Equações Normais para o vetor de pesos ótimo w*.",
                        "Igualando o gradiente a zero: 2Xᵀ(Xw - y) = 0 <=> XᵀXw = Xᵀy. Assumindo X com posto pleno de colunas, XᵀX é invertível, resultando na solução analítica w* = (XᵀX)⁻¹Xᵀy.",
                    ),
                    (
                        "Em redes neurais artificiais, como a regra da cadeia no cálculo multivariado viabiliza o algoritmo de retropropagação do erro (Backpropagation)?",
                        "O Backpropagation calcula eficientemente o gradiente da perda em relação a cada peso em camadas ocultas aplicando a regra da cadeia recursivamente de trás para frente. Isso permite reaproveitar derivadas intermediárias (programação dinâmica), evitando recálculo redundante.",
                    ),
                    (
                        "O que estabelecem as Condições de Karush-Kuhn-Tucker (KKT) na otimização matemática não linear com restrições?",
                        "As condições KKT são condições necessárias de primeira ordem para que uma solução seja ótima em problemas com restrições. Englobam estacionaridade do Lagrangeano, viabilidade primal, viabilidade dual dos multiplicadores e folga complementar (λ_i · g_i(x) = 0).",
                    ),
                ],
            },
        ]

        # 4. Criação e persistência dos tópicos, nós e seus conteúdos
        nodes_map: dict[str, StudyNode] = {}
        for spec in nodes_spec:
            # Cria Tópico correspondente
            topic = Topic(
                subject_id=subject.id,
                name=str(spec["title"]),
            )
            self.topic_repo.save(topic)

            node = self.node_repo.save(
                StudyNode(
                    map_id=study_map.id,
                    title=str(spec["title"]),
                    description=str(spec["description"]),
                    theory_content=str(spec["theory_content"]),
                    pos_x=float(spec["pos_x"]),
                    pos_y=float(spec["pos_y"]),
                    icon=str(spec["icon"]),
                )
            )
            nodes_map[str(spec["key"])] = node

            # Material de Conhecimento com node_id e raw_text
            material_tuple = spec["material"]
            mat_title = material_tuple[0]
            mat_text = material_tuple[1]
            source = self.source_repo.save(
                KnowledgeSource(
                    title=str(mat_title),
                    topic_ids=[topic.id],
                    node_id=node.id,
                    content_type="TEXT",
                    raw_text=str(mat_text),
                    char_count=len(str(mat_text)),
                    total_chunks=1,
                )
            )
            self.content_repo.attach_knowledge_source(node.id, source.id)

            # Flashcards
            flashcards_list: list[tuple[str, str]] = spec["flashcards"]
            for front, back in flashcards_list:
                fc = Flashcard(front=front, back=back, topic_ids=[topic.id])
                self.flashcard_repo.save(fc)
                self.content_repo.attach_flashcard(node.id, fc.id)

            # Perguntas SRS com node_id
            questions_list: list[tuple[str, str]] = spec["questions"]
            for prompt, answer in questions_list:
                q = Question(
                    prompt=prompt,
                    expected_answer=answer,
                    node_id=node.id,
                    topic_ids=[topic.id],
                )
                self.question_repo.save(q)
                self.content_repo.attach_question(node.id, q.id)

        # 5. Arestas de Pré-requisito (Grafo Dirigido Acíclico - DAG)
        edges_spec = [
            ("linear_algebra", "vector_calculus"),
            ("linear_algebra", "probability_monte_carlo"),
            ("vector_calculus", "odes_numerical"),
            ("vector_calculus", "optimization_ml"),
            ("probability_monte_carlo", "optimization_ml"),
        ]

        for src_key, tgt_key in edges_spec:
            src_node = nodes_map[src_key]
            tgt_node = nodes_map[tgt_key]
            self.edge_repo.save(
                StudyEdge(
                    map_id=study_map.id,
                    source_node_id=src_node.id,
                    target_node_id=tgt_node.id,
                )
            )

        return study_map
