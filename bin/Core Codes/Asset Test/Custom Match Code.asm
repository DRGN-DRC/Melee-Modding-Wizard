#To be inserted at 801b148c
.macro branchl reg, address
lis \reg, \address @h
ori \reg,\reg,\address @l
mtctr \reg
bctrl
.endm

.macro branch reg, address
lis \reg, \address @h
ori \reg,\reg,\address @l
mtctr \reg
bctr
.endm

.macro load reg, address
lis \reg, \address @h
ori \reg, \reg, \address @l
.endm

################################
## Match variable definitions ##
################################

.set READY_On,0x00
.set READY_Off,0x20
########################
.set Offscreen_Unk,0x40
.set Offscreen_Unk2,0x00
########################
.set Pause_HideHUD,0x02
.set Pause_ShowLRAStart,0x04
.set Pause_CheckForLRAStart,0x08
.set Pause_ShowZRetry,0x10
.set Pause_CheckForZ,0x20
.set Pause_ShowAnalogStick,0x40
########################
.set Stock_RunStockLogic,0x20
.set Stock_NoStockLogic,0x0
########################
.set Stock_SkipUnkStockCode,0x40

.set Match_SkipCheckForGameEnd,0x80
.set Match_CheckForGameEnd,0x00
########################
.set BombRain_On,0x01
.set BombRain_Off,0x00
########################
.set Teams_On,0x1
.set Teams_Off,0x0
########################
.set KOCounter_Enable,0x1
.set KOCounter_Disable,0x0
########################
.set PlayerStatus_Human,0x0
.set PlayerStatus_CPU,0x1
.set PlayerStatus_Demo,0x2
.set PlayerStatus_None,0x3
########################
.set Subcolor_Normal,0x0
.set Subcolor_Light,0x1
.set Subcolor_Dark,0x2
.set Subcolor_Black,0x3
.set Subcolor_Gray,0x4
########################
.set Team_None,0x0
.set Team_Red,0x0
.set Team_Blue,0x1
.set Team_Green,0x2
#######################
.set Nametag_None,0x78
########################
.set Rumble_Off,0x00
.set Rumble_On,0x80

.set Spawn_Fall,0x00
.set Spawn_Normal,0x40
########################
.set CPUType_Stay,0x0
.set CPUType_Escape,0x2
.set CPUType_Jump,0x3
.set CPUType_Normal,0x4
.set CPUType_Normal2,0x5
.set CPUType_Nana,0x6
.set CPUType_Defensive,0x7
.set CPUType_Struggle,0x8
.set CPUType_Freak,0x9
.set CPUType_Cooperate,0xA
.set CPUType_SpLwLink,0xB
.set CPUType_SpLwSamus,0xC
.set CPUType_OnlyItem,0xD
.set CPUType_EvZelda,0xE
.set CPUType_NoAct,0xF
.set CPUType_Air,0x10
.set CPUType_Item,0x11
.set CPUType_GuardEdge,0x12
########################

################
## Start Code ##
################

  load     r3,0x80480530           #Match Struct In Memory
  bl    MatchInfoStruct         #Custom Match Struct
  mflr    r4
  li    r5,0xF0                   #Struct Length
  branchl    r12,0x800031f4     #memcpy
  b    exit

MatchInfoStruct:
blrl

######################################################

################
## Match Info ##
################

#Timer, HUD, Pause, and Player Count
  .byte [[Timer]] | [[HUD Count]] | [[Match Type]]
  .byte [[Music]] | [[GO! Display]]
  .byte [[Offscreen Unknown]] | [[Show HUD]]
  .byte [[Show Player Scores]] | [[Timer Stops While Paused]] | Pause_ShowLRAStart | Pause_CheckForLRAStart | Pause_ShowAnalogStick
#Stocks, Grab behavior, Game End Logic, Bomb Rain
  .byte Stock_RunStockLogic
  .byte [[Hitbox Collisions]] | Match_CheckForGameEnd
  .byte BombRain_Off
  .byte 0
#Teams, KO Counter, Item frequency
  .byte Teams_Off
  .byte KOCounter_Disable
  .byte 0
  .byte [[Items]]
#Item behavior, Stage ID
  .byte 0
  .byte 0
  .hword [[Stage]]
#Timer (in seconds)
  .long 480       #seconds
  .byte 0         #milliseconds
#Unknown
  .byte 0
  .byte 0
  .byte 0
#Unknown (read on game end)
  .long 0
#Unknown
  .long 0
#Item Switch
  .long 0xFFFFFFFF  #all enabled
  .long 0xFFFFFFFF  #all enabled
#Unknown
  .long 0x00000000
#Camera Shake Multiplier
  .float 1.0
#Unknown
  .float 1.0
#Unknown
  .float 1.0
#Function to run during StartMelee
  .long 0x0
#Unknown
  .long 0x0
#Function to run while checking for Pause input
  .long 0x0
#Unknown
  .long 0x0
#Function to run every match frame 1(paused or unpaused)
  .long 0x0
#Function to run every match frame 2(paused or unpaused)
  .long 0x0
#Function to run when the match ends
  .long 0x0
#Unknown
  .long 0x0
#isMultispawn (displays a bunch of stocks in the top left, like adventure mode yoshi team)
  .long 0x0
#Unknown
  .long 0x0

#################
## Player Info ##
#################

#Player 1
.byte [[Player 1 Character]]
.byte PlayerStatus_Human
.byte 4                         #Stock Count
.byte [[P1 Costume ID]]         #Costume ID
.byte 0                         #Port number override (0 = default)
.byte -1                        #Spawn point override (-1 = default)
.byte 0                         #Initial Facing Direction? (0 is default)
.byte Subcolor_Normal           #Subcolor
.byte 9                         #Handicap (9 seems to be the default)
.byte Team_None                 #Team ID
.byte Nametag_None              #Nametag ID (0x78 is none)
.byte 0                         #Unknown
.byte Rumble_Off | Spawn_Normal #Rumble + Spawn Flag
.byte 0                         #Unknown bitflags
.byte CPUType_Normal            #CPU type, only takes affect when player is a CPU
.byte 1                         #CPU level, only takes affect when player is a CPU
.hword 0                        #Starting damage
.hword 0                        #Damage after respawning
.hword 0                        #Starting stamina percent
.hword 0                        #Nothing
.float 1.0                      #Attack Ratio
.float 1.0                      #Defense Ratio
.float 1.0                      #Model Scale

#Player 2 Info
.byte [[Player 2 Character]]
.byte PlayerStatus_Human
.byte 4                         #Stock Count
.byte [[P2 Costume ID]]         #Costume ID
.byte 0                         #Port number override (0 = default)
.byte -1                        #Spawn point override (-1 = default)
.byte 0                         #Initial Facing Direction? (0 is default)
.byte Subcolor_Normal           #Subcolor
.byte 9                         #Handicap (9 seems to be the default)
.byte Team_None                 #Team ID
.byte Nametag_None              #Nametag ID (0x78 is none)
.byte 0                         #Unknown
.byte Rumble_Off | Spawn_Normal #Rumble + Spawn Flag
.byte 0                         #Unknown bitflags
.byte CPUType_Normal            #CPU type, only takes affect when player is a CPU
.byte 1                         #CPU level, only takes affect when player is a CPU
.hword 0                        #Starting damage
.hword 0                        #Damage after respawning
.hword 0                        #Starting stamina percent
.hword 0                        #Nothing
.float 1.0                      #Attack Ratio
.float 1.0                      #Defense Ratio
.float 1.0                      #Model Scale

#Player 3 Info
.byte [[Player 3 Character]]
.byte PlayerStatus_None
.byte 4                         #Stock Count
.byte [[P3 Costume ID]]         #Costume ID
.byte 0                         #Port number override (0 = default)
.byte -1                        #Spawn point override (-1 = default)
.byte 0                         #Initial Facing Direction? (0 is default)
.byte Subcolor_Normal           #Subcolor
.byte 9                         #Handicap (9 seems to be the default)
.byte Team_None                 #Team ID
.byte Nametag_None              #Nametag ID (0x78 is none)
.byte 0                         #Unknown
.byte Rumble_Off | Spawn_Normal #Rumble + Spawn Flag
.byte 0                         #Unknown bitflags
.byte CPUType_Normal            #CPU type, only takes affect when player is a CPU
.byte 1                         #CPU level, only takes affect when player is a CPU
.hword 0                        #Starting damage
.hword 0                        #Damage after respawning
.hword 0                        #Starting stamina percent
.hword 0                        #Nothing
.float 1.0                      #Attack Ratio
.float 1.0                      #Defense Ratio
.float 1.0                      #Model Scale

#Player 4 Info
.byte [[Player 4 Character]]
.byte PlayerStatus_None
.byte 4                         #Stock Count
.byte [[P4 Costume ID]]         #Costume ID
.byte 0                         #Port number override (0 = default)
.byte -1                        #Spawn point override (-1 = default)
.byte 0                         #Initial Facing Direction? (0 is default)
.byte Subcolor_Normal           #Subcolor
.byte 9                         #Handicap (9 seems to be the default)
.byte Team_None                 #Team ID
.byte Nametag_None              #Nametag ID (0x78 is none)
.byte 0                         #Unknown
.byte Rumble_Off | Spawn_Normal #Rumble + Spawn Flag
.byte 0                         #Unknown bitflags
.byte CPUType_Normal            #CPU type, only takes affect when player is a CPU
.byte 1                         #CPU level, only takes affect when player is a CPU
.hword 0                        #Starting damage
.hword 0                        #Damage after respawning
.hword 0                        #Starting stamina percent
.hword 0                        #Nothing
.float 1.0                      #Attack Ratio
.float 1.0                      #Defense Ratio
.float 1.0                      #Model Scale

################################################################

exit:
lmw    r27, 0x0014 (sp)
b 0 	# Branch back to injection site (branch distance calculated upon installation)