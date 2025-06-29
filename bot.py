from keep_alive import keep_alive
keep_alive()

import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações dos IDs
GUILD_ID = None  # Será definido pelo usuário
TICKET_CHANNEL_ID = 1369350790782652416
TICKET_CATEGORY_ID = 1369350390583263464
TICKET_LOG_CHANNEL_ID = 1369350793181925428
BATE_PONTO_CHANNEL_ID = 1369350872718508062
ALERT_CHANNEL_ID = 1369350878041215017
CENTRAL_CHANNEL_ID = 1369350943732138074
VIATURA_LOG_CHANNEL_ID = 1369350949230874834
VIATURA_ROLE_ID = 1369350943732138074
GENERAL_LOG_CHANNEL_ID = 1369351129091280978
PANEL_PERMISSION_ROLE_ID = 1369351249022947468

# IDs para o sistema de ausência
ABSENCE_LOG_CHANNEL_ID = 1369350960220082328
ABSENCE_ROLE_ID = 1369351129091280978

# IDs para o sistema de setagem de cargos
CARGO_PANEL_CHANNEL_ID = GENERAL_LOG_CHANNEL_ID  # Pode ser alterado conforme necessário

# IDs para o sistema de reset de horas e membros ativos/inativos
RESET_HORAS_LOG_CHANNEL_ID = 1369350894151274496
MEMBROS_ATIVOS_CHANNEL_ID = 1369350882805682326
MEMBROS_INATIVOS_CHANNEL_ID = 1369350899410927688

# Canais de voz para solicitação de viatura
VIATURA_VOICE_CHANNELS = [1369350593101041685, 1369350612080394321]

# Canais de voz para alertas e bate-ponto
VOICE_CHANNELS = [
    1369350549077491783, 1369350561178193991, 1369350581826879658, 1369350598142460034,
    1369350601065889822, 1369350614638919801, 1369350619298664540, 1369350627561574580,
    1369350635891327136, 1369350641306046504, 1369350646720893019, 1369350652777599147,
    1369350663150239874, 1369350667466178610, 1369350672864252106, 1369350685841293462,
    1369350696410812557, 1369350700789928117, 1369350708641534022,
    1369350712856936621, 1369350719194271937, 1369350730280079422, 1369350735027769444,
    1369350737150218312, 1369350749842047147, 1369350764983488632, 1369350767139491921,
    1369350773137477763, 1369350783325306970, 1369350696410812557
]

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Bot setup
bot = commands.Bot(command_prefix='!', intents=intents)

# Dicionários para armazenar dados
ticket_counter = 0
bate_ponto_data = {}
viatura_requests = {}
voice_alerts = {}
absence_requests = {}
cargo_requests = {}

# Sistema de patentes (do menor para o maior)
PATENTES = {
    'soldado': 1,
    'cabo': 2,
    'terceiro_sargento': 3,
    'segundo_sargento': 4,
    'primeiro_sargento': 5,
    'subtenente': 6,
    'aspirante': 7,
    'segundo_tenente': 8,
    'primeiro_tenente': 9,
    'capitao': 10,
    'major': 11,
    'tenente_coronel': 12,
    'coronel': 13,
    'comandante_geral': 14
}

# Configuração de cargos para setagem automática
CARGO_CONFIG = {
    1369351259311575150: {"nome": "SCGPM", "pai": None},
    1369351728180494488: {"nome": "CEL", "pai": 1369351759939633152},
    1369351738729037854: {"nome": "T.CEL", "pai": 1369351759939633152},
    1369351748866670704: {"nome": "MAJ", "pai": 1369351759939633152},
    1369351780726603946: {"nome": "CAP", "pai": 1369351791170289764},
    1369351812188209183: {"nome": "1°TEN", "pai": 1369351833193283705},
    1369351822937948180: {"nome": "2°TEN", "pai": 1369351833193283705},
    1369351853833322758: {"nome": "ASP", "pai": 1369351864319217738},
    1369351885139738796: {"nome": "S.TEN", "pai": 1369351927380312136},
    1369351896220958790: {"nome": "1°SGT", "pai": 1369351927380312136},
    1369351906618638439: {"nome": "2°SGT", "pai": 1369351927380312136},
    1369351917184221316: {"nome": "3°SGT", "pai": 1369351927380312136},
    1369351948490375351: {"nome": "CB", "pai": 1369351979540680804},
    1369351958753837096: {"nome": "SD-1ª", "pai": 1369351979540680804},
    1369351969088606340: {"nome": "SD-2ª", "pai": 1369351979540680804}
}

def get_user_patente(member):
    """Retorna a patente do usuário baseada nos cargos"""
    for role in member.roles:
        role_name = role.name.lower().replace(' ', '_')
        if role_name in PATENTES:
            return role_name, PATENTES[role_name]
    return 'soldado', 1

def get_highest_patente(members):
    """Retorna o membro com a maior patente"""
    highest_member = None
    highest_rank = 0

    for member in members:
        patente_name, patente_rank = get_user_patente(member)
        if patente_rank > highest_rank:
            highest_rank = patente_rank
            highest_member = member

    return highest_member

def format_nickname(member, cargo_nome):
    """Formata o nickname do membro com base no cargo"""
    # Determinar prefixo
    prefixo = "SCGPM" if cargo_nome == "SCGPM" else "13°BPM/M"

    # Obter sufixo anterior (ID) se existir, ou usar os 5 últimos do ID
    sufixo_match = re.search(r'「(.{3,10})」$', member.display_name)
    sufixo = sufixo_match.group(0) if sufixo_match else f"「{str(member.id)[-5:]}」"

    # Limpar nome: remover prefixo, sufixo e cargo antigo
    nome_atual = member.display_name

    # Remover qualquer bloco entre 「」
    nome_atual = re.sub(r'「.*?」', '', nome_atual)

    # Remover prefixos conhecidos
    nome_atual = re.sub(r'^(SCGPM|13°BPM/M)?\s?', '', nome_atual)

    # Remover cargos antigos
    cargos_conhecidos = [info["nome"] for info in CARGO_CONFIG.values()]
    for cargo in cargos_conhecidos:
        nome_atual = re.sub(f'^{re.escape(cargo)}\\s?', '', nome_atual)

    nome_atual = nome_atual.strip()

    # Se o nome ficou vazio, usar o username
    if not nome_atual:
        nome_atual = member.name

    # Formatar novo apelido
    novo_apelido = f"「{prefixo}」{cargo_nome} {nome_atual} {sufixo}"

    return novo_apelido

# Classes para o sistema de tickets
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🎫 Abrir Ticket', style=discord.ButtonStyle.primary, custom_id='open_ticket')
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        global ticket_counter
        ticket_counter += 1

        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f'ticket-{ticket_counter:04d}',
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title='🎫 Ticket Aberto',
            description=(
                f"**Olá {interaction.user.mention}!** 👋\n\n"
                f"🔹 Seu ticket foi criado com sucesso!\n"
                f"🔹 Descreva detalhadamente sua solicitação\n"
                f"🔹 Nossa equipe responderá em breve\n\n"
                f"**📋 Informações do Ticket:**\n"
                f"🆔 **ID:** #{ticket_counter:04d}\n"
                f"👤 **Solicitante:** {interaction.user.display_name}\n"
                f"🕐 **Aberto em:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n"
                f"📍 **Status:** Aguardando resposta"
            ),
            color=0x00ff00
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text='PMESP - Sistema de Tickets', icon_url=guild.icon.url if guild.icon else None)

        close_view = TicketCloseView()
        await ticket_channel.send(embed=embed, view=close_view)

        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title='📋 Ticket Aberto',
                description=(
                    f"**🎫 Novo ticket criado!**\n\n"
                    f"🆔 **ID:** #{ticket_counter:04d}\n"
                    f"👤 **Usuário:** {interaction.user.mention}\n"
                    f"📍 **Canal:** {ticket_channel.mention}\n"
                    f"🕐 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                ),
                color=0x00ff00
            )
            await log_channel.send(embed=log_embed)

        general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f'🎫 **Ticket #{ticket_counter:04d}** aberto por {interaction.user.mention} em {ticket_channel.mention}')

        await interaction.response.send_message(
            f'✅ **Ticket criado com sucesso!**\n'
            f'🎫 Acesse seu ticket em: {ticket_channel.mention}',
            ephemeral=True
        )

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Fechar Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title='🔒 Confirmar Fechamento',
            description=(
                '**⚠️ Tem certeza que deseja fechar este ticket?**\n\n'
                '🔹 Esta ação não pode ser desfeita\n'
                '🔹 O canal será deletado permanentemente\n'
                '🔹 Certifique-se de ter salvado informações importantes'
            ),
            color=0xff0000
        )

        confirm_view = TicketConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class TicketConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label='✅ Sim, Fechar', style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title='🔒 Ticket Fechado',
                description=(
                    f"**🎫 Ticket fechado!**\n\n"
                    f"📍 **Canal:** {channel.name}\n"
                    f"👤 **Fechado por:** {interaction.user.mention}\n"
                    f"🕐 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                ),
                color=0xff0000
            )
            await log_channel.send(embed=log_embed)

        general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f'🔒 **Ticket {channel.name}** fechado por {interaction.user.mention}')

        await interaction.response.send_message('🔒 **Ticket será fechado em 5 segundos...**')
        await asyncio.sleep(5)
        await channel.delete()

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('✅ **Fechamento cancelado!**', ephemeral=True)

# Classes para o sistema de bate-ponto
class BatePontoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🟢 Abrir Ponto', style=discord.ButtonStyle.success, custom_id='abrir_ponto', emoji='⏰')
    async def abrir_ponto(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        current_time = datetime.now()

        if user_id in bate_ponto_data and bate_ponto_data[user_id]['status'] == 'aberto':
            embed = discord.Embed(
                title='⚠️ Ponto Já Aberto',
                description=(
                    f"**{interaction.user.mention}, você já tem um ponto aberto!**\n\n"
                    f"🕐 **Aberto desde:** {bate_ponto_data[user_id]['start_time'].strftime('%d/%m/%Y às %H:%M:%S')}\n"
                    f"⏱️ **Tempo decorrido:** {self.calculate_time_diff(bate_ponto_data[user_id]['start_time'], current_time)}\n\n"
                    f"🔹 Use o botão **'🔴 Fechar Ponto'** para encerrar seu expediente"
                ),
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not interaction.user.voice or interaction.user.voice.channel.id not in VOICE_CHANNELS:
            embed = discord.Embed(
                title='❌ Canal de Voz Necessário',
                description=(
                    f"**{interaction.user.mention}, você precisa estar em um canal de voz válido!**\n\n"
                    f"🔹 Entre em um dos canais de voz autorizados\n"
                    f"🔹 Tente abrir o ponto novamente\n\n"
                    f"📍 **Canais válidos:** Canais da categoria PMESP"
                ),
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        bate_ponto_data[user_id] = {
            'status': 'aberto',
            'start_time': current_time,
            'voice_channel': interaction.user.voice.channel.id,
            'total_hours': bate_ponto_data.get(user_id, {}).get('total_hours', 0)
        }

        embed = discord.Embed(
            title='✅ Ponto Aberto com Sucesso',
            description=(
                f"**🎉 Bom trabalho, {interaction.user.mention}!**\n\n"
                f"⏰ **Horário de entrada:** {current_time.strftime('%d/%m/%Y às %H:%M:%S')}\n"
                f"📍 **Canal de voz:** {interaction.user.voice.channel.name}\n"
                f"🏛️ **Unidade:** PMESP\n\n"
                f"🔹 Seu expediente foi iniciado\n"
                f"🔹 Mantenha-se no canal de voz\n"
                f"🔹 Lembre-se de fechar o ponto ao final\n\n"
                f"👮‍♂️ **Servir e Proteger!**"
            ),
            color=0x00ff00
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text='PMESP - Sistema de Bate-Ponto', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        general_log = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(
                f"🟢 **Ponto aberto** por {interaction.user.mention} às {current_time.strftime('%H:%M:%S')} "
                f"no canal {interaction.user.voice.channel.name}"
            )

    @discord.ui.button(label='🔴 Fechar Ponto', style=discord.ButtonStyle.danger, custom_id='fechar_ponto', emoji='⏹️')
    async def fechar_ponto(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        current_time = datetime.now()

        if user_id not in bate_ponto_data or bate_ponto_data[user_id]['status'] != 'aberto':
            embed = discord.Embed(
                title='⚠️ Nenhum Ponto Aberto',
                description=(
                    f"**{interaction.user.mention}, você não tem nenhum ponto aberto!**\n\n"
                    f"🔹 Use o botão **'🟢 Abrir Ponto'** para iniciar seu expediente\n"
                    f"🔹 Certifique-se de estar em um canal de voz válido"
                ),
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        start_time = bate_ponto_data[user_id]['start_time']
        worked_seconds = (current_time - start_time).total_seconds()
        worked_hours = worked_seconds / 3600

        bate_ponto_data[user_id]['status'] = 'fechado'
        bate_ponto_data[user_id]['end_time'] = current_time
        bate_ponto_data[user_id]['total_hours'] += worked_hours

        hours = int(worked_seconds // 3600)
        minutes = int((worked_seconds % 3600) // 60)
        seconds = int(worked_seconds % 60)

        embed = discord.Embed(
            title='🔴 Ponto Fechado com Sucesso',
            description=(
                f"**👋 Até logo, {interaction.user.mention}!**\n\n"
                f"⏰ **Horário de saída:** {current_time.strftime('%d/%m/%Y às %H:%M:%S')}\n"
                f"🕐 **Tempo trabalhado:** {hours:02d}h {minutes:02d}m {seconds:02d}s\n"
                f"📊 **Total acumulado:** {self.format_hours(bate_ponto_data[user_id]['total_hours'])}\n"
                f"🏛️ **Unidade:** PMESP\n\n"
                f"🔹 Seu expediente foi encerrado\n"
                f"🔹 Horas contabilizadas com sucesso\n"
                f"🔹 Obrigado pelo seu serviço!\n\n"
                f"👮‍♂️ **Servir e Proteger!**"
            ),
            color=0xff0000
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text='PMESP - Sistema de Bate-Ponto', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        general_log = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(
                f"🔴 **Ponto fechado** por {interaction.user.mention} às {current_time.strftime('%H:%M:%S')} "
                f"- Tempo trabalhado: {hours:02d}h {minutes:02d}m {seconds:02d}s"
            )

    @discord.ui.button(label='📊 Minhas Horas', style=discord.ButtonStyle.primary, custom_id='minhas_horas', emoji='📈')
    async def minhas_horas(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        current_time = datetime.now()

        if user_id not in bate_ponto_data:
            embed = discord.Embed(
                title='📊 Relatório de Horas',
                description=(
                    f"**{interaction.user.mention}, você ainda não registrou nenhum ponto!**\n\n"
                    f"🔹 Use o botão **'🟢 Abrir Ponto'** para começar\n"
                    f"🔹 Suas horas aparecerão aqui após o primeiro registro"
                ),
                color=0x0066cc
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = bate_ponto_data[user_id]
        total_hours = user_data.get('total_hours', 0)

        current_session = ''
        if user_data['status'] == 'aberto':
            session_seconds = (current_time - user_data['start_time']).total_seconds()
            session_hours = int(session_seconds // 3600)
            session_minutes = int((session_seconds % 3600) // 60)
            current_session = f'\n🟢 **Sessão atual:** {session_hours:02d}h {session_minutes:02d}m (em andamento)'

        embed = discord.Embed(
            title='📊 Relatório de Horas Trabalhadas',
            description=(
                f"**👤 Policial:** {interaction.user.mention}\n"
                f"🏛️ **Unidade:** PMESP\n"
                f"📅 **Data:** {current_time.strftime('%d/%m/%Y')}\n\n"
                f"⏱️ **Total de horas:** {self.format_hours(total_hours)}\n"
                f"📈 **Status:** {'🟢 Em serviço' if user_data['status'] == 'aberto' else '🔴 Fora de serviço'}\n"
                f"{current_session}\n\n"
                f"🔹 Mantenha seu registro em dia\n"
                f"🔹 Lembre-se de abrir/fechar o ponto\n"
                f"🔹 Suas horas são importantes!\n\n"
                f"👮‍♂️ **Servir e Proteger!**"
            ),
            color=0x0066cc
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text='PMESP - Relatório de Horas', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def calculate_time_diff(self, start_time, end_time):
        """Calcula a diferença de tempo formatada"""
        diff_seconds = (end_time - start_time).total_seconds()
        hours = int(diff_seconds // 3600)
        minutes = int((diff_seconds % 3600) // 60)
        seconds = int(diff_seconds % 60)
        return f'{hours:02d}h {minutes:02d}m {seconds:02d}s'

    def format_hours(self, total_hours):
        """Formata as horas totais"""
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        return f'{hours:02d}h {minutes:02d}m'

# Classes para o sistema de viaturas
class ViaturaSelectorModal(discord.ui.Modal):
    def __init__(self, voice_members):
        super().__init__(title='🚔 Seleção de Viatura PMESP')
        self.voice_members = voice_members

        options_text = '\n'.join([f'{i+1}. {member.display_name}' for i, member in enumerate(voice_members)])

        self.selection = discord.ui.TextInput(
            label='Selecione até 3 pessoas (números separados por vírgula)',
            placeholder='Ex: 1,3,5 (máximo 3 pessoas)',
            style=discord.TextStyle.short,
            max_length=20,
            required=True
        )
        self.add_item(self.selection)

        self.reason = discord.ui.TextInput(
            label='Motivo da solicitação',
            placeholder='Descreva o motivo da solicitação de viatura...',
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            selected_indices = [int(x.strip()) - 1 for x in self.selection.value.split(',')]

            if len(selected_indices) > 3:
                await interaction.response.send_message('❌ **Máximo de 3 pessoas permitido!**', ephemeral=True)
                return

            if any(i < 0 or i >= len(self.voice_members) for i in selected_indices):
                await interaction.response.send_message('❌ **Números inválidos selecionados!**', ephemeral=True)
                return

            selected_members = [self.voice_members[i] for i in selected_indices]

            if interaction.user not in selected_members:
                selected_members.append(interaction.user)

            if len(selected_members) > 3:
                selected_members = selected_members[:3]

            highest_patente_member = get_highest_patente(selected_members)
            highest_patente_name, highest_patente_rank = get_user_patente(highest_patente_member)

            request_id = len(viatura_requests) + 1
            viatura_requests[request_id] = {
                'solicitante': interaction.user,
                'membros': selected_members,
                'motivo': self.reason.value,
                'timestamp': datetime.now(),
                'status': 'pendente',
                'maior_patente': highest_patente_member
            }

            log_channel = interaction.guild.get_channel(VIATURA_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title='🚔 Solicitação de Viatura',
                    description=(
                        f"**📋 Nova solicitação de viatura!**\n\n"
                        f"🆔 **ID:** #{request_id:04d}\n"
                        f"👤 **Solicitante:** {interaction.user.mention}\n"
                        f"🏆 **Maior Patente:** {highest_patente_member.mention} ({highest_patente_name.replace('_', ' ').title()})\n"
                        f"📝 **Motivo:** {self.reason.value}\n"
                        f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n\n"
                        f"👥 **Membros da Viatura:**\n"
                        + '\n'.join([f'🔹 {member.mention}' for member in selected_members])
                    ),
                    color=0x0066cc
                )
                embed.set_footer(text='PMESP - Sistema de Viaturas', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

                approval_view = ViaturaApprovalView(request_id)
                await log_channel.send(embed=embed, view=approval_view)

                asyncio.create_task(self.auto_approve_viatura(request_id, log_channel))

            await interaction.response.send_message(
                f'✅ **Solicitação de viatura enviada!**\n'
                f'🆔 **ID:** #{request_id:04d}\n'
                f'⏰ **Aguardando aprovação...**',
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message('❌ **Formato inválido! Use números separados por vírgula (ex: 1,2,3)**', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ **Erro ao processar solicitação:** {str(e)}', ephemeral=True)

    async def auto_approve_viatura(self, request_id, log_channel):
        await asyncio.sleep(300)

        if request_id in viatura_requests and viatura_requests[request_id]['status'] == 'pendente':
            viatura_requests[request_id]['status'] = 'aprovado_sistema'
            viatura_requests[request_id]['aprovado_por'] = 'Sistema Automático'

            embed = discord.Embed(
                title='✅ Viatura Aprovada Automaticamente',
                description=(
                    f"**🚔 Viatura #{request_id:04d} aprovada pelo sistema!**\n\n"
                    f"⏰ **Motivo:** Tempo limite de 5 minutos atingido\n"
                    f"🤖 **Aprovado por:** Sistema Automático\n"
                    f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                ),
                color=0x00ff00
            )
            await log_channel.send(embed=embed)

# Classes para o sistema de ausência
class AbsenceRequestModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='🏠 Solicitação de Ausência PMESP')

        self.start_date = discord.ui.TextInput(
            label='Data de Início (DD/MM/AAAA)',
            placeholder='Ex: 25/12/2024',
            style=discord.TextStyle.short,
            max_length=10,
            required=True
        )
        self.add_item(self.start_date)

        self.end_date = discord.ui.TextInput(
            label='Data de Fim (DD/MM/AAAA)',
            placeholder='Ex: 30/12/2024',
            style=discord.TextStyle.short,
            max_length=10,
            required=True
        )
        self.add_item(self.end_date)

        self.reason = discord.ui.TextInput(
            label='Motivo da Ausência',
            placeholder='Descreva detalhadamente o motivo da sua ausência...',
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar formato das datas
            start_date_obj = datetime.strptime(self.start_date.value, '%d/%m/%Y')
            end_date_obj = datetime.strptime(self.end_date.value, '%d/%m/%Y')

            if start_date_obj > end_date_obj:
                await interaction.response.send_message('❌ **A data de início não pode ser posterior à data de fim!**', ephemeral=True)
                return

            if start_date_obj < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                await interaction.response.send_message('❌ **A data de início não pode ser no passado!**', ephemeral=True)
                return

            request_id = len(absence_requests) + 1
            absence_requests[request_id] = {
                'solicitante': interaction.user,
                'data_inicio': start_date_obj,
                'data_fim': end_date_obj,
                'motivo': self.reason.value,
                'timestamp': datetime.now(),
                'status': 'pendente'
            }

            log_channel = interaction.guild.get_channel(ABSENCE_LOG_CHANNEL_ID)
            if log_channel:
                duration_days = (end_date_obj - start_date_obj).days + 1

                embed = discord.Embed(
                    title='🏠 Solicitação de Ausência',
                    description=(
                        f"**📋 Nova solicitação de ausência!**\n\n"
                        f"🆔 **ID:** #{request_id:04d}\n"
                        f"👤 **Solicitante:** {interaction.user.mention}\n"
                        f"📅 **Período:** {self.start_date.value} até {self.end_date.value}\n"
                        f"⏱️ **Duração:** {duration_days} dia(s)\n"
                        f"📝 **Motivo:** {self.reason.value}\n"
                        f"🕐 **Solicitado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                    ),
                    color=0xff9900
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.set_footer(text='PMESP - Sistema de Ausências', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

                approval_view = AbsenceApprovalView(request_id)
                await log_channel.send(embed=embed, view=approval_view)

            await interaction.response.send_message(
                f'✅ **Solicitação de ausência enviada!**\n'
                f'🆔 **ID:** #{request_id:04d}\n'
                f'📅 **Período:** {self.start_date.value} até {self.end_date.value}\n'
                f'⏰ **Aguardando aprovação...**',
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message('❌ **Formato de data inválido! Use DD/MM/AAAA (ex: 25/12/2024)**', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ **Erro ao processar solicitação:** {str(e)}', ephemeral=True)

class AbsenceApprovalView(discord.ui.View):
    def __init__(self, request_id):
        super().__init__(timeout=None)
        self.request_id = request_id

    @discord.ui.button(label='✅ Aprovar', style=discord.ButtonStyle.success, custom_id='aprovar_ausencia')
    async def aprovar_ausencia(self, interaction: discord.Interaction, button: discord.ui.Button):
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para aprovar ausências!**', ephemeral=True)
            return

        if self.request_id not in absence_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if absence_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        absence_requests[self.request_id]['status'] = 'aprovado'
        absence_requests[self.request_id]['aprovado_por'] = interaction.user

        # Adicionar cargo de AUSENTE ao usuário
        solicitante = absence_requests[self.request_id]['solicitante']
        guild = interaction.guild
        absence_role = guild.get_role(ABSENCE_ROLE_ID)

        if absence_role and solicitante in guild.members:
            try:
                await solicitante.add_roles(absence_role, reason=f'Ausência aprovada - ID #{self.request_id:04d}')
            except discord.Forbidden:
                await interaction.followup.send('⚠️ **Ausência aprovada, mas não foi possível adicionar o cargo (sem permissão).**', ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f'⚠️ **Ausência aprovada, mas erro ao adicionar cargo:** {str(e)}', ephemeral=True)

        aprovador_patente, _ = get_user_patente(interaction.user)

        embed = discord.Embed(
            title='✅ Ausência Aprovada',
            description=(
                f"**🏠 Ausência #{self.request_id:04d} aprovada!**\n\n"
                f"👤 **Aprovado por:** {interaction.user.mention}\n"
                f"🏆 **Patente:** {aprovador_patente.replace('_', ' ').title()}\n"
                f"🆔 **ID in-game:** {interaction.user.display_name}\n"
                f"🏷️ **Cargo atribuído:** {absence_role.name if absence_role else 'AUSENTE'}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)

        # Notificar o solicitante
        try:
            solicitante_embed = discord.Embed(
                title='✅ Sua Ausência Foi Aprovada!',
                description=(
                    f"**🎉 Parabéns! Sua solicitação de ausência foi aprovada.**\n\n"
                    f"🆔 **ID:** #{self.request_id:04d}\n"
                    f"📅 **Período:** {absence_requests[self.request_id]['data_inicio'].strftime('%d/%m/%Y')} até {absence_requests[self.request_id]['data_fim'].strftime('%d/%m/%Y')}\n"
                    f"👤 **Aprovado por:** {interaction.user.display_name}\n"
                    f"🏷️ **Cargo atribuído:** {absence_role.name if absence_role else 'AUSENTE'}\n\n"
                    f"🔹 Aproveite seu período de ausência!\n"
                    f"🔹 Lembre-se de retornar na data prevista\n\n"
                    f"👮‍♂️ **PMESP - Servir e Proteger**"
                ),
                color=0x00ff00
            )
            await solicitante.send(embed=solicitante_embed)
        except:
            pass  # Caso não consiga enviar DM

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label='❌ Negar', style=discord.ButtonStyle.danger, custom_id='negar_ausencia')
    async def negar_ausencia(self, interaction: discord.Interaction, button: discord.ui.Button):
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para negar ausências!**', ephemeral=True)
            return

        if self.request_id not in absence_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if absence_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        absence_requests[self.request_id]['status'] = 'negado'
        absence_requests[self.request_id]['negado_por'] = interaction.user

        embed = discord.Embed(
            title='❌ Ausência Negada',
            description=(
                f"**🏠 Ausência #{self.request_id:04d} negada!**\n\n"
                f"👤 **Negado por:** {interaction.user.mention}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff0000
        )

        await interaction.response.send_message(embed=embed)

        # Notificar o solicitante
        try:
            solicitante = absence_requests[self.request_id]['solicitante']
            solicitante_embed = discord.Embed(
                title='❌ Sua Ausência Foi Negada',
                description=(
                    f"**😔 Infelizmente, sua solicitação de ausência foi negada.**\n\n"
                    f"🆔 **ID:** #{self.request_id:04d}\n"
                    f"📅 **Período solicitado:** {absence_requests[self.request_id]['data_inicio'].strftime('%d/%m/%Y')} até {absence_requests[self.request_id]['data_fim'].strftime('%d/%m/%Y')}\n"
                    f"👤 **Negado por:** {interaction.user.display_name}\n\n"
                    f"🔹 Entre em contato com a administração para mais informações\n"
                    f"🔹 Você pode fazer uma nova solicitação se necessário\n\n"
                    f"👮‍♂️ **PMESP - Servir e Proteger**"
                ),
                color=0xff0000
            )
            await solicitante.send(embed=solicitante_embed)
        except:
            pass  # Caso não consiga enviar DM

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

class ViaturaApprovalView(discord.ui.View):
    def __init__(self, request_id):
        super().__init__(timeout=300)
        self.request_id = request_id

    @discord.ui.button(label='✅ Aprovar', style=discord.ButtonStyle.success, custom_id='aprovar_viatura')
    async def aprovar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para aprovar viaturas!**', ephemeral=True)
            return

        if self.request_id not in viatura_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if viatura_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        viatura_requests[self.request_id]['status'] = 'aprovado'
        viatura_requests[self.request_id]['aprovado_por'] = interaction.user

        aprovador_patente, _ = get_user_patente(interaction.user)

        embed = discord.Embed(
            title='✅ Viatura Aprovada',
            description=(
                f"**🚔 Viatura #{self.request_id:04d} aprovada!**\n\n"
                f"👤 **Aprovado por:** {interaction.user.mention}\n"
                f"🏆 **Patente:** {aprovador_patente.replace('_', ' ').title()}\n"
                f"🆔 **ID in-game:** {interaction.user.display_name}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label='❌ Negar', style=discord.ButtonStyle.danger, custom_id='negar_viatura')
    async def negar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para negar viaturas!**', ephemeral=True)
            return

        if self.request_id not in viatura_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if viatura_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        viatura_requests[self.request_id]['status'] = 'negado'
        viatura_requests[self.request_id]['negado_por'] = interaction.user

        embed = discord.Embed(
            title='❌ Viatura Negada',
            description=(
                f"**🚔 Viatura #{self.request_id:04d} negada!**\n\n"
                f"👤 **Negado por:** {interaction.user.mention}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff0000
        )

        await interaction.response.send_message(embed=embed)

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

class ViaturaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🚔 Solicitar Viatura', style=discord.ButtonStyle.primary, custom_id='solicitar_viatura', emoji='🚨')
    async def solicitar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or interaction.user.voice.channel.id not in VIATURA_VOICE_CHANNELS:
            embed = discord.Embed(
                title='❌ Canal de Voz Necessário',
                description=(
                    f"**{interaction.user.mention}, você precisa estar em um canal de voz autorizado!**\n\n"
                    f"🔹 Entre em um dos canais de voz da Central\n"
                    f"🔹 Tente solicitar a viatura novamente\n\n"
                    f"📍 **Canais autorizados:** Canais da Central PMESP"
                ),
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        voice_members = [member for member in voice_channel.members if member != interaction.user and not member.bot]

        if not voice_members:
            embed = discord.Embed(
                title='⚠️ Nenhum Membro Disponível',
                description=(
                    f"**{interaction.user.mention}, não há outros membros no canal de voz!**\n\n"
                    f"🔹 Aguarde outros policiais entrarem no canal\n"
                    f"🔹 Ou solicite uma viatura individual"
                ),
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        modal = ViaturaSelectorModal(voice_members)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🏠 Solicitar Ausência', style=discord.ButtonStyle.secondary, custom_id='solicitar_ausencia', emoji='📋')
    async def solicitar_ausencia(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AbsenceRequestModal()
        await interaction.response.send_modal(modal)

# Classes para o sistema de setagem de cargos
class CargoRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📌 Solicitar Setagem', style=discord.ButtonStyle.primary, custom_id='solicitar_cargo')
    async def solicitar_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CargoRequestModal()
        await interaction.response.send_modal(modal)

class CargoRequestModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='🎖️ Solicitação de Setagem de Cargo')

        self.target_user = discord.ui.TextInput(
            label='Usuário (mencione com @)',
            placeholder='Ex: @Pedro Blanc',
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )
        self.add_item(self.target_user)

        self.cargo_name = discord.ui.TextInput(
            label='Nome do Cargo',
            placeholder='Ex: CEL, MAJ, CAP, 1°TEN, etc.',
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )
        self.add_item(self.cargo_name)

        self.reason = discord.ui.TextInput(
            label='Motivo da Solicitação',
            placeholder='Descreva o motivo da setagem de cargo...',
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Extrair ID do usuário mencionado
            user_mention = self.target_user.value.strip()
            user_id_match = re.search(r'<@!?(\d+)>', user_mention)

            if not user_id_match:
                await interaction.response.send_message('❌ **Formato de usuário inválido! Use @usuário**', ephemeral=True)
                return

            user_id = int(user_id_match.group(1))
            target_member = interaction.guild.get_member(user_id)

            if not target_member:
                await interaction.response.send_message('❌ **Usuário não encontrado no servidor!**', ephemeral=True)
                return

            # Buscar cargo pelo nome
            cargo_nome = self.cargo_name.value.strip().upper()
            cargo_id = None

            for cid, info in CARGO_CONFIG.items():
                if info["nome"].upper() == cargo_nome:
                    cargo_id = cid
                    break

            if not cargo_id:
                await interaction.response.send_message(f'❌ **Cargo "{cargo_nome}" não encontrado na configuração!**', ephemeral=True)
                return

            cargo_role = interaction.guild.get_role(cargo_id)
            if not cargo_role:
                await interaction.response.send_message(f'❌ **Cargo "{cargo_nome}" não existe no servidor!**', ephemeral=True)
                return

            request_id = len(cargo_requests) + 1
            cargo_requests[request_id] = {
                'solicitante': interaction.user,
                'target': target_member,
                'cargo_id': cargo_id,
                'cargo_nome': cargo_nome,
                'motivo': self.reason.value,
                'timestamp': datetime.now(),
                'status': 'pendente'
            }

            log_channel = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title='🎖️ Solicitação de Setagem de Cargo',
                    description=(
                        f"**📋 Nova solicitação de setagem de cargo!**\n\n"
                        f"🆔 **ID:** #{request_id:04d}\n"
                        f"👤 **Solicitante:** {interaction.user.mention}\n"
                        f"🎯 **Usuário alvo:** {target_member.mention}\n"
                        f"🏷️ **Cargo:** {cargo_role.mention} ({cargo_nome})\n"
                        f"📝 **Motivo:** {self.reason.value}\n"
                        f"🕐 **Solicitado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                    ),
                    color=0x800080
                )
                embed.set_thumbnail(url=target_member.display_avatar.url)
                embed.set_footer(text='PMESP - Sistema de Setagem de Cargos', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

                approval_view = CargoApprovalView(request_id)
                await log_channel.send(embed=embed, view=approval_view)

            await interaction.response.send_message(
                f'✅ **Solicitação de setagem de cargo enviada!**\n'
                f'🆔 **ID:** #{request_id:04d}\n'
                f'🎯 **Usuário:** {target_member.display_name}\n'
                f'🏷️ **Cargo:** {cargo_nome}\n'
                f'⏰ **Aguardando aprovação...**',
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f'❌ **Erro ao processar solicitação:** {str(e)}', ephemeral=True)

class CargoApprovalView(discord.ui.View):
    def __init__(self, request_id):
        super().__init__(timeout=None)
        self.request_id = request_id

    @discord.ui.button(label='✅ Aceitar', style=discord.ButtonStyle.success, custom_id='aceitar_cargo')
    async def aceitar_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if PANEL_PERMISSION_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para aprovar setagem de cargos!**', ephemeral=True)
            return

        if self.request_id not in cargo_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if cargo_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        try:
            request_data = cargo_requests[self.request_id]
            target_member = request_data['target']
            cargo_id = request_data['cargo_id']
            cargo_nome = request_data['cargo_nome']

            guild = interaction.guild
            cargo_role = guild.get_role(cargo_id)

            if not cargo_role:
                await interaction.response.send_message('❌ **Cargo não encontrado no servidor!**', ephemeral=True)
                return

            # Obter informações do cargo
            cargo_info = CARGO_CONFIG[cargo_id]

            # Formatar novo nickname
            novo_apelido = format_nickname(target_member, cargo_nome)

            # Remover todos os cargos anteriores da configuração
            todos_cargos_ids = list(CARGO_CONFIG.keys()) + [info["pai"] for info in CARGO_CONFIG.values() if info["pai"]]
            cargos_a_remover = [guild.get_role(cid) for cid in todos_cargos_ids if guild.get_role(cid)]
            cargos_a_remover = [role for role in cargos_a_remover if role in target_member.roles]

            if cargos_a_remover:
                await target_member.remove_roles(*cargos_a_remover, reason=f'Setagem de cargo - ID #{self.request_id:04d}')

            # Adicionar novo cargo
            await target_member.add_roles(cargo_role, reason=f'Setagem de cargo - ID #{self.request_id:04d}')

            # Adicionar cargo pai se existir
            if cargo_info["pai"]:
                cargo_pai = guild.get_role(cargo_info["pai"])
                if cargo_pai:
                    await target_member.add_roles(cargo_pai, reason=f'Cargo agrupador - ID #{self.request_id:04d}')

            # Atualizar nickname
            try:
                await target_member.edit(nick=novo_apelido, reason=f'Setagem de cargo - ID #{self.request_id:04d}')
            except discord.Forbidden:
                pass  # Pode não ter permissão para alterar nickname de alguns usuários

            cargo_requests[self.request_id]['status'] = 'aprovado'
            cargo_requests[self.request_id]['aprovado_por'] = interaction.user

            embed = discord.Embed(
                title='✅ Cargo Setado com Sucesso',
                description=(
                    f"**🎖️ Cargo #{self.request_id:04d} setado com sucesso!**\n\n"
                    f"👤 **Aprovado por:** {interaction.user.mention}\n"
                    f"🎯 **Usuário:** {target_member.mention}\n"
                    f"🏷️ **Cargo:** {cargo_role.mention} ({cargo_nome})\n"
                    f"📝 **Novo nickname:** `{novo_apelido}`\n"
                    f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                ),
                color=0x00ff00
            )

            await interaction.response.send_message(embed=embed)

            # Log no canal geral
            general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
            if general_log:
                await general_log.send(
                    f"✅ **Cargo {cargo_role.mention} setado para {target_member.mention}**. "
                    f"Nome alterado para `{novo_apelido}` por {interaction.user.mention}"
                )

            # Notificar o usuário que recebeu o cargo
            try:
                user_embed = discord.Embed(
                    title='🎖️ Seu Cargo Foi Atualizado!',
                    description=(
                        f"**🎉 Parabéns! Seu cargo foi atualizado com sucesso.**\n\n"
                        f"🆔 **ID:** #{self.request_id:04d}\n"
                        f"🏷️ **Novo cargo:** {cargo_role.name} ({cargo_nome})\n"
                        f"📝 **Novo nickname:** `{novo_apelido}`\n"
                        f"👤 **Aprovado por:** {interaction.user.display_name}\n\n"
                        f"🔹 Seu perfil foi atualizado automaticamente\n"
                        f"🔹 Aproveite suas novas responsabilidades!\n\n"
                        f"👮‍♂️ **PMESP - Servir e Proteger**"
                    ),
                    color=0x00ff00
                )
                await target_member.send(embed=user_embed)
            except:
                pass  # Caso não consiga enviar DM

            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            await interaction.response.send_message(f'❌ **Erro ao setar cargo:** {str(e)}', ephemeral=True)

    @discord.ui.button(label='❌ Negar', style=discord.ButtonStyle.danger, custom_id='negar_cargo')
    async def negar_cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if PANEL_PERMISSION_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para negar setagem de cargos!**', ephemeral=True)
            return

        if self.request_id not in cargo_requests:
            await interaction.response.send_message('❌ **Solicitação não encontrada!**', ephemeral=True)
            return

        if cargo_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message('❌ **Esta solicitação já foi processada!**', ephemeral=True)
            return

        cargo_requests[self.request_id]['status'] = 'negado'
        cargo_requests[self.request_id]['negado_por'] = interaction.user

        request_data = cargo_requests[self.request_id]
        target_member = request_data['target']

        embed = discord.Embed(
            title='❌ Setagem de Cargo Negada',
            description=(
                f"**🎖️ Setagem de cargo #{self.request_id:04d} negada!**\n\n"
                f"👤 **Negado por:** {interaction.user.mention}\n"
                f"🎯 **Usuário:** {target_member.mention}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff0000
        )

        await interaction.response.send_message(embed=embed)

        # Log no canal geral
        general_log = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f"❌ **Cargo NÃO foi setado para {target_member.mention}** (negado por {interaction.user.mention})")

        # Notificar o solicitante
        try:
            solicitante = request_data['solicitante']
            solicitante_embed = discord.Embed(
                title='❌ Sua Solicitação Foi Negada',
                description=(
                    f"**😔 Infelizmente, sua solicitação de setagem de cargo foi negada.**\n\n"
                    f"🆔 **ID:** #{self.request_id:04d}\n"
                    f"🎯 **Usuário:** {target_member.display_name}\n"
                    f"🏷️ **Cargo solicitado:** {request_data['cargo_nome']}\n"
                    f"👤 **Negado por:** {interaction.user.display_name}\n\n"
                    f"🔹 Entre em contato com a administração para mais informações\n"
                    f"🔹 Você pode fazer uma nova solicitação se necessário\n\n"
                    f"👮‍♂️ **PMESP - Servir e Proteger**"
                ),
                color=0xff0000
            )
            await solicitante.send(embed=solicitante_embed)
        except:
            pass  # Caso não consiga enviar DM

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

# Eventos do Bot
@bot.event
async def on_ready():
    print(f'🤖 Bot {bot.user} está online!')
    print(f'📊 Conectado a {len(bot.guilds)} servidor(s)')

    # Adiciona as views persistentes
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
    bot.add_view(BatePontoView())
    bot.add_view(ViaturaView())
    bot.add_view(AbsenceApprovalView(0))  # Dummy view para registrar o custom_id
    bot.add_view(CargoRequestView())
    bot.add_view(CargoApprovalView(0))  # Dummy view para registrar o custom_id

    # Inicia tasks
    check_voice_alerts.start()

@bot.event
async def on_voice_state_update(member, before, after):
    """Monitora mudanças de estado de voz"""

    if before.channel and before.channel.id in VOICE_CHANNELS and (not after.channel or after.channel.id not in VOICE_CHANNELS):
        voice_alerts[member.id] = {
            'timeout': datetime.now() + timedelta(minutes=2),
            'channel_left': before.channel.id
        }

        alert_channel = member.guild.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title='⚠️ Alerta de Saída de Canal',
                description=(
                    f"**👤 Usuário:** {member.mention}\n"
                    f"**📍 Canal:** {before.channel.name}\n"
                    f"**🕐 Horário:** {datetime.now().strftime('%H:%M:%S')}\n"
                    f"**⏰ Tempo limite:** 2 minutos para retornar"
                ),
                color=0xff9900
            )
            await alert_channel.send(embed=embed)

    elif after.channel and after.channel.id in VOICE_CHANNELS and member.id in voice_alerts:
        del voice_alerts[member.id]

        alert_channel = member.guild.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title='✅ Retorno Confirmado',
                description=(
                    f"**👤 Usuário:** {member.mention}\n"
                    f"**📍 Canal:** {after.channel.name}\n"
                    f"**🕐 Horário:** {datetime.now().strftime('%H:%M:%S')}"
                ),
                color=0x00ff00
            )
            await alert_channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    """Log quando um membro entra no servidor"""
    general_log = member.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title='👋 Membro Entrou',
            description=(
                f"**Novo membro no servidor!**\n\n"
                f"👤 **Usuário:** {member.mention}\n"
                f"🆔 **ID:** {member.id}\n"
                f"📅 **Conta criada:** {member.created_at.strftime('%d/%m/%Y')}\n"
                f"🕐 **Entrou em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x00ff00
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_member_remove(member):
    """Log quando um membro sai do servidor"""
    general_log = member.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title='👋 Membro Saiu',
            description=(
                f"**Membro saiu do servidor!**\n\n"
                f"👤 **Usuário:** {member.display_name}\n"
                f"🆔 **ID:** {member.id}\n"
                f"🕐 **Saiu em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff0000
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    """Log quando um membro é atualizado (cargos, nick, etc.)"""
    general_log = after.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if not general_log:
        return

    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]

        if added_roles or removed_roles:
            embed = discord.Embed(
                title='🏷️ Cargos Atualizados',
                description=(
                    f"**Cargos do membro foram alterados!**\n\n"
                    f"👤 **Usuário:** {after.mention}\n"
                    f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                ),
                color=0x0066cc
            )

            if added_roles:
                embed.add_field(
                    name='➕ Cargos Adicionados',
                    value='\n'.join([f'🔹 {role.name}' for role in added_roles]),
                    inline=False
                )

            if removed_roles:
                embed.add_field(
                    name='➖ Cargos Removidos',
                    value='\n'.join([f'🔹 {role.name}' for role in removed_roles]),
                    inline=False
                )

            embed.set_thumbnail(url=after.display_avatar.url)
            await general_log.send(embed=embed)

    if before.display_name != after.display_name:
        embed = discord.Embed(
            title='📝 Nickname Alterado',
            description=(
                f"**Nickname do membro foi alterado!**\n\n"
                f"👤 **Usuário:** {after.mention}\n"
                f"📝 **Antes:** {before.display_name}\n"
                f"📝 **Depois:** {after.display_name}\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x0066cc
        )
        embed.set_thumbnail(url=after.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_message_delete(message):
    """Log quando uma mensagem é deletada"""
    if message.author.bot:
        return

    general_log = message.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log and message.channel.id != GENERAL_LOG_CHANNEL_ID:
        embed = discord.Embed(
            title='🗑️ Mensagem Deletada',
            description=(
                f"**Mensagem foi deletada!**\n\n"
                f"👤 **Autor:** {message.author.mention}\n"
                f"📍 **Canal:** {message.channel.mention}\n"
                f"📝 **Conteúdo:** {message.content[:500] if message.content else '*Sem conteúdo de texto*'}\n"
                f"🕐 **Deletada em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff9900
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    """Log quando uma mensagem é editada"""
    if before.author.bot or before.content == after.content:
        return

    general_log = after.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log and after.channel.id != GENERAL_LOG_CHANNEL_ID:
        embed = discord.Embed(
            title='✏️ Mensagem Editada',
            description=(
                f"**Mensagem foi editada!**\n\n"
                f"👤 **Autor:** {after.mention}\n"
                f"📍 **Canal:** {after.channel.mention}\n"
                f"🔗 **Link:** [Ir para mensagem]({after.jump_url})\n"
                f"🕐 **Editada em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x0066cc
        )

        if before.content:
            embed.add_field(
                name='📝 Antes',
                value=before.content[:500] + ('...' if len(before.content) > 500 else ''),
                inline=False
            )

        if after.content:
            embed.add_field(
                name='📝 Depois',
                value=after.content[:500] + ('...' if len(after.content) > 500 else ''),
                inline=False
            )

        embed.set_thumbnail(url=after.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    """Log quando um canal é criado"""
    general_log = channel.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title='📢 Canal Criado',
            description=(
                f"**Novo canal criado!**\n\n"
                f"📍 **Canal:** {channel.mention}\n"
                f"📝 **Nome:** {channel.name}\n"
                f"🏷️ **Tipo:** {channel.type}\n"
                f"🕐 **Criado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x00ff00
        )
        await general_log.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    """Log quando um canal é deletado"""
    general_log = channel.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title='🗑️ Canal Deletado',
            description=(
                f"**Canal foi deletado!**\n\n"
                f"📝 **Nome:** {channel.name}\n"
                f"🏷️ **Tipo:** {channel.type}\n"
                f"🕐 **Deletado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0xff0000
        )
        await general_log.send(embed=embed)

# Task para verificar alertas de voz
@tasks.loop(seconds=30)
async def check_voice_alerts():
    """Verifica se usuários saíram dos canais de voz e gerencia alertas"""
    current_time = datetime.now()

    for user_id, alert_data in list(voice_alerts.items()):
        if current_time >= alert_data['timeout']:
            if user_id in bate_ponto_data and bate_ponto_data[user_id]['status'] == 'aberto':
                bate_ponto_data[user_id]['status'] = 'fechado'
                bate_ponto_data[user_id]['end_time'] = current_time

                start_time = bate_ponto_data[user_id]['start_time']
                worked_hours = (current_time - start_time).total_seconds() / 3600

                if 'total_hours' not in bate_ponto_data[user_id]:
                    bate_ponto_data[user_id]['total_hours'] = 0
                bate_ponto_data[user_id]['total_hours'] += worked_hours

                guild = bot.get_guild(GUILD_ID) if GUILD_ID else bot.guilds[0]
                general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
                if general_log:
                    user = guild.get_member(user_id)
                    await general_log.send(
                        f"⏰ **Bate-ponto fechado automaticamente** para {user.mention if user else f'<@{user_id}>'} "
                        f"(não retornou ao canal de voz em 2 minutos)"
                    )

            del voice_alerts[user_id]

# Comandos do Bot
@bot.command(name='setup_tickets')
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """Comando para configurar o painel de tickets"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send('❌ **Canal de tickets não encontrado!**')
        return

    embed = discord.Embed(
        title='🎫 Sistema de Tickets PMESP',
        description=(
            "**🚔 Bem-vindo ao Sistema de Tickets da PMESP! 🚔**\n\n"
            "📋 **Como funciona:**\n"
            "🔹 Clique no botão abaixo para abrir um ticket\n"
            "🔹 Descreva sua solicitação detalhadamente\n"
            "🔹 Nossa equipe responderá em breve\n"
            "🔹 O ticket será criado em um canal privado\n\n"
            "⚠️ **Importante:**\n"
            "🔸 Use apenas para assuntos oficiais\n"
            "🔸 Seja claro e objetivo\n"
            "🔸 Aguarde a resposta da equipe\n"
            "🔸 Não abra tickets desnecessários\n\n"
            "🏛️ **PMESP - Polícia Militar do Estado de São Paulo**\n"
            "👮‍♂️ *Servir e Proteger*"
        ),
        color=0x0066cc
    )
    embed.set_footer(text='PMESP - Sistema Oficial de Tickets', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = TicketView()
    await channel.send(embed=embed, view=view)
    await ctx.send('✅ **Painel de tickets configurado com sucesso!**')

@bot.command(name='setup_bate_ponto')
@commands.has_permissions(administrator=True)
async def setup_bate_ponto(ctx):
    """Comando para configurar o painel de bate-ponto"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    channel = bot.get_channel(BATE_PONTO_CHANNEL_ID)
    if not channel:
        await ctx.send('❌ **Canal de bate-ponto não encontrado!**')
        return

    embed = discord.Embed(
        title='⏰ Sistema de Bate-Ponto PMESP',
        description=(
            "**🚔 Bem-vindo ao Sistema de Bate-Ponto da PMESP! 🚔**\n\n"
            "📋 **Como funciona:**\n"
            "🟢 **Abrir Ponto:** Inicia seu expediente\n"
            "🔴 **Fechar Ponto:** Encerra seu expediente\n"
            "📊 **Minhas Horas:** Visualiza seu relatório\n\n"
            "⚠️ **Importante:**\n"
            "🔸 Você deve estar em um canal de voz válido\n"
            "🔸 Mantenha-se no canal durante o expediente\n"
            "🔸 Se sair do canal, você tem 2 minutos para retornar\n"
            "🔸 Após 2 minutos, o ponto será fechado automaticamente\n"
            "🔸 Sempre feche o ponto ao final do expediente\n\n"
            "📊 **Funcionalidades:**\n"
            "⏱️ Controle automático de horas\n"
            "📈 Relatórios individuais\n"
            "🔔 Alertas de saída de canal\n"
            "💾 Histórico de pontos\n\n"
            "🏛️ **PMESP - Polícia Militar do Estado de São Paulo**\n"
            "👮‍♂️ *Servir e Proteger*"
        ),
        color=0x0066cc
    )
    embed.set_footer(text='PMESP - Sistema Oficial de Bate-Ponto', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = BatePontoView()
    await channel.send(embed=embed, view=view)
    await ctx.send('✅ **Painel de bate-ponto configurado com sucesso!**')

@bot.command(name='setup_central')
@commands.has_permissions(administrator=True)
async def setup_central(ctx):
    """Comando para configurar o painel da central"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    channel = bot.get_channel(CENTRAL_CHANNEL_ID)
    if not channel:
        await ctx.send('❌ **Canal da central não encontrado!**')
        return

    embed = discord.Embed(
        title='🚔 Central de Operações PMESP',
        description=(
            "**🚨 Bem-vindo à Central de Operações da PMESP! 🚨**\n\n"
            "📋 **Sistemas Disponíveis:**\n\n"
            "🚔 **Solicitação de Viaturas:**\n"
            "🔹 Clique no botão 'Solicitar Viatura' abaixo\n"
            "🔹 Você deve estar em um canal de voz autorizado\n"
            "🔹 Selecione até 3 pessoas para compor a viatura\n"
            "🔹 Descreva o motivo da solicitação\n\n"
            "🏠 **Solicitação de Ausências:**\n"
            "🔹 Clique no botão 'Solicitar Ausência' abaixo\n"
            "🔹 Informe o período de ausência (data início/fim)\n"
            "🔹 Descreva detalhadamente o motivo\n"
            "🔹 Aguarde aprovação da administração\n\n"
            "⚠️ **Requisitos:**\n"
            "🔸 Para viaturas: estar em canal de voz da Central\n"
            "🔸 Máximo de 3 pessoas por viatura\n"
            "🔸 Motivo válido para todas as solicitações\n"
            "🔸 Aguardar aprovação do responsável\n\n"
            "📊 **Processo de Aprovação:**\n"
            "⏱️ Tempo limite: 5 minutos (viaturas)\n"
            "🤖 Aprovação automática se não houver resposta\n"
            "👮‍♂️ Aprovação manual pelo responsável\n"
            "📋 Log completo de todas as solicitações\n\n"
            "🏛️ **PMESP - Polícia Militar do Estado de São Paulo**\n"
            "👮‍♂️ *Servir e Proteger*"
        ),
        color=0x0066cc
    )
    embed.set_footer(text='PMESP - Central de Operações', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = ViaturaView()
    await channel.send(embed=embed, view=view)
    await ctx.send('✅ **Painel da central configurado com sucesso!**')

@bot.command(name='painelsetarcargo')
@commands.has_permissions(administrator=True)
async def painel_setar_cargo(ctx):
    """Comando para configurar o painel de setagem de cargos"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    embed = discord.Embed(
        title='🎖️ Painel de Setagem de Cargo PMESP',
        description=(
            "**🚔 Sistema de Setagem Automática de Cargos da PMESP! 🚔**\n\n"
            "📋 **Como funciona:**\n"
            "🔹 Clique no botão abaixo para solicitar setagem de cargo\n"
            "🔹 Informe o usuário e o cargo desejado\n"
            "🔹 Descreva o motivo da solicitação\n"
            "🔹 Um moderador irá aprovar ou negar\n\n"
            "🎖️ **Cargos Disponíveis:**\n"
            "🔸 **Oficiais Superiores:** CEL, T.CEL, MAJ\n"
            "🔸 **Oficiais Intermediários:** CAP\n"
            "🔸 **Oficiais Subalternos:** 1°TEN, 2°TEN\n"
            "🔸 **Aspirante:** ASP\n"
            "🔸 **Praças Especiais:** S.TEN, 1°SGT, 2°SGT, 3°SGT\n"
            "🔸 **Praças:** CB, SD-1ª, SD-2ª\n"
            "🔸 **Especial:** SCGPM\n\n"
            "⚠️ **Importante:**\n"
            "🔸 O nickname será formatado automaticamente\n"
            "🔸 Cargos anteriores serão removidos\n"
            "🔸 Aguarde aprovação da administração\n"
            "🔸 Use apenas para setagens oficiais\n\n"
            "🏛️ **PMESP - Polícia Militar do Estado de São Paulo**\n"
            "👮‍♂️ *Servir e Proteger*"
        ),
        color=0x800080
    )
    embed.set_footer(text='PMESP - Sistema de Setagem de Cargos', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = CargoRequestView()
    await ctx.send('✅ **Painel de setagem de cargo enviado!**', ephemeral=True)
    await ctx.send(embed=embed, view=view)

@bot.command(name='setarcargo')
@commands.has_permissions(administrator=True)
async def setar_cargo_interativo(ctx):
    """Comando interativo para setar cargo com seleção de múltiplos membros"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    embed = discord.Embed(
        title='🎖️ Setagem Interativa de Cargo',
        description=(
            "**🔧 Sistema de Setagem de Cargo PMESP**\n\n"
            "🔹 Selecione múltiplos membros\n"
            "🔹 Escolha o cargo por nome ou ID\n"
            "🔹 Formatação automática do nickname\n"
            "🔹 Remoção automática de cargos anteriores\n\n"
            "**Clique no botão abaixo para começar:**"
        ),
        color=0x800080
    )

    view = SetCargoInteractiveView()
    await ctx.send(embed=embed, view=view)

class SetCargoInteractiveView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='🎖️ Iniciar Setagem', style=discord.ButtonStyle.primary)
    async def iniciar_setagem(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetCargoModal()
        await interaction.response.send_modal(modal)

class SetCargoModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='🎖️ Setagem de Cargo PMESP')

        self.membros_input = discord.ui.TextInput(
            label='👥 Membros (IDs ou @menções)',
            placeholder='Ex: @Pedro @João 123456789 987654321',
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )

        self.cargo_input = discord.ui.TextInput(
            label='🎖️ Cargo (Nome ou ID)',
            placeholder='Ex: SCGPM, CEL, 1369351259311575150',
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )

        self.motivo_input = discord.ui.TextInput(
            label='📝 Motivo da Setagem',
            placeholder='Ex: Promoção por mérito, Transferência de setor...',
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )

        self.add_item(self.membros_input)
        self.add_item(self.cargo_input)
        self.add_item(self.motivo_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Processar membros
        membros_text = self.membros_input.value.strip()
        membros = []

        # Extrair IDs e menções
        import re
        ids_mencoes = re.findall(r'<@!?(\d+)>|(\d{17,19})', membros_text)

        for match in ids_mencoes:
            user_id = int(match[0] or match[1])
            member = interaction.guild.get_member(user_id)
            if member:
                membros.append(member)

        if not membros:
            await interaction.response.send_message(
                '❌ **Nenhum membro válido encontrado!**\n'
                'Use @menções ou IDs válidos de membros do servidor.',
                ephemeral=True
            )
            return

        # Processar cargo
        cargo_text = self.cargo_input.value.strip()
        cargo = None
        cargo_config = None

        # Tentar por ID primeiro
        if cargo_text.isdigit():
            cargo_id = int(cargo_text)
            cargo = interaction.guild.get_role(cargo_id)
            if cargo and cargo_id in CARGO_CONFIG:
                cargo_config = CARGO_CONFIG[cargo_id]

        # Se não encontrou por ID, tentar por nome
        if not cargo:
            for role_id, config in CARGO_CONFIG.items():
                if config["nome"].lower() == cargo_text.lower():
                    cargo = interaction.guild.get_role(role_id)
                    cargo_config = config
                    break

        if not cargo or not cargo_config:
            # Mostrar cargos disponíveis
            cargos_disponiveis = []
            for role_id, config in CARGO_CONFIG.items():
                role = interaction.guild.get_role(role_id)
                if role:
                    cargos_disponiveis.append(f"🔹 **{config['nome']}** (ID: {role_id})")

            embed_erro = discord.Embed(
                title='❌ Cargo Não Encontrado',
                description=(
                    f"**Cargo '{cargo_text}' não foi encontrado!**\n\n"
                    "**📋 Cargos disponíveis:**\n" + "\n".join(cargos_disponiveis)
                ),
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_erro, ephemeral=True)
            return

        # Criar embed de confirmação
        membros_lista = "\n".join([f"🔹 {member.display_name} ({member.mention})" for member in membros])

        embed = discord.Embed(
            title='📋 Confirmação de Setagem de Cargo',
            description=(
                f"**🎖️ Cargo:** {cargo.mention} ({cargo_config['nome']})\n"
                f"**👥 Membros ({len(membros)}):**\n{membros_lista}\n\n"
                f"**📝 Motivo:** {self.motivo_input.value}\n\n"
                f"**⚠️ Ações que serão executadas:**\n"
                f"🔹 Remover todos os cargos PMESP anteriores\n"
                f"🔹 Adicionar o novo cargo\n"
                f"🔹 Formatar nickname automaticamente\n"
                f"🔹 Enviar logs para o canal apropriado\n\n"
                f"**Deseja confirmar a setagem?**"
            ),
            color=0x800080
        )

        # Criar solicitação para cada membro
        request_ids = []
        for member in membros:
            request_id = len(cargo_requests) + 1
            cargo_requests[request_id] = {
                'solicitante': interaction.user,
                'target': member,
                'cargo_id': cargo.id,
                'cargo_nome': cargo_config["nome"],
                'motivo': self.motivo_input.value,
                'timestamp': datetime.now(),
                'status': 'pendente'
            }
            request_ids.append(request_id)

        view = CargoMultipleApprovalView(request_ids)
        await interaction.response.send_message(embed=embed, view=view)

class CargoMultipleApprovalView(discord.ui.View):
    def __init__(self, request_ids):
        super().__init__(timeout=300)
        self.request_ids = request_ids

    @discord.ui.button(label='✅ Confirmar Setagem', style=discord.ButtonStyle.success)
    async def aceitar_setagem(self, interaction: discord.Interaction, button: discord.ui.Button):
        if PANEL_PERMISSION_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para confirmar setagens!**', ephemeral=True)
            return

        sucessos = []
        erros = []

        for request_id in self.request_ids:
            if request_id not in cargo_requests:
                continue

            request = cargo_requests[request_id]
            target = request['target']
            cargo_id = request['cargo_id']
            cargo_nome = request['cargo_nome']

            try:
                # Remover todos os cargos PMESP anteriores
                cargos_para_remover = []
                for role in target.roles:
                    if role.id in CARGO_CONFIG:
                        cargos_para_remover.append(role)
                    # Remover cargos "pai" também
                    for config_id, config in CARGO_CONFIG.items():
                        if config.get("pai") == role.id:
                            cargos_para_remover.append(role)

                if cargos_para_remover:
                    await target.remove_roles(*cargos_para_remover, reason=f'Setagem de cargo por {interaction.user}')

                # Adicionar novo cargo
                novo_cargo = interaction.guild.get_role(cargo_id)
                if novo_cargo:
                    await target.add_roles(novo_cargo, reason=f'Setagem de cargo por {interaction.user}')

                # Adicionar cargo "pai" se existir
                cargo_config = CARGO_CONFIG[cargo_id]
                if cargo_config.get("pai"):
                    cargo_pai = interaction.guild.get_role(cargo_config["pai"])
                    if cargo_pai:
                        await target.add_roles(cargo_pai, reason=f'Cargo pai para {cargo_nome}')

                # Formatar nickname
                novo_nickname = format_nickname(target, cargo_nome)
                if novo_nickname != target.display_name:
                    await target.edit(nick=novo_nickname, reason=f'Formatação automática para cargo {cargo_nome}')

                sucessos.append(f"✅ {target.display_name} → {cargo_nome}")

                # Atualizar status da solicitação
                cargo_requests[request_id]['status'] = 'aceito'
                cargo_requests[request_id]['aprovado_por'] = interaction.user

                # Enviar DM para o usuário
                try:
                    embed_dm = discord.Embed(
                        title='🎖️ Cargo Atualizado',
                        description=(
                            f"**Seu cargo foi atualizado com sucesso!**\n\n"
                            f"🎖️ **Novo Cargo:** {cargo_nome}\n"
                            f"👤 **Aprovado por:** {interaction.user.display_name}\n"
                            f"📝 **Motivo:** {request['motivo']}\n"
                            f"🕐 **Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                        ),
                        color=0x00ff00
                    )
                    await target.send(embed=embed_dm)
                except:
                    pass  # Ignorar se não conseguir enviar DM

            except Exception as e:
                erros.append(f"❌ {target.display_name} → Erro: {str(e)}")
                cargo_requests[request_id]['status'] = 'erro'

        # Resposta de confirmação
        resultado_texto = ""
        if sucessos:
            resultado_texto += "**✅ Setagens Realizadas:**\n" + "\n".join(sucessos) + "\n\n"
        if erros:
            resultado_texto += "**❌ Erros Encontrados:**\n" + "\n".join(erros)

        embed_resultado = discord.Embed(
            title='📊 Resultado da Setagem',
            description=resultado_texto,
            color=0x00ff00 if not erros else 0xff9900
        )

        await interaction.response.send_message(embed=embed_resultado)

        # Log no canal geral
        general_log = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            embed_log = discord.Embed(
                title='🎖️ Setagem de Cargo Executada',
                description=(
                    f"**👤 Executado por:** {interaction.user.mention}\n"
                    f"**📊 Total de membros:** {len(self.request_ids)}\n"
                    f"**✅ Sucessos:** {len(sucessos)}\n"
                    f"**❌ Erros:** {len(erros)}\n"
                    f"**🕐 Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                ),
                color=0x800080
            )
            await general_log.send(embed=embed_log)

        # Desabilitar botões
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.danger)
    async def cancelar_setagem(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Marcar todas as solicitações como canceladas
        for request_id in self.request_ids:
            if request_id in cargo_requests:
                cargo_requests[request_id]['status'] = 'cancelado'

        embed = discord.Embed(
            title='❌ Setagem Cancelada',
            description=f"**Setagem de {len(self.request_ids)} membro(s) foi cancelada.**",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Desabilitar botões
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

@bot.command(name='status')
@commands.has_permissions(administrator=True)
async def status_sistema(ctx):
    """Mostra o status do sistema"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    pontos_abertos = len([data for data in bate_ponto_data.values() if data.get('status') == 'aberto'])
    viaturas_pendentes = len([data for data in viatura_requests.values() if data.get('status') == 'pendente'])
    ausencias_pendentes = len([data for data in absence_requests.values() if data.get('status') == 'pendente'])
    cargos_pendentes = len([data for data in cargo_requests.values() if data.get('status') == 'pendente'])
    alertas_ativos = len(voice_alerts)

    embed = discord.Embed(
        title='📊 Status do Sistema PMESP',
        description=(
            "**🤖 Bot Online e Funcionando!**\n\n"
            "📈 **Estatísticas Atuais:**\n"
            f"🎫 **Tickets:** {ticket_counter} total criados\n"
            f"⏰ **Pontos Abertos:** {pontos_abertos}\n"
            f"🚔 **Viaturas Pendentes:** {viaturas_pendentes}\n"
            f"🏠 **Ausências Pendentes:** {ausencias_pendentes}\n"
            f"🎖️ **Setagens de Cargo Pendentes:** {cargos_pendentes}\n"
            f"⚠️ **Alertas Ativos:** {alertas_ativos}\n\n"
            "🔧 **Sistemas Ativos:**\n"
            "✅ Sistema de Tickets\n"
            "✅ Sistema de Bate-Ponto\n"
            "✅ Sistema de Viaturas\n"
            "✅ Sistema de Ausências\n"
            "✅ Sistema de Setagem de Cargos\n"
            "✅ Sistema de Logs\n"
            "✅ Sistema de Alertas\n\n"
            f"🕐 **Última atualização:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
        ),
        color=0x00ff00
    )
    embed.set_footer(text='PMESP - Sistema de Gestão', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    await ctx.send(embed=embed)

@bot.command(name='setup_all')
@commands.has_permissions(administrator=True)
async def setup_all(ctx):
    """Configura todos os painéis de uma vez"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    await ctx.send('🔄 **Configurando todos os painéis...**')

    try:
        await setup_tickets(ctx)
        await asyncio.sleep(1)

        await setup_bate_ponto(ctx)
        await asyncio.sleep(1)

        await setup_central(ctx)
        await asyncio.sleep(1)

        await painel_setar_cargo(ctx)

        await ctx.send('✅ **Todos os painéis foram configurados com sucesso!**')

    except Exception as e:
        await ctx.send(f'❌ **Erro durante a configuração:** {str(e)}')

@bot.command(name='setup_resethoras')
@commands.has_permissions(administrator=True)
async def setup_reset_horas(ctx):
    """Comando para resetar as horas do bate-ponto de todos os membros"""

    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send('❌ **Você não tem permissão para usar este comando!**')
        return

    if not bate_ponto_data:
        await ctx.send('❌ **Não há dados de bate-ponto para resetar!**')
        return

    # Confirmar reset
    embed = discord.Embed(
        title='⚠️ Confirmação de Reset de Horas',
        description=(
            "**🚨 ATENÇÃO: Esta ação irá resetar TODAS as horas de bate-ponto!**\n\n"
            "🔹 Todos os dados de horas serão zerados\n"
            "🔹 Esta ação não pode ser desfeita\n"
            "🔹 Um relatório será enviado antes do reset\n\n"
            "**Tem certeza que deseja continuar?**"
        ),
        color=0xff0000
    )

    view = ResetHorasConfirmView()
    await ctx.send(embed=embed, view=view)

class ResetHorasConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label='✅ Confirmar Reset', style=discord.ButtonStyle.danger)
    async def confirmar_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if PANEL_PERMISSION_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message('❌ **Você não tem permissão para confirmar o reset!**', ephemeral=True)
            return

        # Gerar relatório antes do reset
        reset_log_channel = interaction.guild.get_channel(RESET_HORAS_LOG_CHANNEL_ID)

        if reset_log_channel:
            # Embed principal do reset
            embed_reset = discord.Embed(
                title='🔄 Reset de Horas Executado',
                description=(
                    f"**📊 Reset de horas realizado com sucesso!**\n\n"
                    f"👤 **Executado por:** {interaction.user.mention}\n"
                    f"🕐 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n"
                    f"📈 **Total de membros afetados:** {len(bate_ponto_data)}\n\n"
                    f"**📋 Relatório detalhado abaixo:**"
                ),
                color=0xff9900
            )
            await reset_log_channel.send(embed=embed_reset)

            # Relatório detalhado dos membros
            membros_ordenados = sorted(
                bate_ponto_data.items(),
                key=lambda x: x[1].get('total_hours', 0),
                reverse=True
            )

            relatorio_texto = "**📊 RELATÓRIO DE HORAS ANTES DO RESET:**\n\n"

            for i, (user_id, data) in enumerate(membros_ordenados, 1):
                member = interaction.guild.get_member(user_id)
                if member:
                    total_hours = data.get('total_hours', 0)
                    hours = int(total_hours)
                    minutes = int((total_hours - hours) * 60)
                    status = "🟢 Ativo" if data.get('status') == 'aberto' else "🔴 Inativo"

                    relatorio_texto += f"**{i:02d}.** {member.display_name}\n"
                    relatorio_texto += f"     ⏱️ **Horas:** {hours:02d}h {minutes:02d}m\n"
                    relatorio_texto += f"     📊 **Status:** {status}\n\n"

                    # Dividir em mensagens se ficar muito longo
                    if len(relatorio_texto) > 1800:
                        embed_relatorio = discord.Embed(
                            title='📋 Relatório de Horas (Parte)',
                            description=relatorio_texto,
                            color=0x0066cc
                        )
                        await reset_log_channel.send(embed=embed_relatorio)
                        relatorio_texto = ""

            # Enviar última parte do relatório
            if relatorio_texto:
                embed_relatorio = discord.Embed(
                    title='📋 Relatório de Horas (Final)',
                    description=relatorio_texto,
                    color=0x0066cc
                )
                await reset_log_channel.send(embed=embed_relatorio)

            # Gerar listas de membros ativos e inativos
            await self.gerar_listas_atividade(interaction.guild, membros_ordenados)

        # Executar o reset
        bate_ponto_data.clear()

        embed_sucesso = discord.Embed(
            title='✅ Reset Concluído',
            description=(
                f"**🎉 Reset de horas executado com sucesso!**\n\n"
                f"🔄 **Todas as horas foram zeradas**\n"
                f"📊 **Relatório enviado para o canal de logs**\n"
                f"📈 **Listas de ativos/inativos atualizadas**\n"
                f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
            ),
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed_sucesso)

        # Log no canal geral
        general_log = interaction.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f"🔄 **Reset de horas executado** por {interaction.user.mention}")

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    async def gerar_listas_atividade(self, guild, membros_ordenados):
        """Gera as listas de membros ativos e inativos"""

        # Canal de membros ativos
        canal_ativos = guild.get_channel(MEMBROS_ATIVOS_CHANNEL_ID)
        if canal_ativos:
            embed_ativos = discord.Embed(
                title='🏆 Membros Mais Ativos',
                description="**📈 Top 20 membros com mais horas trabalhadas:**\n\n",
                color=0x00ff00
            )

            texto_ativos = ""
            for i, (user_id, data) in enumerate(membros_ordenados[:20], 1):
                member = guild.get_member(user_id)
                if member:
                    total_hours = data.get('total_hours', 0)
                    hours = int(total_hours)
                    minutes = int((total_hours - hours) * 60)

                    if i <= 3:
                        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    else:
                        emoji = "🏅"

                    texto_ativos += f"{emoji} **{i:02d}.** {member.display_name}\n"
                    texto_ativos += f"     ⏱️ {hours:02d}h {minutes:02d}m\n\n"

            embed_ativos.description += texto_ativos
            embed_ativos.set_footer(text=f'Atualizado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}')

            await canal_ativos.send(embed=embed_ativos)

        # Canal de membros inativos
        canal_inativos = guild.get_channel(MEMBROS_INATIVOS_CHANNEL_ID)
        if canal_inativos:
            # Pegar os 20 com menos horas (incluindo 0 horas)
            membros_inativos = membros_ordenados[-20:] if len(membros_ordenados) > 20 else membros_ordenados
            membros_inativos.reverse()  # Inverter para mostrar os menos ativos primeiro

            embed_inativos = discord.Embed(
                title='📉 Membros Menos Ativos',
                description="**⚠️ Membros com menos horas trabalhadas:**\n\n",
                color=0xff9900
            )

            texto_inativos = ""
            for i, (user_id, data) in enumerate(membros_inativos, 1):
                member = guild.get_member(user_id)
                if member:
                    total_hours = data.get('total_hours', 0)
                    hours = int(total_hours)
                    minutes = int((total_hours - hours) * 60)

                    emoji = "⚠️" if total_hours == 0 else "📉"

                    texto_inativos += f"{emoji} **{i:02d}.** {member.display_name}\n"
                    texto_inativos += f"     ⏱️ {hours:02d}h {minutes:02d}m\n\n"

            embed_inativos.description += texto_inativos
            embed_inativos.set_footer(text=f'Atualizado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}')

            await canal_inativos.send(embed=embed_inativos)

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.secondary)
    async def cancelar_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title='❌ Reset Cancelado',
            description="**Reset de horas foi cancelado com sucesso.**",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

@bot.command(name='help_pmesp')
async def help_pmesp(ctx):
    """Mostra os comandos disponíveis do bot PMESP"""

    embed = discord.Embed(
        title='📚 Comandos do Bot PMESP',
        description=(
            "**🚔 Lista de comandos disponíveis:**\n\n"
            "👮‍♂️ **Comandos Administrativos:**\n"
            f"🔹 `!setup_tickets` - Configura painel de tickets\n"
            f"🔹 `!setup_bate_ponto` - Configura painel de bate-ponto\n"
            f"🔹 `!setup_central` - Configura painel da central\n"
            f"🔹 `!painelsetarcargo` - Configura painel de setagem de cargos\n"
            f"🔹 `!setarcargo` - Setagem interativa de cargos (múltiplos membros)\n"
            f"🔹 `!setup_resethoras` - Reseta todas as horas do bate-ponto\n"
            f"🔹 `!setup_all` - Configura todos os painéis\n"
            f"🔹 `!status` - Mostra status do sistema\n\n"
            "ℹ️ **Comandos Gerais:**\n"
            f"🔹 `!help_pmesp` - Mostra esta mensagem\n\n"
            "⚠️ **Nota:** Comandos administrativos requerem permissões especiais"
        ),
        color=0x0066cc
    )
    embed.set_footer(text='PMESP - Sistema de Ajuda', icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    await ctx.send(embed=embed)

# Execução do Bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print('❌ Token do Discord não encontrado! Defina a variável DISCORD_TOKEN')
    else:
        bot.run(TOKEN)

