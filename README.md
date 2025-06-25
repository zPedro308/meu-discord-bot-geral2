# 🚔 Bot PMESP - Sistema Completo de Gestão

Bot Discord completo para o servidor PMESP (Polícia Militar do Estado de São Paulo) com funcionalidades avançadas de tickets, bate-ponto, solicitação de viaturas, logs e alertas.

## 🎯 Funcionalidades

### 🎫 Sistema de Tickets
- Painel infinito para abertura de tickets
- Criação automática de canais privados
- Sistema de logs completo
- Fechamento com confirmação

### ⏰ Sistema de Bate-Ponto
- Controle de entrada e saída
- Monitoramento de canais de voz
- Alertas automáticos para saída de canal
- Fechamento automático após 2 minutos fora do canal
- Relatório individual de horas

### 🚔 Sistema de Viaturas
- Solicitação de viaturas com até 3 pessoas
- Verificação automática de patentes
- Sistema de aprovação/negação
- Aprovação automática após 5 minutos
- Logs detalhados de todas as operações

### 📊 Sistema de Logs
- Logs gerais de todas as atividades
- Monitoramento de entrada/saída de membros
- Logs de mudanças de cargos e nicknames
- Logs de mensagens editadas/deletadas
- Logs de criação/exclusão de canais

### 🔔 Sistema de Alertas
- Monitoramento de 30+ canais de voz
- Alertas automáticos para saída de canais
- Tempo limite de 2 minutos para retorno

## 🛠️ Instalação

### Pré-requisitos
- Python 3.11+
- Conta Discord Developer
- Servidor Discord com permissões administrativas

### Passo 1: Clone o projeto
```bash
git clone <url-do-repositorio>
cd pmesp_bot
```

### Passo 2: Instale as dependências
```bash
pip install -r requirements.txt
```

### Passo 3: Configure o bot
1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie uma nova aplicação
3. Vá para a seção "Bot"
4. Copie o token do bot
5. Edite o arquivo `.env`:

```env
DISCORD_TOKEN=SEU_TOKEN_AQUI
GUILD_ID=ID_DO_SEU_SERVIDOR
```

### Passo 4: Configure as permissões
O bot precisa das seguintes permissões:
- Gerenciar canais
- Gerenciar mensagens
- Enviar mensagens
- Usar comandos de barra
- Ver canais
- Conectar a canais de voz
- Ver estado de voz dos membros

### Passo 5: Execute o bot
```bash
python bot.py
```

## ⚙️ Configuração dos Canais

### IDs dos Canais (já configurados no código)
- **Canal de Tickets:** 1369350790782652416
- **Categoria de Tickets:** 1369350390583263464
- **Canal de Logs de Tickets:** 1369350793181925428
- **Canal de Bate-Ponto:** 1369350872718508062
- **Canal de Alertas:** 1369350878041215017
- **Canal da Central:** 1369350612080394321
- **Canal de Logs de Viaturas:** 1369350949230874834
- **Canal de Logs Gerais:** 1369351129091280978

### Cargos Importantes
- **Cargo para Aprovar Viaturas:** 1369352042031616121
- **Cargo para Gerar Painéis:** 1369351249022947468

## 🎮 Comandos Disponíveis

### Comandos Administrativos
- `!setup_tickets` - Configura o painel de tickets
- `!setup_bate_ponto` - Configura o painel de bate-ponto
- `!setup_central` - Configura o painel da central
- `!setup_all` - Configura todos os painéis de uma vez
- `!status` - Mostra o status do sistema

### Comandos Gerais
- `!help_pmesp` - Mostra a lista de comandos

## 🔧 Personalização

### Sistema de Patentes
O sistema reconhece as seguintes patentes (do menor para o maior):
1. Soldado
2. Cabo
3. Terceiro Sargento
4. Segundo Sargento
5. Primeiro Sargento
6. Subtenente
7. Aspirante
8. Segundo Tenente
9. Primeiro Tenente
10. Capitão
11. Major
12. Tenente Coronel
13. Coronel
14. Comandante Geral

### Canais de Voz Monitorados
O bot monitora 30 canais de voz específicos para:
- Sistema de bate-ponto
- Alertas de saída
- Solicitação de viaturas

## 📋 Como Usar

### 1. Configuração Inicial
Execute `!setup_all` para configurar todos os painéis automaticamente.

### 2. Sistema de Tickets
- Os usuários clicam no botão "🎫 Abrir Ticket"
- Um canal privado é criado automaticamente
- O ticket pode ser fechado com confirmação

### 3. Sistema de Bate-Ponto
- Entre em um canal de voz válido
- Clique em "🟢 Abrir Ponto" para iniciar
- Clique em "🔴 Fechar Ponto" para encerrar
- Use "📊 Minhas Horas" para ver o relatório

### 4. Sistema de Viaturas
- Entre em um canal de voz da Central
- Clique em "🚔 Solicitar Viatura"
- Selecione até 3 pessoas
- Aguarde a aprovação

## 🚨 Recursos Especiais

### Painéis Infinitos
Todos os painéis são persistentes e funcionam mesmo após reinicializações do bot.

### Sistema de Alertas Inteligente
- Monitora saída de canais de voz
- Alerta em tempo real
- Fecha bate-ponto automaticamente após 2 minutos

### Logs Completos
- Todas as ações são registradas
- Logs organizados por categoria
- Histórico completo de atividades

### Aprovação Automática
- Viaturas são aprovadas automaticamente após 5 minutos
- Sistema de backup para garantir fluidez

## 🛡️ Segurança

- Verificação de permissões em todos os comandos
- Validação de canais de voz
- Sistema de cargos para controle de acesso
- Logs de segurança para auditoria

## 📞 Suporte

Para suporte técnico ou dúvidas:
- Comandante Geral: Pedro Blanc
- Servidor: PMESP

## 📄 Licença

Este bot foi desenvolvido especificamente para o servidor PMESP.

---

**🚔 PMESP - Servir e Proteger 👮‍♂️**

