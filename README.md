Gestor de P.A - Aplicação Desktop Colaborativa
Este é um aplicativo de desktop desenvolvido em Python com PyQt5 para o gerenciamento de registros de P.A. (Pendência de Análise). A aplicação utiliza o Google Firebase (Firestore) como banco de dados, permitindo a sincronização de dados em tempo real e o uso colaborativo entre múltiplos utilizadores.


✨ Funcionalidades Principais
Cadastro e Edição: Formulário completo para criar e atualizar registros.

Sincronização em Tempo Real: Todas as alterações são refletidas instantaneamente para todos os utilizadores graças ao Firebase Firestore.

Visualização em Tabela: Visualize todos os registros numa tabela que permite ordenação por colunas.

Cálculo Automático de Prazos: A data de vencimento é calculada automaticamente com base no tipo de P.A.

Alertas Visuais: O sistema destaca os registros com prazos vencidos ou próximos do vencimento.

Exportação para Excel: Exporte todos os dados da tabela para um ficheiro .xlsx com um único clique.

Histórico de Ações: Um log regista as principais ações realizadas durante a sessão (salvar, excluir, exportar, etc.).

Interface Moderna: Tema escuro para uma visualização mais confortável.

🚨 ALERTA DE SEGURANÇA CRÍTICO 🚨
Este projeto usa o SDK Admin do Firebase (firebase_admin), que concede privilégios de administrador totais sobre o seu banco de dados.

O ficheiro de credenciais serviceAccountKey.json NÃO PODE SER COMPARTILHADO OU ENVIADO PARA O GITHUB. Se o fizer, qualquer pessoa poderá ler, modificar e excluir permanentemente todos os seus dados.

Boas Práticas de Segurança
NUNCA adicione o ficheiro serviceAccountKey.json ao Git.

Crie e utilize o ficheiro .gitignore (instruções abaixo) para evitar envios acidentais.

Mantenha a sua chave (.json) NUMA PASTA SEGURA E SEPARADA do código do projeto. A versão segura do script (gestor_pa_seguro.py) foi desenhada para pedir a localização deste ficheiro.

🚀 Instalação e Execução
1. Pré-requisitos
Certifique-se de que tem o Python 3 instalado.

2. Instalar as Dependências
Abra o terminal ou prompt de comando e execute:

pip install PyQt5 firebase-admin pandas openpyxl

3. Fazer o Download da Chave de Serviço
Vá ao seu projeto no Firebase Console.

Clique na engrenagem (⚙️) > Configurações do projeto > Contas de serviço.

Clique em "Gerar nova chave privada" e salve o ficheiro serviceAccountKey.json num local seguro no seu computador (ex: C:\Segredos\Firebase).

4. Executar a Aplicação
Navegue até à pasta do projeto no terminal e execute o script seguro:

python gestor_pa_seguro.py

Na primeira execução, a aplicação irá pedir para você localizar o ficheiro serviceAccountKey.json que salvou.

🛡️ Configuração do .gitignore
Para garantir que a sua chave secreta e outros ficheiros desnecessários nunca sejam enviados para o GitHub, crie um ficheiro chamado .gitignore na raiz do seu projeto com o seguinte conteúdo:

# Ficheiros de segredo - NUNCA ENVIAR!
serviceAccountKey.json
*.json
app_config.json

# Ambiente Python
__pycache__/
*.pyc
venv/
.venv/
/dist/
/build/

# Ficheiros de IDEs
.idea/
.vscode/

