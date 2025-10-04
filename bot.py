import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime
import asyncio
import io

# Intents necesarios
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Sistema de almacenamiento de datos
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'tickets': {},
        'server_status': 'offline',
        'banned_users': {},
        'config': {
            'staff_role_id': None,
            'logs_channel_id': None,
            'updates_channel_id': None,
            'ticket_counter': 0,
            'server_logo': 'https://i.imgur.com/9w3wHPF.png',  # Logo por defecto
            'server_online_image': 'https://i.imgur.com/dQwWZpF.png',  # Imagen online por defecto
            'server_offline_image': 'https://i.imgur.com/3vN8FkM.png',  # Imagen offline por defecto
            'transcript_channel_id': None,
            'ticket_panel_channel_id': None,
            'ticket_categories': {
                'soporte': {
                    'name': '🛠️ Soporte Técnico',
                    'description': 'Problemas técnicos, bugs del servidor o ayuda general',
                    'emoji': '🛠️',
                    'category_id': None
                },
                'donaciones': {
                    'name': '💰 Donaciones',
                    'description': 'Consultas sobre donaciones, VIP y beneficios',
                    'emoji': '💰',
                    'category_id': None
                },
                'gangas': {
                    'name': '🎁 Gangas',
                    'description': 'Ofertas especiales, eventos y promociones',
                    'emoji': '🎁',
                    'category_id': None
                },
                'reporte': {
                    'name': '🚨 Reporte a Jugador',
                    'description': 'Reportar jugadores que incumplen las normas',
                    'emoji': '🚨',
                    'category_id': None
                }
            }
        }
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

bot_data = load_data()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user.name}')
    print(f'ID: {bot.user.id}')
    print('------')
    
    # Registrar las vistas persistentes
    bot.add_view(TicketButtonView())
    bot.add_view(CloseTicketView())
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)} comandos sincronizados')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')
    
    await bot.change_presence(activity=discord.Game(name="FiveM Server"))

# ==================== COMANDOS DE CONFIGURACIÓN ====================

@bot.tree.command(name="setup", description="Configuración inicial básica del bot")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild = interaction.guild
        
        # Crear canal de logs
        logs_channel = await guild.create_text_channel(
            name="📋-logs",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
        )
        
        # Crear canal de actualizaciones
        updates_channel = await guild.create_text_channel(
            name="📢-actualizaciones",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(send_messages=False)
            }
        )
        
        # Crear canal de transcripts
        transcript_channel = await guild.create_text_channel(
            name="📄-transcripts",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
        )
        
        bot_data['config']['logs_channel_id'] = logs_channel.id
        bot_data['config']['updates_channel_id'] = updates_channel.id
        bot_data['config']['transcript_channel_id'] = transcript_channel.id
        save_data(bot_data)
        
        embed = discord.Embed(
            title="✅ Setup Básico Completado",
            description="Configuración inicial completada. Ahora configura las categorías de tickets.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📋 Canal de Logs", value=f"<#{logs_channel.id}>", inline=True)
        embed.add_field(name="📢 Canal de Actualizaciones", value=f"<#{updates_channel.id}>", inline=True)
        embed.add_field(name="📄 Canal de Transcripts", value=f"<#{transcript_channel.id}>", inline=True)
        embed.add_field(name="📝 Siguiente Paso", value="Usa `/setupcategory` para configurar cada categoría de ticket", inline=False)
        embed.set_footer(text=f"Configurado por {interaction.user.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al configurar: {e}", ephemeral=True)

@bot.tree.command(name="setupcategory", description="Configura la categoría para un tipo de ticket")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(tipo=[
    app_commands.Choice(name="🛠️ Soporte Técnico", value="soporte"),
    app_commands.Choice(name="💰 Donaciones", value="donaciones"),
    app_commands.Choice(name="🎁 Gangas", value="gangas"),
    app_commands.Choice(name="🚨 Reporte a Jugador", value="reporte")
])
async def setupcategory(interaction: discord.Interaction, tipo: str, category_id: str):
    try:
        category_id_int = int(category_id)
        category = interaction.guild.get_channel(category_id_int)
        
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ ID de categoría inválido. Asegúrate de que sea una categoría válida.", ephemeral=True)
            return
        
        bot_data['config']['ticket_categories'][tipo]['category_id'] = category_id_int
        save_data(bot_data)
        
        ticket_info = bot_data['config']['ticket_categories'][tipo]
        
        embed = discord.Embed(
            title="✅ Categoría Configurada",
            description=f"{ticket_info['emoji']} **{ticket_info['name']}**\nSe abrirá en: **{category.name}**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📝 Descripción", value=ticket_info['description'], inline=False)
        embed.add_field(name="🆔 Category ID", value=f"`{category_id}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ ID inválido. Debe ser un número.", ephemeral=True)

@bot.tree.command(name="setpanelchannel", description="Establece el canal donde se enviará el panel de tickets")
@app_commands.checks.has_permissions(administrator=True)
async def setpanelchannel(interaction: discord.Interaction, canal: discord.TextChannel):
    bot_data['config']['ticket_panel_channel_id'] = canal.id
    save_data(bot_data)
    
    embed = discord.Embed(
        title="✅ Canal de Panel Configurado",
        description=f"El panel de tickets se enviará a {canal.mention}",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setupstaff", description="Establece el rol de staff")
@app_commands.checks.has_permissions(administrator=True)
async def setupstaff(interaction: discord.Interaction, rol: discord.Role):
    bot_data['config']['staff_role_id'] = rol.id
    save_data(bot_data)
    
    embed = discord.Embed(
        title="✅ Rol de Staff Configurado",
        description=f"El rol {rol.mention} ha sido establecido como rol de staff.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setimages", description="Configura las imágenes del bot (logo, online, offline)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(tipo=[
    app_commands.Choice(name="Logo del Servidor", value="logo"),
    app_commands.Choice(name="Imagen Server Online", value="online"),
    app_commands.Choice(name="Imagen Server Offline", value="offline")
])
async def setimages(interaction: discord.Interaction, tipo: str, url: str):
    if tipo == "logo":
        bot_data['config']['server_logo'] = url
        nombre = "Logo del Servidor"
    elif tipo == "online":
        bot_data['config']['server_online_image'] = url
        nombre = "Imagen Server Online"
    else:
        bot_data['config']['server_offline_image'] = url
        nombre = "Imagen Server Offline"
    
    save_data(bot_data)
    
    embed = discord.Embed(
        title="✅ Imagen Configurada",
        description=f"**{nombre}** ha sido actualizado.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_image(url=url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== ESTADO DEL SERVIDOR ====================

@bot.tree.command(name="serverup", description="Marca el servidor como online")
async def serverup(interaction: discord.Interaction, ip: str = None, slots: int = 32):
    bot_data['server_status'] = 'online'
    save_data(bot_data)
    
    embed = discord.Embed(
        title="🟢 SERVIDOR ONLINE",
        description="¡El servidor está ahora disponible para jugar!",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="📡 Estado", value="✅ Online", inline=True)
    
    if ip:
        embed.add_field(name="🌐 IP del Servidor", value=f"`{ip}`", inline=True)
    
    embed.add_field(name="👥 Slots Disponibles", value=f"`{slots}`", inline=True)
    embed.add_field(name="⏰ Actualizado", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=False)
    
    # Añadir logo
    if bot_data['config']['server_logo']:
        embed.set_thumbnail(url=bot_data['config']['server_logo'])
    
    # Añadir imagen de servidor online
    if bot_data['config']['server_online_image']:
        embed.set_image(url=bot_data['config']['server_online_image'])
    
    embed.set_footer(text=f"Actualizado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, "Server Status", f"{interaction.user.mention} marcó el servidor como **ONLINE**")

@bot.tree.command(name="serverdown", description="Marca el servidor como offline")
async def serverdown(interaction: discord.Interaction, razon: str = "Mantenimiento programado"):
    bot_data['server_status'] = 'offline'
    save_data(bot_data)
    
    embed = discord.Embed(
        title="🔴 SERVIDOR OFFLINE",
        description="El servidor está actualmente en mantenimiento.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="📡 Estado", value="❌ Offline", inline=True)
    embed.add_field(name="📝 Razón", value=razon, inline=True)
    embed.add_field(name="⏰ Desde", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=False)
    
    # Añadir logo
    if bot_data['config']['server_logo']:
        embed.set_thumbnail(url=bot_data['config']['server_logo'])
    
    # Añadir imagen de servidor offline
    if bot_data['config']['server_offline_image']:
        embed.set_image(url=bot_data['config']['server_offline_image'])
    
    embed.set_footer(text=f"Actualizado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, "Server Status", f"{interaction.user.mention} marcó el servidor como **OFFLINE**\n**Razón:** {razon}")

# ==================== SISTEMA DE BANEOS ====================

@bot.tree.command(name="ban", description="Banea a un usuario del servidor FiveM")
async def ban(interaction: discord.Interaction, usuario: discord.User, razon: str, duracion: str = "permanente"):
    bot_data['banned_users'][str(usuario.id)] = {
        'username': str(usuario),
        'razon': razon,
        'duracion': duracion,
        'banned_by': str(interaction.user),
        'banned_at': int(datetime.now().timestamp())
    }
    save_data(bot_data)
    
    embed = discord.Embed(
        title="🔨 Usuario Baneado",
        description=f"**{usuario.mention}** ha sido baneado del servidor FiveM.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Usuario", value=f"{usuario.mention}\n`ID: {usuario.id}`", inline=True)
    embed.add_field(name="⏰ Duración", value=duracion, inline=True)
    embed.add_field(name="📝 Razón", value=razon, inline=False)
    embed.add_field(name="👮 Baneado por", value=interaction.user.mention, inline=True)
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.set_footer(text=f"Ban ejecutado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, "Ban", f"{interaction.user.mention} baneó a {usuario.mention}\n**Razón:** {razon}\n**Duración:** {duracion}")

@bot.tree.command(name="unban", description="Desbanea a un usuario")
async def unban(interaction: discord.Interaction, userid: str):
    if userid not in bot_data['banned_users']:
        await interaction.response.send_message("❌ Este usuario no está baneado.", ephemeral=True)
        return
    
    banned_user = bot_data['banned_users'][userid]
    del bot_data['banned_users'][userid]
    save_data(bot_data)
    
    embed = discord.Embed(
        title="✅ Usuario Desbaneado",
        description=f"**{banned_user['username']}** ha sido desbaneado.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Usuario", value=f"{banned_user['username']}\n`ID: {userid}`", inline=True)
    embed.add_field(name="👮 Desbaneado por", value=interaction.user.mention, inline=True)
    embed.set_footer(text=f"Unban ejecutado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, "Unban", f"{interaction.user.mention} desbaneó a {banned_user['username']}")

@bot.tree.command(name="bans", description="Lista de usuarios baneados")
async def bans(interaction: discord.Interaction):
    banned_list = bot_data['banned_users']
    
    if not banned_list:
        await interaction.response.send_message("✅ No hay usuarios baneados.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 Lista de Baneados",
        description=f"Total de baneados: **{len(banned_list)}**",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    for idx, (user_id, data) in enumerate(list(banned_list.items())[:10], 1):
        embed.add_field(
            name=f"{idx}. {data['username']}",
            value=f"**ID:** `{user_id}`\n**Razón:** {data['razon']}\n**Duración:** {data['duracion']}\n**Por:** {data['banned_by']}",
            inline=False
        )
    
    if len(banned_list) > 10:
        embed.set_footer(text=f"Mostrando 10 de {len(banned_list)} baneados")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== SISTEMA DE ACTUALIZACIONES ====================

@bot.tree.command(name="actualizacion", description="Envía una actualización al canal de actualizaciones")
async def actualizacion(interaction: discord.Interaction, titulo: str, descripcion: str, imagen: str = None):
    if not bot_data['config']['updates_channel_id']:
        await interaction.response.send_message("❌ No hay canal de actualizaciones configurado. Usa /setup primero.", ephemeral=True)
        return
    
    channel = interaction.guild.get_channel(bot_data['config']['updates_channel_id'])
    
    embed = discord.Embed(
        title=f"📢 {titulo}",
        description=descripcion,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if imagen:
        embed.set_image(url=imagen)
    
    if bot_data['config']['server_logo']:
        embed.set_thumbnail(url=bot_data['config']['server_logo'])
    
    embed.set_footer(text=f"Actualizado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await channel.send(content="@everyone", embed=embed)
    await interaction.response.send_message("✅ Actualización enviada correctamente.", ephemeral=True)

# ==================== PANEL DE CONTROL ====================

@bot.tree.command(name="panel", description="Muestra el panel de control del servidor")
async def panel(interaction: discord.Interaction):
    status = "🟢 Online" if bot_data['server_status'] == 'online' else "🔴 Offline"
    ban_count = len(bot_data['banned_users'])
    ticket_count = len([t for t in bot_data['tickets'].values() if t.get('open', False)])
    
    embed = discord.Embed(
        title="🎮 Panel de Control - FiveM",
        description="Estado actual del servidor y estadísticas",
        color=discord.Color.green() if bot_data['server_status'] == 'online' else discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="📡 Estado del Servidor", value=status, inline=True)
    embed.add_field(name="🔨 Usuarios Baneados", value=f"`{ban_count}`", inline=True)
    embed.add_field(name="🎫 Tickets Activos", value=f"`{ticket_count}`", inline=True)
    
    if bot_data['config']['server_logo']:
        embed.set_thumbnail(url=bot_data['config']['server_logo'])
    
    embed.set_footer(text=f"Solicitado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ==================== SISTEMA DE TICKETS ====================

class TicketButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Soporte Técnico", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id="ticket_soporte")
    async def soporte_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "soporte")
    
    @discord.ui.button(label="Donaciones", style=discord.ButtonStyle.success, emoji="💰", custom_id="ticket_donaciones")
    async def donaciones_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "donaciones")
    
    @discord.ui.button(label="Gangas", style=discord.ButtonStyle.secondary, emoji="🎁", custom_id="ticket_gangas")
    async def gangas_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "gangas")
    
    @discord.ui.button(label="Reporte a Jugador", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="ticket_reporte")
    async def reporte_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "reporte")

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket_action(interaction)
    
    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="transcript_ticket")
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_transcript(interaction)

@bot.tree.command(name="ticketpanel", description="Crea el panel de tickets con botones")
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    # Verificar que las categorías estén configuradas
    missing_categories = []
    for tipo, data in bot_data['config']['ticket_categories'].items():
        if data['category_id'] is None:
            missing_categories.append(data['name'])
    
    if missing_categories:
        await interaction.response.send_message(
            f"❌ Faltan configurar categorías:\n" + "\n".join([f"• {cat}" for cat in missing_categories]) + 
            "\n\nUsa `/setupcategory` para configurarlas.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🎫 Sistema de Tickets",
        description="**Bienvenido al sistema de soporte**\n\n"
                    "Selecciona el tipo de ticket que necesitas abriendo haciendo clic en uno de los botones de abajo:\n\n"
                    "🛠️ **Soporte Técnico**\n"
                    "Problemas técnicos, bugs del servidor o ayuda general\n\n"
                    "💰 **Donaciones**\n"
                    "Consultas sobre donaciones, VIP y beneficios\n\n"
                    "🎁 **Gangas**\n"
                    "Ofertas especiales, eventos y promociones\n\n"
                    "🚨 **Reporte a Jugador**\n"
                    "Reportar jugadores que incumplen las normas",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if bot_data['config']['server_logo']:
        embed.set_thumbnail(url=bot_data['config']['server_logo'])
    
    embed.set_footer(text="Haz clic en un botón para abrir tu ticket")
    
    # Determinar canal
    if bot_data['config']['ticket_panel_channel_id']:
        channel = interaction.guild.get_channel(bot_data['config']['ticket_panel_channel_id'])
        if channel:
            view = TicketButtonView()
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Panel de tickets creado en el canal configurado.", ephemeral=True)
        else:
            view = TicketButtonView()
            await interaction.channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Panel de tickets creado en este canal.", ephemeral=True)
    else:
        view = TicketButtonView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel de tickets creado.", ephemeral=True)

async def create_ticket(interaction: discord.Interaction, ticket_type: str):
    await interaction.response.defer(ephemeral=True)
    
    ticket_info = bot_data['config']['ticket_categories'][ticket_type]
    
    if not ticket_info['category_id']:
        await interaction.followup.send(f"❌ La categoría de {ticket_info['name']} no está configurada. Contacta con un administrador.", ephemeral=True)
        return
    
    # Verificar si ya tiene un ticket abierto
    for ticket in bot_data['tickets'].values():
        if ticket.get('user_id') == interaction.user.id and ticket.get('open', False):
            channel = interaction.guild.get_channel(ticket['channel_id'])
            await interaction.followup.send(f"❌ Ya tienes un ticket abierto: {channel.mention}", ephemeral=True)
            return
    
    try:
        bot_data['config']['ticket_counter'] += 1
        ticket_number = str(bot_data['config']['ticket_counter']).zfill(4)
        
        category = interaction.guild.get_channel(ticket_info['category_id'])
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }
        
        # Añadir permisos al staff si está configurado
        if bot_data['config']['staff_role_id']:
            staff_role = interaction.guild.get_role(bot_data['config']['staff_role_id'])
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        channel = await category.create_text_channel(
            name=f"ticket-{ticket_number}",
            overwrites=overwrites
        )
        
        bot_data['tickets'][str(channel.id)] = {
            'user_id': interaction.user.id,
            'type': ticket_type,
            'number': ticket_number,
            'channel_id': channel.id,
            'open': True,
            'created_at': int(datetime.now().timestamp()),
            'messages': []
        }
        save_data(bot_data)
        
        embed = discord.Embed(
            title=f"{ticket_info['emoji']} Ticket #{ticket_number} - {ticket_info['name']}",
            description=f"¡Hola {interaction.user.mention}!\n\n"
                       f"Gracias por abrir un ticket. Un miembro del staff te atenderá pronto.\n\n"
                       f"**Categoría:** {ticket_info['name']}\n"
                       f"**Descripción:** {ticket_info['description']}\n"
                       f"**Creado:** <t:{int(datetime.now().timestamp())}:R>",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if bot_data['config']['server_logo']:
            embed.set_thumbnail(url=bot_data['config']['server_logo'])
        
        embed.set_footer(text=f"Ticket creado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        
        view = CloseTicketView()
        
        mention_text = interaction.user.mention
        if bot_data['config']['staff_role_id']:
            mention_text += f" <@&{bot_data['config']['staff_role_id']}>"
        
        await channel.send(content=mention_text, embed=embed, view=view)
        await interaction.followup.send(f"✅ Ticket creado: {channel.mention}", ephemeral=True)
        
        await log_action(interaction.guild, "Ticket Creado", f"{interaction.user.mention} creó el ticket #{ticket_number}\n**Tipo:** {ticket_info['name']}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al crear el ticket: {e}", ephemeral=True)