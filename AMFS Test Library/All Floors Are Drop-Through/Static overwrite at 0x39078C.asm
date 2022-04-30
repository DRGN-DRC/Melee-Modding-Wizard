# Storing at the end of Area 5 of USB/MCC region
# The original code modifies DataOffset_CheckIfOnDropThroughPlatform and ECB_StoreCeilingID+Type.
# This variation instead makes this change while in the debug menu, using the line menu item's 'target function'.
# Conveniently, the current value is updated before a menu item's target function is executed.

.macro SetWord address, value
  lis r15, \address@h		# Load the address to modify
  ori r15, r15, \address@l
  lis r16, \value@h		# Load the value change
  ori r16, r16, \value@l
  stw r16, 0(r15)		# Store value to address
.endm

# New code, to execute on menu item Left/Right check
lwz	r15, 0x10(r4)	# Load flag address (the menu item's current value)
lwz	r16, 0(r15)	# Load flag value
cmpwi	r16, 0
beq	TURN_OFF

# Turn On
SetWord 0x8004CBD4, 0x38600100
SetWord 0x8004FD24, 0x3B200000
b END

TURN_OFF:
SetWord 0x8004CBD4, 0x546305EE
SetWord 0x8004FD24, 0xAB240006

END:
blr