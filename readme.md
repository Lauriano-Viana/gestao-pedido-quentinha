# 🍲 Sistema de Pedidos de Quentinhas (Congresso RCC/PI)

Este é um projeto de aplicação web desenvolvido com Streamlit para gerenciar pedidos de refeições ("quentinhas") para um evento específico, o Congresso da Renovação Carismática Católica (RCC) do Piauí.

A aplicação possui duas interfaces principais: uma para os clientes realizarem e agendarem seus pedidos e outra para a administração gerenciar, aprovar e acompanhar a entrega desses pedidos. Todos os dados são armazenados e lidos de uma Planilha Google (Google Sheets), servindo como um banco de dados simples e eficaz.

## ✨ Funcionalidades

### 🛍️ Página do Cliente (`Fazer Pedido`)

  - **Cardápio Dinâmico**: Exibe as opções de refeições disponíveis e seus respectivos preços.
  - **Seleção de Data**: Permite que o cliente escolha para quais dias do evento deseja agendar o pedido (ex: Sábado, Domingo).
  - **Carrinho de Compras**: O cliente pode adicionar múltiplas unidades de diferentes pratos para cada dia selecionado.
  - **Cálculo Automático**: O subtotal por dia e o valor total do pedido são calculados e exibidos em tempo real.
  - **Informações de Pagamento**: Exibe as instruções para pagamento via Pix ou em dinheiro.
  - **Coleta de Dados**: Um formulário para o cliente inserir nome, telefone e observações.
  - **Registro do Pedido**: Ao finalizar, o pedido é salvo em uma nova linha na Planilha Google com o status "Pendente".

### 👑 Painel de Administração (`Painel de Administração`)

  - **Acesso Restrito**: Protegido por um login e senha simples.
  - **Duas Abas Principais**:
    1.  **Gerenciar Pedidos**:
          - Lista todos os pedidos com status "Pendente".
          - Ferramentas de busca para filtrar pedidos por ID, nome ou telefone.
          - **Aprovação de Pedidos**: O administrador pode aprovar um pedido, o que atualiza seu status para "Aprovado" na planilha.
          - **Notificação via WhatsApp**: Gera um link pré-formatado do WhatsApp para notificar o cliente que seu pedido foi aprovado.
    2.  **Relatórios e Entregas**:
          - **Filtro por Data**: Permite visualizar todos os pedidos aprovados para uma data específica.
          - **Lista de Entregas**: Exibe uma lista dos pedidos aprovados que ainda não foram marcados como entregues.
          - **Controle de Entrega**: Um botão para marcar o pedido como "Entregue", atualizando a planilha.
          - **Busca Avançada**: Filtros para encontrar pedidos a serem entregues por ID, nome ou item específico no pedido.
          - **Resumo Financeiro**:
              - **Contagem de Itens**: Mostra a quantidade total vendida de cada prato.
              - **Fechamento de Caixa**: Calcula o valor total arrecadado no dia e detalha os totais por forma de pagamento (Pix, Dinheiro).

## 🛠️ Tecnologias Utilizadas

  - **Framework Web**: [Streamlit](https://streamlit.io/)
  - **Banco de Dados**: [Google Sheets](https://www.google.com/sheets/about/)
  - **Bibliotecas Python**:
      - `pandas`: Para manipulação e análise de dados.
      - `gspread`: Para interagir com a API do Google Sheets.
      - `google-oauth2-service-account`: Para autenticação com as APIs do Google.

## 🚀 Configuração e Instalação

Para executar este projeto localmente, siga os passos abaixo.

### 1\. Pré-requisitos

  - Python 3.8 ou superior.
  - Uma conta Google.

### 2\. Instalação das Dependências

Clone o repositório (ou apenas salve o arquivo `.py`) e instale as bibliotecas necessárias:

```bash
pip install streamlit pandas gspread google-oauth2-service-account
```

### 3\. Configuração do Google Sheets e API

1.  **Crie um Projeto no Google Cloud Console**: Se você não tiver um, crie um novo projeto.

2.  **Ative as APIs**: No seu projeto, ative a **Google Sheets API** e a **Google Drive API**.

3.  **Crie uma Conta de Serviço**:

      - Vá para "IAM e Admin" \> "Contas de Serviço".
      - Crie uma nova conta de serviço, dê um nome a ela (ex: `sheets-editor`).
      - Crie uma chave para esta conta de serviço (formato JSON) e faça o download do arquivo. O conteúdo deste arquivo será usado nas `secrets` do Streamlit.

4.  **Crie sua Planilha Google**:

      - Crie uma nova planilha. Anote o ID dela (presente na URL: `.../spreadsheets/d/AQUI_VAI_O_ID/edit`).
      - Na primeira linha, crie os seguintes cabeçalhos de coluna, exatamente como abaixo:
        ```
        ID | Data/Hora | Nome Cliente | Coluna Vazia 1 | Telefone Cliente | Coluna Vazia 2 | Itens Pedido | Total Pedido | Observacoes | Tipo Pagamento | Coluna Vazia 3 | Status | Coluna Vazia 4 | Grand Total | Entregue
        ```
        > **Nota**: As colunas mais importantes que o script utiliza são: `ID`, `Data/Hora`, `Nome Cliente`, `Telefone Cliente`, `Itens Pedido`, `Total Pedido`, `Observacoes`, `Tipo Pagamento`, `Status` e `Entregue`. As outras são usadas como espaçadores e podem ser deixadas em branco.

5.  **Compartilhe a Planilha**:

      - Abra o arquivo JSON da sua conta de serviço e encontre o email do cliente (ex: `...iam.gserviceaccount.com`).
      - Na sua Planilha Google, clique em "Compartilhar" e adicione este email, dando a ele permissões de **Editor**.

### 4\. Configuração das Secrets do Streamlit

1.  Crie uma pasta chamada `.streamlit` no diretório raiz do seu projeto.
2.  Dentro dela, crie um arquivo chamado `secrets.toml`.
3.  Adicione o seguinte conteúdo ao arquivo, substituindo os valores pelos seus:

<!-- end list -->

```toml
# .streamlit/secrets.toml

# Credenciais de Login do Admin
admin_login = "SEU_USUARIO_ADMIN"
admin_senha = "SUA_SENHA_ADMIN"

# ID da sua Planilha Google
GOOGLE_SHEETS_ID = "ID_DA_SUA_PLANILHA_COPIADO_DA_URL"

# Credenciais do Google Service Account (copie do arquivo .json)
[google_credentials]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "sua-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nSUA_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "seu-client-email@seu-project-id.iam.gserviceaccount.com"
client_id = "seu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "url-do-seu-certificado"
```

> **Atenção**: O campo `private_key` no TOML deve ser envolto em aspas triplas para preservar as quebras de linha.

## ▶️ Como Executar

Após concluir toda a configuração, abra um terminal no diretório do projeto e execute o seguinte comando:

```bash
streamlit run quentinhas3.py
```

A aplicação será aberta no seu navegador padrão.