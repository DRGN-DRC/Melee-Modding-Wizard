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
.set Timer_Frozen,0x0
.set Timer_Unknown,0x1
.set Timer_CountDown,0x02
.set Timer_CountUp,0x03

.set HUDCount_One,0x04
.set HUDCount_Two,0x08
.set HUDCount_Three,0x0C
.set HUDCount_Four,0x10
.set HUDCount_Five,0x14
.set HUDCount_Six,0x18

.set MatchType_Stock,0x20
.set MatchType_Time,0x00
########################
.set Music_On,0x8
.set Music_Off,0x0

.set READY_On,0x00
.set READY_Off,0x20
########################
.set Offscreen_Unk,0x40
.set Offscreen_Unk2,0x00

.set HUD_Create,0x02
.set HUD_DontCreate,0x00

.set SingleButton_On,0x10
.set SingleButton_Off,0x00
########################
.set HUD_ShowScore,0x80
.set HUD_HideScore,0x00

.set Timer_RunWhilePaused,0x01
.set Timer_StopWhilePaused,0x00
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
.set HitboxCollision_Disable,0x20
.set HitboxCollision_Enable,0x00

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
.set Items_Off,-1
.set Items_VeryLow,0
.set Items_Low,1
.set Items_Medium,2
.set Items_High,3
.set Items_VeryHigh,4
########################
#Character External IDs
.set CaptainFalcon,0x0
.set DK,0x1
.set Fox,0x2
.set GaW,0x3
.set Kirby,0x4
.set Bowser,0x5
.set Link,0x6
.set Luigi,0x7
.set Mario,0x8
.set Marth,0x9
.set Mewtwo,0xA
.set Ness,0xB
.set Peach,0xC
.set Pikachu,0xD
.set IceClimbers,0xE
.set Jigglypuff,0xF
.set Samus,0x10
.set Yoshi,0x11
.set Zelda,0x12
.set Sheik,0x13
.set Falco,0x14
.set YLink,0x15
.set Doc,0x16
.set Roy,0x17
.set Pichu,0x18
.set Ganondorf,0x19
########################

#Stage External IDs
.set FoD,0x2
.set PokemonStadium,0x3
.set PeachsCastle,0x4
.set KongoJungle,0x5
.set Brinstar,0x6
.set Corneria,0x7
.set YoshiStory,0x8
.set Onett,0x9
.set MuteCity,0xA
.set RainbowCruise,0xB
.set JungleJapes,0xC
.set GreatBay,0xD
.set HyruleTemple,0xE
.set BrinstarDepths,0xF
.set YoshiIsland,0x10
.set GreenGreens,0x11
.set Fourside,0x12
.set MushroomKingdomI,0x13
.set MushroomKingdomII,0x14
.set Akaneia,0x15
.set Venom,0x16
.set PokeFloats,0x17
.set BigBlue,0x18
.set IcicleMountain,0x19
.set IceTop,0x1A
.set FlatZone,0x1B
.set DreamLand,0x1C
.set YoshiIsland64,0x1D
.set KongoJungle64,0x1E
.set Battlefield,0x1F
.set FinalDestination,0x20

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
  .byte Timer_CountDown | HUDCount_Two | MatchType_Stock
  .byte Music_On | READY_On
  .byte Offscreen_Unk2 | HUD_Create
  .byte HUD_HideScore | Timer_StopWhilePaused | Pause_ShowLRAStart | Pause_CheckForLRAStart | Pause_ShowAnalogStick
#Stocks, Grab behavior, Game End Logic, Bomb Rain
  .byte Stock_RunStockLogic
  .byte HitboxCollision_Enable | Match_CheckForGameEnd
  .byte BombRain_Off
  .byte 0
#Teams, KO Counter, Item frequency
  .byte Teams_Off
  .byte KOCounter_Disable
  .byte 0
  .byte Items_Off
#Item behavior, Stage ID
  .byte 0
  .byte 0
  .hword FinalDestination
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
.byte Marth
.byte PlayerStatus_Human
.byte 4                         #Stock Count
.byte 0                         #Costume ID
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
.byte Marth
.byte PlayerStatus_Human
.byte 4                         #Stock Count
.byte 0                         #Costume ID
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
.byte Marth
.byte PlayerStatus_None
.byte 4                         #Stock Count
.byte 0                         #Costume ID
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
.byte Marth
.byte PlayerStatus_None
.byte 4                         #Stock Count
.byte 0                         #Costume ID
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