import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
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
CENTRAL_CHANNEL_ID = 1369350612080394321
VIATURA_LOG_CHANNEL_ID = 1369350949230874834
VIATURA_ROLE_ID = 1369352042031616121
GENERAL_LOG_CHANNEL_ID = 1369351129091280978
PANEL_PERMISSION_ROLE_ID = 1369351249022947468

# Canais de voz para solicitação de viatura
VIATURA_VOICE_CHANNELS = [1369350612080394321, 1369350593101041685]

# Canais de voz para alertas e bate-ponto
VOICE_CHANNELS = [
    1369350549077491783, 1369350561178193991, 1369350573408911390, 1369350581826879658,
    1369350598142460034, 1369350601065889822, 1369350614638919801, 1369350619298664540,
    1369350627561574580, 1369350635891327136, 1369350641306046504, 1369350646720893019,
    1369350652777599147, 1369350663150239874, 1369350667466178610, 1369350672864252106,
    1369350685841293462, 1369350696410812557, 1369350700789928117, 1369350708641534022,
    1369350712856936621, 1369350719194271937, 1369350730280079422, 1369350735027769444,
    1369350737150218312, 1369350749842047147, 1369350764983488632, 1369350767139491921,
    1369350773137477763, 1369350783325306970
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

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🎫 Abrir Ticket', style=discord.ButtonStyle.primary, custom_id='open_ticket')
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        global ticket_counter
        ticket_counter += 1
        
        # Cria o canal do ticket
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
        
        # Embed do ticket
        embed = discord.Embed(
            title="🎫 Ticket Aberto",
            description=f"**Olá {interaction.user.mention}!** 👋\n\n"
                       f"🔹 Seu ticket foi criado com sucesso!\n"
                       f"🔹 Descreva detalhadamente sua solicitação\n"
                       f"🔹 Nossa equipe responderá em breve\n\n"
                       f"**📋 Informações do Ticket:**\n"
                       f"🆔 **ID:** #{ticket_counter:04d}\n"
                       f"👤 **Solicitante:** {interaction.user.display_name}\n"
                       f"🕐 **Aberto em:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n"
                       f"📍 **Status:** Aguardando resposta",
            color=0x00ff00
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="PMESP - Sistema de Tickets", icon_url=guild.icon.url if guild.icon else None)
        
        close_view = TicketCloseView()
        await ticket_channel.send(embed=embed, view=close_view)
        
        # Log do ticket
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📋 Ticket Aberto",
                description=f"**🎫 Novo ticket criado!**\n\n"
                           f"🆔 **ID:** #{ticket_counter:04d}\n"
                           f"👤 **Usuário:** {interaction.user.mention}\n"
                           f"📍 **Canal:** {ticket_channel.mention}\n"
                           f"🕐 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                color=0x00ff00
            )
            await log_channel.send(embed=log_embed)
        
        # Log geral
        general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f"🎫 **Ticket #{ticket_counter:04d}** aberto por {interaction.user.mention} em {ticket_channel.mention}")
        
        await interaction.response.send_message(
            f"✅ **Ticket criado com sucesso!**\n"
            f"🎫 Acesse seu ticket em: {ticket_channel.mention}",
            ephemeral=True
        )

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Fechar Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Confirmar Fechamento",
            description="**⚠️ Tem certeza que deseja fechar este ticket?**\n\n"
                       "🔹 Esta ação não pode ser desfeita\n"
                       "🔹 O canal será deletado permanentemente\n"
                       "🔹 Certifique-se de ter salvado informações importantes",
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
        
        # Log do fechamento
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="🔒 Ticket Fechado",
                description=f"**🎫 Ticket fechado!**\n\n"
                           f"📍 **Canal:** {channel.name}\n"
                           f"👤 **Fechado por:** {interaction.user.mention}\n"
                           f"🕐 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                color=0xff0000
            )
            await log_channel.send(embed=log_embed)
        
        # Log geral
        general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
        if general_log:
            await general_log.send(f"🔒 **Ticket {channel.name}** fechado por {interaction.user.mention}")
        
        await interaction.response.send_message("🔒 **Ticket será fechado em 5 segundos...**")
        await asyncio.sleep(5)
        await channel.delete()

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ **Fechamento cancelado!**", ephemeral=True)

@bot.event
async def on_ready():
    print(f'🤖 Bot {bot.user} está online!')
    print(f'📊 Conectado a {len(bot.guilds)} servidor(s)')
    
    # Adiciona as views persistentes
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
    bot.add_view(BatePontoView())
    bot.add_view(ViaturaView())
    
    # Inicia tasks
    check_voice_alerts.start()

@bot.command(name='setup_tickets')
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """Comando para configurar o painel de tickets"""
    
    # Verifica se o usuário tem o cargo necessário
    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ **Você não tem permissão para usar este comando!**")
        return
    
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ **Canal de tickets não encontrado!**")
        return
    
    embed = discord.Embed(
        title="🎫 Sistema de Tickets PMESP",
        description="**🚔 Bem-vindo ao Sistema de Tickets da PMESP! 🚔**\n\n"
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
                   "👮‍♂️ *Servir e Proteger*",
        color=0x0066cc
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/pmesp_logo.png")
    embed.set_footer(text="PMESP - Sistema Oficial de Tickets", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    view = TicketView()
    await channel.send(embed=embed, view=view)
    await ctx.send("✅ **Painel de tickets configurado com sucesso!**")

# Task para verificar alertas de voz
@tasks.loop(seconds=30)
async def check_voice_alerts():
    """Verifica se usuários saíram dos canais de voz e gerencia alertas"""
    current_time = datetime.now()
    
    for user_id, alert_data in list(voice_alerts.items()):
        if current_time >= alert_data['timeout']:
            # Remove o alerta e fecha o bate-ponto se necessário
            if user_id in bate_ponto_data and bate_ponto_data[user_id]['status'] == 'aberto':
                # Fecha o bate-ponto automaticamente
                bate_ponto_data[user_id]['status'] = 'fechado'
                bate_ponto_data[user_id]['end_time'] = current_time
                
                # Calcula as horas trabalhadas
                start_time = bate_ponto_data[user_id]['start_time']
                worked_hours = (current_time - start_time).total_seconds() / 3600
                
                if 'total_hours' not in bate_ponto_data[user_id]:
                    bate_ponto_data[user_id]['total_hours'] = 0
                bate_ponto_data[user_id]['total_hours'] += worked_hours
                
                # Envia log
                guild = bot.get_guild(GUILD_ID) if GUILD_ID else bot.guilds[0]
                general_log = guild.get_channel(GENERAL_LOG_CHANNEL_ID)
                if general_log:
                    user = guild.get_member(user_id)
                    await general_log.send(
                        f"⏰ **Bate-ponto fechado automaticamente** para {user.mention if user else f'<@{user_id}>'} "
                        f"(não retornou ao canal de voz em 2 minutos)"
                    )
            
            del voice_alerts[user_id]

@bot.event
async def on_voice_state_update(member, before, after):
    """Monitora mudanças de estado de voz"""
    
    # Se o usuário saiu de um canal monitorado
    if before.channel and before.channel.id in VOICE_CHANNELS and (not after.channel or after.channel.id not in VOICE_CHANNELS):
        # Inicia o alerta de 2 minutos
        voice_alerts[member.id] = {
            'timeout': datetime.now() + timedelta(minutes=2),
            'channel_left': before.channel.id
        }
        
        # Envia alerta
        alert_channel = member.guild.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title="⚠️ Alerta de Saída de Canal",
                description=f"**👤 Usuário:** {member.mention}\n"
                           f"**📍 Canal:** {before.channel.name}\n"
                           f"**🕐 Horário:** {datetime.now().strftime('%H:%M:%S')}\n"
                           f"**⏰ Tempo limite:** 2 minutos para retornar",
                color=0xff9900
            )
            await alert_channel.send(embed=embed)
    
    # Se o usuário entrou em um canal monitorado (cancela o alerta)
    elif after.channel and after.channel.id in VOICE_CHANNELS and member.id in voice_alerts:
        del voice_alerts[member.id]
        
        # Envia confirmação
        alert_channel = member.guild.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title="✅ Retorno Confirmado",
                description=f"**👤 Usuário:** {member.mention}\n"
                           f"**📍 Canal:** {after.channel.name}\n"
                           f"**🕐 Horário:** {datetime.now().strftime('%H:%M:%S')}",
                color=0x00ff00
            )
            await alert_channel.send(embed=embed)

if __name__ == "__main__":
    # Token do bot (deve ser definido como variável de ambiente)
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ Token do Discord não encontrado! Defina a variável DISCORD_TOKEN")
    else:
        bot.run(TOKEN)



# Classes para o sistema de bate-ponto
class BatePontoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🟢 Abrir Ponto', style=discord.ButtonStyle.success, custom_id='abrir_ponto', emoji='⏰')
    async def abrir_ponto(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        current_time = datetime.now()
        
        # Verifica se o usuário já tem ponto aberto
        if user_id in bate_ponto_data and bate_ponto_data[user_id]['status'] == 'aberto':
            embed = discord.Embed(
                title="⚠️ Ponto Já Aberto",
                description=f"**{interaction.user.mention}, você já tem um ponto aberto!**\n\n"
                           f"🕐 **Aberto desde:** {bate_ponto_data[user_id]['start_time'].strftime('%d/%m/%Y às %H:%M:%S')}\n"
                           f"⏱️ **Tempo decorrido:** {self.calculate_time_diff(bate_ponto_data[user_id]['start_time'], current_time)}\n\n"
                           f"🔹 Use o botão **'🔴 Fechar Ponto'** para encerrar seu expediente",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Verifica se o usuário está em um canal de voz válido
        if not interaction.user.voice or interaction.user.voice.channel.id not in VOICE_CHANNELS:
            embed = discord.Embed(
                title="❌ Canal de Voz Necessário",
                description=f"**{interaction.user.mention}, você precisa estar em um canal de voz válido!**\n\n"
                           f"🔹 Entre em um dos canais de voz autorizados\n"
                           f"🔹 Tente abrir o ponto novamente\n\n"
                           f"📍 **Canais válidos:** Canais da categoria PMESP",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Abre o ponto
        bate_ponto_data[user_id] = {
            'status': 'aberto',
            'start_time': current_time,
            'voice_channel': interaction.user.voice.channel.id,
            'total_hours': bate_ponto_data.get(user_id, {}).get('total_hours', 0)
        }
        
        embed = discord.Embed(
            title="✅ Ponto Aberto com Sucesso",
            description=f"**🎉 Bom trabalho, {interaction.user.mention}!**\n\n"
                       f"⏰ **Horário de entrada:** {current_time.strftime('%d/%m/%Y às %H:%M:%S')}\n"
                       f"📍 **Canal de voz:** {interaction.user.voice.channel.name}\n"
                       f"🏛️ **Unidade:** PMESP\n\n"
                       f"🔹 Seu expediente foi iniciado\n"
                       f"🔹 Mantenha-se no canal de voz\n"
                       f"🔹 Lembre-se de fechar o ponto ao final\n\n"
                       f"👮‍♂️ **Servir e Proteger!**",
            color=0x00ff00
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="PMESP - Sistema de Bate-Ponto", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log geral
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
        
        # Verifica se o usuário tem ponto aberto
        if user_id not in bate_ponto_data or bate_ponto_data[user_id]['status'] != 'aberto':
            embed = discord.Embed(
                title="⚠️ Nenhum Ponto Aberto",
                description=f"**{interaction.user.mention}, você não tem nenhum ponto aberto!**\n\n"
                           f"🔹 Use o botão **'🟢 Abrir Ponto'** para iniciar seu expediente\n"
                           f"🔹 Certifique-se de estar em um canal de voz válido",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calcula o tempo trabalhado
        start_time = bate_ponto_data[user_id]['start_time']
        worked_seconds = (current_time - start_time).total_seconds()
        worked_hours = worked_seconds / 3600
        
        # Atualiza os dados
        bate_ponto_data[user_id]['status'] = 'fechado'
        bate_ponto_data[user_id]['end_time'] = current_time
        bate_ponto_data[user_id]['total_hours'] += worked_hours
        
        # Formata o tempo trabalhado
        hours = int(worked_seconds // 3600)
        minutes = int((worked_seconds % 3600) // 60)
        seconds = int(worked_seconds % 60)
        
        embed = discord.Embed(
            title="🔴 Ponto Fechado com Sucesso",
            description=f"**👋 Até logo, {interaction.user.mention}!**\n\n"
                       f"⏰ **Horário de saída:** {current_time.strftime('%d/%m/%Y às %H:%M:%S')}\n"
                       f"🕐 **Tempo trabalhado:** {hours:02d}h {minutes:02d}m {seconds:02d}s\n"
                       f"📊 **Total acumulado:** {self.format_hours(bate_ponto_data[user_id]['total_hours'])}\n"
                       f"🏛️ **Unidade:** PMESP\n\n"
                       f"🔹 Seu expediente foi encerrado\n"
                       f"🔹 Horas contabilizadas com sucesso\n"
                       f"🔹 Obrigado pelo seu serviço!\n\n"
                       f"👮‍♂️ **Servir e Proteger!**",
            color=0xff0000
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="PMESP - Sistema de Bate-Ponto", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log geral
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
        
        # Verifica se o usuário tem dados
        if user_id not in bate_ponto_data:
            embed = discord.Embed(
                title="📊 Relatório de Horas",
                description=f"**{interaction.user.mention}, você ainda não registrou nenhum ponto!**\n\n"
                           f"🔹 Use o botão **'🟢 Abrir Ponto'** para começar\n"
                           f"🔹 Suas horas aparecerão aqui após o primeiro registro",
                color=0x0066cc
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        user_data = bate_ponto_data[user_id]
        total_hours = user_data.get('total_hours', 0)
        
        # Se tem ponto aberto, calcula o tempo atual
        current_session = ""
        if user_data['status'] == 'aberto':
            session_seconds = (current_time - user_data['start_time']).total_seconds()
            session_hours = int(session_seconds // 3600)
            session_minutes = int((session_seconds % 3600) // 60)
            current_session = f"\n🟢 **Sessão atual:** {session_hours:02d}h {session_minutes:02d}m (em andamento)"
        
        embed = discord.Embed(
            title="📊 Relatório de Horas Trabalhadas",
            description=f"**👤 Policial:** {interaction.user.mention}\n"
                       f"🏛️ **Unidade:** PMESP\n"
                       f"📅 **Data:** {current_time.strftime('%d/%m/%Y')}\n\n"
                       f"⏱️ **Total de horas:** {self.format_hours(total_hours)}\n"
                       f"📈 **Status:** {'🟢 Em serviço' if user_data['status'] == 'aberto' else '🔴 Fora de serviço'}"
                       f"{current_session}\n\n"
                       f"🔹 Mantenha seu registro em dia\n"
                       f"🔹 Lembre-se de abrir/fechar o ponto\n"
                       f"🔹 Suas horas são importantes!\n\n"
                       f"👮‍♂️ **Servir e Proteger!**",
            color=0x0066cc
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="PMESP - Relatório de Horas", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def calculate_time_diff(self, start_time, end_time):
        """Calcula a diferença de tempo formatada"""
        diff_seconds = (end_time - start_time).total_seconds()
        hours = int(diff_seconds // 3600)
        minutes = int((diff_seconds % 3600) // 60)
        seconds = int(diff_seconds % 60)
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
    
    def format_hours(self, total_hours):
        """Formata as horas totais"""
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        return f"{hours:02d}h {minutes:02d}m"

@bot.command(name='setup_bate_ponto')
@commands.has_permissions(administrator=True)
async def setup_bate_ponto(ctx):
    """Comando para configurar o painel de bate-ponto"""
    
    # Verifica se o usuário tem o cargo necessário
    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ **Você não tem permissão para usar este comando!**")
        return
    
    channel = bot.get_channel(BATE_PONTO_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ **Canal de bate-ponto não encontrado!**")
        return
    
    embed = discord.Embed(
        title="⏰ Sistema de Bate-Ponto PMESP",
        description="**🚔 Bem-vindo ao Sistema de Bate-Ponto da PMESP! 🚔**\n\n"
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
                   "👮‍♂️ *Servir e Proteger*",
        color=0x0066cc
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/pmesp_logo.png")
    embed.set_footer(text="PMESP - Sistema Oficial de Bate-Ponto", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    view = BatePontoView()
    await channel.send(embed=embed, view=view)
    await ctx.send("✅ **Painel de bate-ponto configurado com sucesso!**")


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

def get_user_patente(member):
    """Retorna a patente do usuário baseada nos cargos"""
    # Esta função deve ser customizada baseada nos cargos do servidor
    # Por enquanto, retorna uma patente padrão
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

class ViaturaSelectorModal(discord.ui.Modal):
    def __init__(self, voice_members):
        super().__init__(title="🚔 Seleção de Viatura PMESP")
        self.voice_members = voice_members
        
        # Cria a lista de opções
        options_text = "\\n".join([f"{i+1}. {member.display_name}" for i, member in enumerate(voice_members)])
        
        self.selection = discord.ui.TextInput(
            label="Selecione até 3 pessoas (números separados por vírgula)",
            placeholder="Ex: 1,3,5 (máximo 3 pessoas)",
            style=discord.TextStyle.short,
            max_length=20,
            required=True
        )
        self.add_item(self.selection)
        
        self.reason = discord.ui.TextInput(
            label="Motivo da solicitação",
            placeholder="Descreva o motivo da solicitação de viatura...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse da seleção
            selected_indices = [int(x.strip()) - 1 for x in self.selection.value.split(',')]
            
            # Validações
            if len(selected_indices) > 3:
                await interaction.response.send_message("❌ **Máximo de 3 pessoas permitido!**", ephemeral=True)
                return
            
            if any(i < 0 or i >= len(self.voice_members) for i in selected_indices):
                await interaction.response.send_message("❌ **Números inválidos selecionados!**", ephemeral=True)
                return
            
            # Membros selecionados
            selected_members = [self.voice_members[i] for i in selected_indices]
            
            # Adiciona o solicitante se não estiver na lista
            if interaction.user not in selected_members:
                selected_members.append(interaction.user)
            
            # Se exceder 3 com o solicitante, remove o último selecionado
            if len(selected_members) > 3:
                selected_members = selected_members[:3]
            
            # Encontra a maior patente
            highest_patente_member = get_highest_patente(selected_members)
            highest_patente_name, highest_patente_rank = get_user_patente(highest_patente_member)
            
            # Cria o ID da solicitação
            request_id = len(viatura_requests) + 1
            viatura_requests[request_id] = {
                'solicitante': interaction.user,
                'membros': selected_members,
                'motivo': self.reason.value,
                'timestamp': datetime.now(),
                'status': 'pendente',
                'maior_patente': highest_patente_member
            }
            
            # Envia para o canal de logs
            log_channel = interaction.guild.get_channel(VIATURA_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🚔 Solicitação de Viatura",
                    description=f"**📋 Nova solicitação de viatura!**\\n\\n"
                               f"🆔 **ID:** #{request_id:04d}\\n"
                               f"👤 **Solicitante:** {interaction.user.mention}\\n"
                               f"🏆 **Maior Patente:** {highest_patente_member.mention} ({highest_patente_name.replace('_', ' ').title()})\\n"
                               f"📝 **Motivo:** {self.reason.value}\\n"
                               f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\\n\\n"
                               f"👥 **Membros da Viatura:**\\n" +
                               "\\n".join([f"🔹 {member.mention}" for member in selected_members]),
                    color=0x0066cc
                )
                embed.set_footer(text="PMESP - Sistema de Viaturas", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                
                # View para aceitar/negar
                approval_view = ViaturaApprovalView(request_id)
                await log_channel.send(embed=embed, view=approval_view)
                
                # Inicia o timer de 5 minutos
                asyncio.create_task(self.auto_approve_viatura(request_id, log_channel))
            
            await interaction.response.send_message(
                f"✅ **Solicitação de viatura enviada!**\\n"
                f"🆔 **ID:** #{request_id:04d}\\n"
                f"⏰ **Aguardando aprovação...**",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message("❌ **Formato inválido! Use números separados por vírgula (ex: 1,2,3)**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ **Erro ao processar solicitação:** {str(e)}", ephemeral=True)
    
    async def auto_approve_viatura(self, request_id, log_channel):
        """Aprova automaticamente a viatura após 5 minutos"""
        await asyncio.sleep(300)  # 5 minutos
        
        if request_id in viatura_requests and viatura_requests[request_id]['status'] == 'pendente':
            viatura_requests[request_id]['status'] = 'aprovado_sistema'
            viatura_requests[request_id]['aprovado_por'] = 'Sistema Automático'
            
            embed = discord.Embed(
                title="✅ Viatura Aprovada Automaticamente",
                description=f"**🚔 Viatura #{request_id:04d} aprovada pelo sistema!**\\n\\n"
                           f"⏰ **Motivo:** Tempo limite de 5 minutos atingido\\n"
                           f"🤖 **Aprovado por:** Sistema Automático\\n"
                           f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
                color=0x00ff00
            )
            await log_channel.send(embed=embed)

class ViaturaApprovalView(discord.ui.View):
    def __init__(self, request_id):
        super().__init__(timeout=300)  # 5 minutos
        self.request_id = request_id

    @discord.ui.button(label='✅ Aprovar', style=discord.ButtonStyle.success, custom_id='aprovar_viatura')
    async def aprovar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se o usuário tem o cargo necessário
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ **Você não tem permissão para aprovar viaturas!**", ephemeral=True)
            return
        
        if self.request_id not in viatura_requests:
            await interaction.response.send_message("❌ **Solicitação não encontrada!**", ephemeral=True)
            return
        
        if viatura_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message("❌ **Esta solicitação já foi processada!**", ephemeral=True)
            return
        
        # Aprova a viatura
        viatura_requests[self.request_id]['status'] = 'aprovado'
        viatura_requests[self.request_id]['aprovado_por'] = interaction.user
        
        # Obtém informações do aprovador
        aprovador_patente, _ = get_user_patente(interaction.user)
        
        embed = discord.Embed(
            title="✅ Viatura Aprovada",
            description=f"**🚔 Viatura #{self.request_id:04d} aprovada!**\\n\\n"
                       f"👤 **Aprovado por:** {interaction.user.mention}\\n"
                       f"🏆 **Patente:** {aprovador_patente.replace('_', ' ').title()}\\n"
                       f"🆔 **ID in-game:** {interaction.user.display_name}\\n"
                       f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Desabilita os botões
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label='❌ Negar', style=discord.ButtonStyle.danger, custom_id='negar_viatura')
    async def negar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se o usuário tem o cargo necessário
        if VIATURA_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ **Você não tem permissão para negar viaturas!**", ephemeral=True)
            return
        
        if self.request_id not in viatura_requests:
            await interaction.response.send_message("❌ **Solicitação não encontrada!**", ephemeral=True)
            return
        
        if viatura_requests[self.request_id]['status'] != 'pendente':
            await interaction.response.send_message("❌ **Esta solicitação já foi processada!**", ephemeral=True)
            return
        
        # Nega a viatura
        viatura_requests[self.request_id]['status'] = 'negado'
        viatura_requests[self.request_id]['negado_por'] = interaction.user
        
        embed = discord.Embed(
            title="❌ Viatura Negada",
            description=f"**🚔 Viatura #{self.request_id:04d} negada!**\\n\\n"
                       f"👤 **Negado por:** {interaction.user.mention}\\n"
                       f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            color=0xff0000
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Desabilita os botões
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

class ViaturaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🚔 Solicitar Viatura', style=discord.ButtonStyle.primary, custom_id='solicitar_viatura', emoji='🚨')
    async def solicitar_viatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se o usuário está em um canal de voz válido
        if not interaction.user.voice or interaction.user.voice.channel.id not in VIATURA_VOICE_CHANNELS:
            embed = discord.Embed(
                title="❌ Canal de Voz Necessário",
                description=f"**{interaction.user.mention}, você precisa estar em um canal de voz autorizado!**\\n\\n"
                           f"🔹 Entre em um dos canais de voz da Central\\n"
                           f"🔹 Tente solicitar a viatura novamente\\n\\n"
                           f"📍 **Canais autorizados:** Canais da Central PMESP",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Obtém membros do canal de voz (exceto o solicitante)
        voice_channel = interaction.user.voice.channel
        voice_members = [member for member in voice_channel.members if member != interaction.user and not member.bot]
        
        if not voice_members:
            embed = discord.Embed(
                title="⚠️ Nenhum Membro Disponível",
                description=f"**{interaction.user.mention}, não há outros membros no canal de voz!**\\n\\n"
                           f"🔹 Aguarde outros policiais entrarem no canal\\n"
                           f"🔹 Ou solicite uma viatura individual",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Abre o modal de seleção
        modal = ViaturaSelectorModal(voice_members)
        await interaction.response.send_modal(modal)

@bot.command(name='setup_central')
@commands.has_permissions(administrator=True)
async def setup_central(ctx):
    """Comando para configurar o painel da central"""
    
    # Verifica se o usuário tem o cargo necessário
    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ **Você não tem permissão para usar este comando!**")
        return
    
    channel = bot.get_channel(CENTRAL_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ **Canal da central não encontrado!**")
        return
    
    embed = discord.Embed(
        title="🚔 Central de Operações PMESP",
        description="**🚨 Bem-vindo à Central de Operações da PMESP! 🚨**\\n\\n"
                   "📋 **Sistema de Solicitação de Viaturas:**\\n"
                   "🔹 Clique no botão abaixo para solicitar uma viatura\\n"
                   "🔹 Você deve estar em um canal de voz autorizado\\n"
                   "🔹 Selecione até 3 pessoas para compor a viatura\\n"
                   "🔹 Descreva o motivo da solicitação\\n\\n"
                   "⚠️ **Requisitos:**\\n"
                   "🔸 Estar em canal de voz da Central\\n"
                   "🔸 Máximo de 3 pessoas por viatura\\n"
                   "🔸 Motivo válido para a solicitação\\n"
                   "🔸 Aguardar aprovação do responsável\\n\\n"
                   "📊 **Processo de Aprovação:**\\n"
                   "⏱️ Tempo limite: 5 minutos\\n"
                   "🤖 Aprovação automática se não houver resposta\\n"
                   "👮‍♂️ Aprovação manual pelo responsável\\n"
                   "📋 Log completo de todas as solicitações\\n\\n"
                   "🏛️ **PMESP - Polícia Militar do Estado de São Paulo**\\n"
                   "👮‍♂️ *Servir e Proteger*",
        color=0x0066cc
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/pmesp_logo.png")
    embed.set_footer(text="PMESP - Central de Operações", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    view = ViaturaView()
    await channel.send(embed=embed, view=view)
    await ctx.send("✅ **Painel da central configurado com sucesso!**")


# Eventos adicionais para logs gerais
@bot.event
async def on_member_join(member):
    """Log quando um membro entra no servidor"""
    general_log = member.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title="👋 Membro Entrou",
            description=f"**Novo membro no servidor!**\\n\\n"
                       f"👤 **Usuário:** {member.mention}\\n"
                       f"🆔 **ID:** {member.id}\\n"
                       f"📅 **Conta criada:** {member.created_at.strftime('%d/%m/%Y')}\\n"
                       f"🕐 **Entrou em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
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
            title="👋 Membro Saiu",
            description=f"**Membro saiu do servidor!**\\n\\n"
                       f"👤 **Usuário:** {member.display_name}\\n"
                       f"🆔 **ID:** {member.id}\\n"
                       f"🕐 **Saiu em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
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
    
    # Verifica mudanças de cargo
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        
        if added_roles or removed_roles:
            embed = discord.Embed(
                title="🏷️ Cargos Atualizados",
                description=f"**Cargos do membro foram alterados!**\\n\\n"
                           f"👤 **Usuário:** {after.mention}\\n"
                           f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
                color=0x0066cc
            )
            
            if added_roles:
                embed.add_field(
                    name="➕ Cargos Adicionados",
                    value="\\n".join([f"🔹 {role.name}" for role in added_roles]),
                    inline=False
                )
            
            if removed_roles:
                embed.add_field(
                    name="➖ Cargos Removidos",
                    value="\\n".join([f"🔹 {role.name}" for role in removed_roles]),
                    inline=False
                )
            
            embed.set_thumbnail(url=after.display_avatar.url)
            await general_log.send(embed=embed)
    
    # Verifica mudanças de nickname
    if before.display_name != after.display_name:
        embed = discord.Embed(
            title="📝 Nickname Alterado",
            description=f"**Nickname do membro foi alterado!**\\n\\n"
                       f"👤 **Usuário:** {after.mention}\\n"
                       f"📝 **Antes:** {before.display_name}\\n"
                       f"📝 **Depois:** {after.display_name}\\n"
                       f"🕐 **Horário:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
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
            title="🗑️ Mensagem Deletada",
            description=f"**Mensagem foi deletada!**\\n\\n"
                       f"👤 **Autor:** {message.author.mention}\\n"
                       f"📍 **Canal:** {message.channel.mention}\\n"
                       f"📝 **Conteúdo:** {message.content[:500] if message.content else '*Sem conteúdo de texto*'}\\n"
                       f"🕐 **Deletada em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
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
            title="✏️ Mensagem Editada",
            description=f"**Mensagem foi editada!**\\n\\n"
                       f"👤 **Autor:** {after.author.mention}\\n"
                       f"📍 **Canal:** {after.channel.mention}\\n"
                       f"🔗 **Link:** [Ir para mensagem]({after.jump_url})\\n"
                       f"🕐 **Editada em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            color=0x0066cc
        )
        
        if before.content:
            embed.add_field(
                name="📝 Antes",
                value=before.content[:500] + ("..." if len(before.content) > 500 else ""),
                inline=False
            )
        
        if after.content:
            embed.add_field(
                name="📝 Depois",
                value=after.content[:500] + ("..." if len(after.content) > 500 else ""),
                inline=False
            )
        
        embed.set_thumbnail(url=after.author.display_avatar.url)
        await general_log.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    """Log quando um canal é criado"""
    general_log = channel.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title="📢 Canal Criado",
            description=f"**Novo canal criado!**\\n\\n"
                       f"📍 **Canal:** {channel.mention}\\n"
                       f"📝 **Nome:** {channel.name}\\n"
                       f"🏷️ **Tipo:** {channel.type}\\n"
                       f"🕐 **Criado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            color=0x00ff00
        )
        await general_log.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    """Log quando um canal é deletado"""
    general_log = channel.guild.get_channel(GENERAL_LOG_CHANNEL_ID)
    if general_log:
        embed = discord.Embed(
            title="🗑️ Canal Deletado",
            description=f"**Canal foi deletado!**\\n\\n"
                       f"📝 **Nome:** {channel.name}\\n"
                       f"🏷️ **Tipo:** {channel.type}\\n"
                       f"🕐 **Deletado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            color=0xff0000
        )
        await general_log.send(embed=embed)

# Comando para verificar status do sistema
@bot.command(name='status')
@commands.has_permissions(administrator=True)
async def status_sistema(ctx):
    """Mostra o status do sistema"""
    
    # Verifica se o usuário tem o cargo necessário
    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ **Você não tem permissão para usar este comando!**")
        return
    
    # Estatísticas
    tickets_abertos = len([data for data in bate_ponto_data.values() if data.get('status') == 'aberto'])
    pontos_abertos = len([data for data in bate_ponto_data.values() if data.get('status') == 'aberto'])
    viaturas_pendentes = len([data for data in viatura_requests.values() if data.get('status') == 'pendente'])
    alertas_ativos = len(voice_alerts)
    
    embed = discord.Embed(
        title="📊 Status do Sistema PMESP",
        description=f"**🤖 Bot Online e Funcionando!**\\n\\n"
                   f"📈 **Estatísticas Atuais:**\\n"
                   f"🎫 **Tickets:** {ticket_counter} total criados\\n"
                   f"⏰ **Pontos Abertos:** {pontos_abertos}\\n"
                   f"🚔 **Viaturas Pendentes:** {viaturas_pendentes}\\n"
                   f"⚠️ **Alertas Ativos:** {alertas_ativos}\\n\\n"
                   f"🔧 **Sistemas Ativos:**\\n"
                   f"✅ Sistema de Tickets\\n"
                   f"✅ Sistema de Bate-Ponto\\n"
                   f"✅ Sistema de Viaturas\\n"
                   f"✅ Sistema de Logs\\n"
                   f"✅ Sistema de Alertas\\n\\n"
                   f"🕐 **Última atualização:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
        color=0x00ff00
    )
    embed.set_footer(text="PMESP - Sistema de Gestão", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    await ctx.send(embed=embed)

# Comando para setup completo
@bot.command(name='setup_all')
@commands.has_permissions(administrator=True)
async def setup_all(ctx):
    """Configura todos os painéis de uma vez"""
    
    # Verifica se o usuário tem o cargo necessário
    if PANEL_PERMISSION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ **Você não tem permissão para usar este comando!**")
        return
    
    await ctx.send("🔄 **Configurando todos os painéis...**")
    
    try:
        # Setup tickets
        await setup_tickets(ctx)
        await asyncio.sleep(1)
        
        # Setup bate-ponto
        await setup_bate_ponto(ctx)
        await asyncio.sleep(1)
        
        # Setup central
        await setup_central(ctx)
        
        await ctx.send("✅ **Todos os painéis foram configurados com sucesso!**")
        
    except Exception as e:
        await ctx.send(f"❌ **Erro durante a configuração:** {str(e)}")

# Comando de ajuda personalizado
@bot.command(name='help_pmesp')
async def help_pmesp(ctx):
    """Mostra os comandos disponíveis do bot PMESP"""
    
    embed = discord.Embed(
        title="📚 Comandos do Bot PMESP",
        description="**🚔 Lista de comandos disponíveis:**\\n\\n"
                   "**👮‍♂️ Comandos Administrativos:**\\n"
                   f"🔹 `!setup_tickets` - Configura painel de tickets\\n"
                   f"🔹 `!setup_bate_ponto` - Configura painel de bate-ponto\\n"
                   f"🔹 `!setup_central` - Configura painel da central\\n"
                   f"🔹 `!setup_all` - Configura todos os painéis\\n"
                   f"🔹 `!status` - Mostra status do sistema\\n\\n"
                   "**ℹ️ Comandos Gerais:**\\n"
                   f"🔹 `!help_pmesp` - Mostra esta mensagem\\n\\n"
                   "**⚠️ Nota:** Comandos administrativos requerem permissões especiais",
        color=0x0066cc
    )
    embed.set_footer(text="PMESP - Sistema de Ajuda", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    await ctx.send(embed=embed)

